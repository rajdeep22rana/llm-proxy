import os
import time
import logging

LOG_REQUESTS = os.getenv("LOG_REQUESTS", "false").lower() in {"1", "true", "yes"}
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_logger = logging.getLogger("llm_proxy.request")
if LOG_REQUESTS:
    # Avoid reconfiguring global logging (let Uvicorn manage handlers/formatters).
    _logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    # Ensure our logger emits somewhere even if the root/uvicorn config ignores it
    if not _logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(_logger.level)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
        # Avoid duplicate logs if propagation would also emit via root
        _logger.propagate = False


async def request_logging_middleware(request, call_next):
    if not LOG_REQUESTS:
        return await call_next(request)
    start = time.perf_counter()

    # Pre-request debug details (avoid expensive operations like reading the body)
    if _logger.isEnabledFor(logging.DEBUG):
        _logger.debug(
            "incoming rid=%s method=%s path=%s query=%s content_length=%s "
            "ua=%s origin=%s has_auth=%s",
            getattr(
                request.state, "request_id", request.headers.get("x-request-id") or "-"
            ),
            request.method,
            request.url.path,
            request.url.query,
            request.headers.get("content-length"),
            request.headers.get("user-agent", ""),
            request.headers.get("origin", ""),
            "authorization" in request.headers,
        )

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

    # Summary line at INFO
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

    # Detailed response metadata at DEBUG
    if _logger.isEnabledFor(logging.DEBUG):
        _logger.debug(
            "response rid=%s status=%s content_length=%s vary=%s",
            rid,
            status,
            response.headers.get("content-length"),
            response.headers.get("vary", ""),
        )

    return response
