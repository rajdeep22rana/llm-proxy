# Repository Guidelines

## Project Structure & Module Organization

The FastAPI app lives in `app/`, where `main.py` wires dependency-injected routers from `app/routers`, middleware in `app/middleware`, metrics in `app/metrics.py`, and provider adapters under `app/providers`. Request/response schemas stay in Pydantic v2 models inside `app/schemas`. Group new code by domain: routers focus on HTTP concerns, providers encapsulate upstream calls, middleware handles cross-cutting policies, and utilities belong in narrowly scoped helpers. Mirror runtime modules in `tests/` using descriptive `test_*.py` files. Keep shared tooling at the root (`Makefile`, `scripts/`, `setup.py`, `requirements*.txt`) so build automation remains discoverable.

## Architecture & Design Principles

Preserve SOLID boundaries: depend on abstractions (interfaces for providers), keep single responsibilities per module, and favor constructor injection through FastAPI’s dependency system. Apply DRY relentlessly—promote repeated logic into helpers or reusable fixtures rather than copying validation or metrics code. Routes orchestrate models and providers but delegate heavy lifting to services; avoid hidden coupling through globals or module-level state. When extending providers, expose a coherent protocol and register it in `app.providers.registry` without leaking configuration parsing into handlers. Document non-trivial flows with concise docstrings or module headers.

## Build, Test, and Development Commands

- `python3 -m venv .venv && source .venv/bin/activate` provisions the recommended virtualenv; install with `pip install -e . && pip install -r requirements-dev.txt`.
- `uvicorn app.main:app --reload --env-file .env` runs the API locally with hot reload and typed env overrides.
- `make test-lint` (or `./scripts/test_lint.sh`) formats with Black, sorts imports, runs Flake8, and executes pytest with coverage.
- `make fmt`, `make lint`, and `make test` support targeted workflows; the `test` target wraps `pytest --cov=app --cov-report=term-missing`.
- `docker build -t llm-proxy .` then `docker run --rm -p 8000:80 llm-proxy` validates containerization; mount a `.env` file to mirror production.

## Coding Style & Naming Conventions

Target Python 3.11, four-space indentation, and Black’s 88-character lines. Maintain absolute imports, snake_case modules and functions, PascalCase classes, and UPPER_SNAKE_CASE constants. Keep functions short and expressive, annotate parameter and return types, and prefer `from __future__ import annotations` when forward references help clarity. Use `async def` handlers, await outbound I/O, and encapsulate blocking work inside `run_in_executor`. Centralize configuration via environment variables or Pydantic settings models; avoid hardcoded paths or secrets. Enforce docstrings on public routers, providers, and complex utilities, explaining intent rather than implementation details.

## API & Error Handling Guidance

Honor HTTP semantics: 2xx for success, 4xx for client issues, 5xx for upstream failures. Validate inbound payloads with Pydantic models, ensuring explicit field constraints and meaningful error messages. Surface errors through `HTTPException` or structured responses, and log actionable context via middleware without leaking secrets. Keep observability hooks (metrics, logging) consistent by reusing shared utilities instead of sprinkling ad-hoc counters. Update the OpenAPI schema when adding routes, and ensure new endpoints include streaming support where applicable.

## Testing Guidelines

Pytest with pytest-asyncio powers the suite. Co-locate tests beside features, follow Arrange–Act–Assert, and use parametrization to expand coverage without duplication. Cover happy paths, validation failures, authentication branches, streaming behavior, and downstream provider errors. Favor fixtures or factory helpers to build requests, keeping data minimal yet descriptive. Use stubs or mocks for external HTTP, but verify integration wiring with targeted contract tests. Maintain high coverage on critical modules and justify skips or xfails in the PR description. Run `make test` before pushing.

## Commit & Pull Request Guidelines

Write imperative, ~60-character commit subjects (e.g., `Enforce rate limit guard`) with concise bodies detailing intent and side effects. Group related changes together; avoid drive-by edits that obscure review. Pull requests should link issues when relevant, summarize behavioral changes, highlight architecture decisions, and list validation commands. Attach logs or screenshots for user-facing updates, note doc updates, and call out breaking configuration shifts. Keep PRs focused and reviewable; if scope grows, split follow-ups.

## Security, Configuration & Operations

Keep secrets in `.env` files or managed stores—never commit credentials. Confirm `MODEL_PROVIDER_MAP`, rate limiting toggles, security headers, and CORS origins before exposing the proxy publicly. Prefer forwarding client tokens over hardcoding upstream API keys, and enforce HTTPS in production deployments. Monitor `/metrics` for latency and error trends, and ensure structured logs are shipped to your observability stack. When adding background tasks or caches, document eviction and failure handling strategies, and validate they remain async-friendly.

## Developer Workflow Tips

Activate pre-commit hooks if available, or run `make test-lint` before every commit. Track dependencies via `requirements.txt` and `requirements-dev.txt`, pin versions when stability matters, and audit updates for breaking changes. Update `README.md`, `PROJECT_PLAN.md`, and `AGENTS.md` whenever behavior, configuration, or workflows change. When in doubt, open an issue detailing assumptions before coding; shared context reduces rework and keeps collaborators aligned.
