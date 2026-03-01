import base64
import os
from typing import Any
from urllib.parse import urlparse

import requests
from fastapi import HTTPException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import (
    BINARY_EXTENSIONS,
    GITHUB_API_BASE,
    GITHUB_MAX_RETRIES,
    GITHUB_RETRY_BACKOFF,
    HIGH_PRIORITY_FILES,
    IGNORED_PATH_SEGMENTS,
    MAX_CONTENT_FETCHES,
    MAX_FILES_FOR_LLM,
    MAX_FILE_CHARS,
    MAX_TOTAL_CHARS,
    REQUEST_TIMEOUT,
)
from app.schemas import RepoRef


github_session = requests.Session()
github_retry_strategy = Retry(
    total=GITHUB_MAX_RETRIES,
    backoff_factor=GITHUB_RETRY_BACKOFF,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET"]),
    respect_retry_after_header=True,
)
github_adapter = HTTPAdapter(max_retries=github_retry_strategy)
github_session.mount("https://", github_adapter)
github_session.mount("http://", github_adapter)


def parse_github_url(url: str) -> RepoRef:
    parsed = urlparse(url.strip())
    if parsed.netloc not in {"github.com", "www.github.com"}:
        raise ValueError("Only github.com URLs are supported")

    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub repository URL")

    owner, repo = path_parts[0], path_parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        raise ValueError("Invalid GitHub repository URL")

    return RepoRef(owner=owner, repo=repo)


def github_get(path: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-repo-summarizer/1.0",
    }
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        response = github_session.get(
            f"{GITHUB_API_BASE}{path}", headers=headers, timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"GitHub API request failed: {exc}") from exc

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Repository or resource not found")
    if response.status_code == 403:
        raise HTTPException(
            status_code=429,
            detail="GitHub API rate limit reached. Please retry later.",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error: {response.status_code}",
        )
    return response.json()


def should_skip_file(path: str) -> bool:
    lower_path = path.lower()
    parts = lower_path.split("/")
    if any(segment in IGNORED_PATH_SEGMENTS for segment in parts):
        return True

    file_name = parts[-1]
    _, dot, ext = file_name.rpartition(".")
    extension = f".{ext}" if dot else ""
    if extension in BINARY_EXTENSIONS:
        return True

    return file_name in {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"}


def file_priority(path: str) -> int:
    lower = path.lower()
    base = lower.split("/")[-1]
    if base in HIGH_PRIORITY_FILES:
        return 100
    if base.startswith("readme"):
        return 95
    if lower.startswith("docs/"):
        return 70
    if lower.startswith("src/") or lower.startswith("app/"):
        return 65
    if lower.startswith("cmd/") or lower.startswith("lib/"):
        return 60
    if lower.startswith("tests/"):
        return 30
    return 40


def summarize_directory_tree(paths: list[str]) -> str:
    top_level: dict[str, int] = {}
    for path in paths:
        top = path.split("/")[0]
        top_level[top] = top_level.get(top, 0) + 1
    sorted_items = sorted(top_level.items(), key=lambda x: x[1], reverse=True)
    return ", ".join(f"{name} ({count} files)" for name, count in sorted_items[:10])


def fetch_repo_context(repo_ref: RepoRef) -> dict[str, Any]:
    repo_data = github_get(f"/repos/{repo_ref.owner}/{repo_ref.repo}")
    default_branch = repo_data.get("default_branch", "main")
    tree_data = github_get(
        f"/repos/{repo_ref.owner}/{repo_ref.repo}/git/trees/{default_branch}?recursive=1"
    )

    file_paths = [entry["path"] for entry in tree_data.get("tree", []) if entry.get("type") == "blob"]
    filtered_paths = [p for p in file_paths if not should_skip_file(p)]
    candidates = sorted(filtered_paths, key=file_priority, reverse=True)

    selected_files: list[str] = []
    budget = MAX_TOTAL_CHARS
    fetch_attempts = 0

    for path in candidates:
        if len(selected_files) >= MAX_FILES_FOR_LLM or fetch_attempts >= MAX_CONTENT_FETCHES or budget <= 1000:
            break
        fetch_attempts += 1
        content_data = github_get(f"/repos/{repo_ref.owner}/{repo_ref.repo}/contents/{path}?ref={default_branch}")
        if isinstance(content_data, list) or content_data.get("encoding") != "base64" or "content" not in content_data:
            continue

        raw_bytes = base64.b64decode(content_data["content"])
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw_bytes.decode("latin-1")
            except UnicodeDecodeError:
                continue

        text = text.strip()
        if not text:
            continue
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + "\n... [truncated]"

        chunk = f"\n## FILE: {path}\n{text}\n"
        if len(chunk) > budget:
            continue
        selected_files.append(chunk)
        budget -= len(chunk)

    languages_data = github_get(f"/repos/{repo_ref.owner}/{repo_ref.repo}/languages")
    primary_languages = sorted(languages_data.keys(), key=lambda lang: languages_data[lang], reverse=True)[:8]

    return {
        "repo_name": repo_data.get("name", repo_ref.repo),
        "description": repo_data.get("description") or "",
        "stars": repo_data.get("stargazers_count", 0),
        "default_branch": default_branch,
        "languages": primary_languages,
        "tree_summary": summarize_directory_tree(filtered_paths),
        "files_payload": "\n".join(selected_files),
    }
