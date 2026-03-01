import os

from dotenv import load_dotenv

load_dotenv()

GITHUB_API_BASE = "https://api.github.com"
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
MAX_FILES_FOR_LLM = 20
MAX_CONTENT_FETCHES = 60
MAX_TOTAL_CHARS = 120_000
MAX_FILE_CHARS = 8_000
REQUEST_TIMEOUT = 20
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
GITHUB_MAX_RETRIES = int(os.getenv("GITHUB_MAX_RETRIES", "3"))
GITHUB_RETRY_BACKOFF = float(os.getenv("GITHUB_RETRY_BACKOFF_SECONDS", "0.5"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_RETRY_BACKOFF = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "1.0"))

BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".7z",
    ".rar",
    ".jar",
    ".war",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".class",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
    ".webm",
    ".bin",
    ".lock",
}

IGNORED_PATH_SEGMENTS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "vendor",
    "venv",
    ".venv",
    "__pycache__",
    "target",
    "out",
}

HIGH_PRIORITY_FILES = {
    "readme.md",
    "readme.rst",
    "readme.txt",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
    "go.mod",
    "cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "makefile",
}
