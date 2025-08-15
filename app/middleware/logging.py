import os
import time
import logging

LOG_REQUESTS = os.getenv("LOG_REQUESTS", "false").lower() in {"1", "true", "yes"}
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_logger = logging.getLogger("llm_proxy.request")
if LOG_REQUESTS:
    logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))


async def request_logging_middleware(request, call_next):
    if not LOG_REQUESTS:
        return await call_next(request)
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000.0
    rid = getattr(
        request.state, "request_id", request.headers.get("x-request-id") or "-"
    )
    method = request.method
    path = request.url.path
    status = response.status_code
    client = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    auth_redacted = "redacted" if "authorization" in request.headers else "none"
    _logger.info(
        "rid=%s method=%s path=%s status=%s duration_ms=%.2f client=%s ua=%s auth=%s",
        rid,
        method,
        path,
        status,
        duration_ms,
        client,
        ua,
        auth_redacted,
    )
    return response
