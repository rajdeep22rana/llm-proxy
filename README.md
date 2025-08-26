# LLM Proxy

A FastAPI-based proxy exposing health, chat, streaming, and Prometheus metrics endpoints. It supports a stub provider for local testing and an OpenAI-compatible provider for services like Ollama, LM Studio, LocalAI, llama.cpp server, or vLLM.

## Contents

- [LLM Proxy](#llm-proxy)
  - [Contents](#contents)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
  - [Configuration](#configuration)
  - [Running](#running)
  - [API](#api)
  - [Provider Resolution](#provider-resolution)
  - [Errors](#errors)
  - [CORS](#cors)
  - [Docker](#docker)
  - [Testing](#testing)
  - [Code Style](#code-style)

## Prerequisites

- Python 3.11+

## Setup

Create and activate a virtual environment, then install dependencies in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate     # Windows PowerShell

pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt
```

## Configuration

Environment variables control behavior. You can use a `.env` file with uvicorn's `--env-file` option.

Example `.env`:

```dotenv
# Default provider if no mapping matches (stub|ollama). Defaults to stub.
LLM_PROVIDER=stub

# Map model names/prefixes to providers. Exact match or prefix* supported.
# Example: "gpt-4=ollama,local-*=stub"
MODEL_PROVIDER_MAP=

# OpenAI-compatible provider settings (used when provider is "ollama").
# Defaults base URL to http://localhost:11434/v1 (common for Ollama).
OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1
OPENAI_COMPAT_API_KEY=

# CORS allowed origins (comma-separated). Defaults to *
CORS_ALLOW_ORIGINS=*

# Request logging
LOG_REQUESTS=false
LOG_LEVEL=INFO

# Max request body size in bytes (0 disables check)
MAX_REQUEST_BYTES=0

# Rate limiting
RATE_LIMIT_ENABLED=false
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_REQUESTS=60
```

## Running

Start the server with hot reload:

```bash
# Optionally pass your .env for configuration
uvicorn app.main:app --reload --env-file .env
```

## API

- `GET /healthz` → returns server health details, for example:

  ```json
  {
    "status": "ok",
    "uptime_seconds": 12.34,
    "version": "1.0",
    "rate_limit": { "enabled": false, "window_seconds": 60, "max_requests": 60 },
    "logging": { "enabled": false, "level": "INFO" },
    "cors": { "allow_origins": ["*"] }
  }
  ```

- `POST /proxy` (requires `Authorization` header):

  - Request body:
    ```json
    {
      "model": "my-model",
      "messages": [{ "role": "user", "content": "hello" }]
    }
    ```
  - Validation:
    - `messages` must be non-empty
    - Allowed roles: `system`, `user`, `assistant`
    - Each message must have non-empty `content`
    - Last message must not be from role `assistant` (system last is allowed)
  - Response: OpenAI-style `ChatResponse` with `choices` and `usage`.

- `POST /proxy/stream` (requires `Authorization` header):
  - Same request body as `/proxy`
  - Response: `text/event-stream`; emits `data: <chunk>` lines and `data: [DONE]` at end

Interactive docs are available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

- Metrics: `GET /metrics` returns Prometheus exposition with:
  - `http_requests_total{method, path, status}`
  - `http_request_duration_seconds{method, path, status}` histogram

## Provider Resolution

The proxy chooses a provider per request model:

- `MODEL_PROVIDER_MAP` controls mapping. Syntax: `model=provider` or `prefix*=provider`.
- If no mapping matches, falls back to `LLM_PROVIDER` (defaults to `stub`).
- Supported providers:
  - `stub`: returns a canned response; streams "stub response".
  - `ollama`: uses the OpenAI-compatible provider, posting to `/v1/chat/completions` at `OPENAI_COMPAT_BASE_URL`.
    - Auth precedence: if inbound `Authorization` header is present, it is forwarded; otherwise, if `OPENAI_COMPAT_API_KEY` is set, it is sent as `Bearer <key>`.

## Errors

- Unhandled exceptions return `500` with `{"error":"Internal Server Error","request_id":<id>}` and include `x-request-id` header.
- If the downstream compatible server indicates an unknown model, the proxy returns `404` with `{"error":"Model Not Found", ...}`.
- Every response includes an `x-request-id` header (generated or propagated from inbound `x-request-id`).

## CORS

CORS is enabled using `CORS_ALLOW_ORIGINS` (comma-separated list). Preflight and simple requests echo the configured origin.

## Docker

Build and run:

```bash
docker build -t llm-proxy .
docker run --rm -p 8000:80 \
  -e LLM_PROVIDER=stub \
  -e CORS_ALLOW_ORIGINS=http://localhost:3000 \
  llm-proxy
```

## Testing

Run the full test suite:

```bash
pytest
```

Run formatter, linter, and tests together (recommended for developers):

```bash
make test-lint
```

If `make` is unavailable, use the script alternative:

```bash
chmod +x scripts/test_lint.sh
./scripts/test_lint.sh
```

## Code Style

- Format code: `black .`
- Lint code: `flake8`
