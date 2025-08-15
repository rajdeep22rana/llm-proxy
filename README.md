# LLM Proxy

A minimal FastAPI-based proxy that exposes a health endpoint and a stubbed chat proxy endpoint. This repository is currently set up for local development and testing only (no real LLM calls).

## Contents

- [LLM Proxy](#llm-proxy)
  - [Contents](#contents)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
  - [Configuration](#configuration)
  - [Running](#running)
  - [API](#api)
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

Environment variables are loaded from a local `.env` file at startup.

Create `.env` (optional for current stub-only flow):

```dotenv
# Provider selection (defaults to stub if unset)
LLM_PROVIDER=stub

# Not used until a real provider is added
# OPENAI_API_KEY=sk-<your-key>
```

## Running

Start the server with hot reload:

```bash
uvicorn app.main:app --reload
```

## API

- `GET /healthz` → `{ "status": "ok" }`
- `POST /proxy` (requires `Authorization` header and a minimal request body):
  - Example request body:
    ```json
    {
      "model": "test-model",
      "messages": [{ "role": "user", "content": "hello" }]
    }
    ```
  - Returns a stubbed OpenAI-style `ChatResponse` payload.

Interactive docs are available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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
