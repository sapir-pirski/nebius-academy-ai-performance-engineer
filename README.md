# GitHub Repository Summarizer API

A FastAPI service that accepts a public GitHub repository URL and returns:
- a human-readable project summary,
- core technologies,
- and a short structure description.

## Tech Stack
- Python 3.10+
- FastAPI
- OpenAI Python SDK (works with OpenAI or Nebius-compatible endpoints)

## Model Choice
Default model is `gpt-4o-mini` when using OpenAI because it is cost-efficient and strong enough for repository summarization tasks. Nebius is also supported via `NEBIUS_API_KEY` with a configurable model.

## Repository Processing Approach
To fit large repositories into LLM context, the service does **selection and compression**:
1. Parse the GitHub URL and query GitHub REST API for repository metadata and full file tree.
2. Skip low-signal or heavy paths/files such as `node_modules/`, `dist/`, `build/`, binaries/images, and lock files.
3. Prioritize files that best explain the project (`README*`, dependency/config files, key source folders like `src/`, `app/`, `lib/`, docs).
4. Fetch only top-ranked files up to a strict budget (file count + total characters, with truncation per file).
5. Send metadata + compact tree summary + selected excerpts to the LLM.

This balances quality and context limits while keeping latency predictable.

## Project Structure

```text
.
├── app
│   ├── main.py                     # FastAPI app, routes, middleware wiring
│   ├── config.py                   # Configuration/constants
│   ├── schemas.py                  # Request/response schemas and RepoRef dataclass
│   ├── logging_setup.py            # File logger setup
│   ├── error_handlers.py           # Global API error handlers
│   └── services
│       ├── repository_service.py   # GitHub fetching/filtering/context building
│       └── llm_service.py          # LLM prompt, call, retry, response parsing
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
```

## Setup (Clean Machine)
1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a local environment file for sensitive values:

```bash
cp .env.example .env
```

4. Edit `.env` and set your keys (at least one LLM provider key):

```bash
# required if using OpenAI
OPENAI_API_KEY=your_openai_api_key

# optional fallback provider
# NEBIUS_API_KEY=your_nebius_api_key

# optional, recommended for higher GitHub API limits
GITHUB_TOKEN=your_github_token
```

5. (Optional) tune model/base URL in `.env`:

```bash
OPENAI_MODEL=gpt-4o-mini
# only if you need a custom OpenAI-compatible endpoint
# OPENAI_BASE_URL=https://your-endpoint/v1

# optional LLM request timeout in seconds (default: 60)
# LLM_TIMEOUT_SECONDS=60

# optional log directory (default: logs)
# LOG_DIR=logs

# optional LLM retry tuning for transient failures
# LLM_MAX_RETRIES=3
# LLM_RETRY_BACKOFF_SECONDS=1.0

# optional GitHub request retry tuning
# GITHUB_MAX_RETRIES=3
# GITHUB_RETRY_BACKOFF_SECONDS=0.5
```

6. Start server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Usage

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/psf/requests"}'
```

Expected successful response shape:

```json
{
  "summary": "...",
  "technologies": ["..."],
  "structure": "..."
}
```

Error response shape:

```json
{
  "status": "error",
  "message": "Description of what went wrong"
}
```

## Notes
- Only public GitHub repositories are supported.
- GitHub unauthenticated rate limits apply.
- If no suitable text files are found, the API returns `422`.
- Provider selection priority: if `OPENAI_API_KEY` is set, OpenAI is used; otherwise `NEBIUS_API_KEY` is used.
- Large-repo protection: content fetches are capped and text is truncated to stay within LLM context budgets.
- `.env` is ignored by git via `.gitignore` so secrets are not committed.
- Logs are written to `logs/app.log` (rotating file handler). You can override the directory with `LOG_DIR` in `.env`.
- LLM errors are mapped to clear HTTP responses (auth `401`, rate limit `429`, timeout `504`, provider failures `502`).
- Transient errors are retried for GitHub API calls and LLM calls with bounded exponential backoff.
