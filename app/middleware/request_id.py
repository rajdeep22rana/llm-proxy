import uuid
import time
from app.metrics import http_requests_total, http_request_duration_seconds


async def request_id_and_metrics_middleware(request, call_next):
    start_time = time.perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
        status = str(response.status_code)
        end_time = time.perf_counter()
        duration = end_time - start_time
    except Exception:
        status = "500"
        end_time = time.perf_counter()
        duration = end_time - start_time
        method = request.method
        path = request.url.path
        http_requests_total.labels(method=method, path=path, status=status).inc()
        http_request_duration_seconds.labels(
            method=method, path=path, status=status
        ).observe(duration)
        raise
    method = request.method
    path = request.url.path
    http_requests_total.labels(method=method, path=path, status=status).inc()
    http_request_duration_seconds.labels(
        method=method, path=path, status=status
    ).observe(duration)
    response.headers["x-request-id"] = request_id
    return response
