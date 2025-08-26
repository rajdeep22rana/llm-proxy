from fastapi import APIRouter, Request
import os
import time

router = APIRouter()


@router.get("/healthz")
async def healthz(request: Request):
    # Uptime since process start
    start_time = getattr(request.app.state, "start_time", None)
    uptime_seconds = time.time() - start_time if start_time else None

    # Basic environment/config readiness checks
    # Consider the app healthy if it can serve requests
    # and required configs are sensible.
    # Optional envs are reported for observability.
    required_ok = True

    # Example: Ensure CORS config parsed (from main.py).
    # If origins list is empty, it still works.
    # Nothing hard-required by this app, so we keep
    # required_ok True unless we add strict checks later.

    status = "ok" if required_ok else "degraded"

    return {
        "status": status,
        "uptime_seconds": uptime_seconds,
        "version": os.getenv("APP_VERSION") or "1.0",
        "rate_limit": {
            "enabled": os.getenv("RATE_LIMIT_ENABLED", "false").lower()
            in {"1", "true", "yes"},
            "window_seconds": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60") or 60),
            "max_requests": int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60") or 60),
        },
        "logging": {
            "enabled": os.getenv("LOG_REQUESTS", "false").lower()
            in {"1", "true", "yes"},
            "level": os.getenv("LOG_LEVEL", "INFO").upper(),
        },
        "cors": {
            "allow_origins": [
                o.strip()
                for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
                if o.strip()
            ],
        },
    }
