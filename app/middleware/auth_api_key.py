import os
import uuid
from fastapi import Response


def _parse_keys(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


async def api_key_auth_middleware(request, call_next):
    enabled = os.getenv("API_KEY_AUTH_ENABLED", "false").lower() in {"1", "true", "yes"}
    if not enabled:
        return await call_next(request)

    allowed_keys = _parse_keys(os.getenv("API_KEYS"))
    # Expect client-provided proxy auth in X-API-Key header to avoid
    # clashing with downstream Authorization
    provided_key = request.headers.get("x-api-key")
    if not provided_key or (allowed_keys and provided_key not in allowed_keys):
        # Unauthorized; include or generate request id for correlation
        rid = (
            getattr(request.state, "request_id", None)
            or request.headers.get("x-request-id")
            or str(uuid.uuid4())
        )
        request.state.request_id = rid
        resp = Response(status_code=401, content=b'{"error":"Unauthorized"}')
        resp.headers["x-request-id"] = rid
        # Encourage clients to supply X-API-Key
        resp.headers["WWW-Authenticate"] = "X-API-Key"
        return resp

    return await call_next(request)
