from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import time
from app.routers.health import router as health_router
from app.routers.proxy import router as proxy_router
from app.metrics import (
    registry,
    http_requests_total,
    http_request_duration_seconds,
    CONTENT_TYPE_LATEST,
    generate_latest,
)

load_dotenv()

app = FastAPI()

# CORS configuration
origins = [o for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Max request size middleware (bytes). 0 disables the check.
MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", "0") or 0)


@app.middleware("http")
async def enforce_max_body_size(request, call_next):
    if MAX_REQUEST_BYTES > 0:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    return Response(status_code=413)
            except ValueError:
                # If header is malformed, continue to let framework handle
                pass
    return await call_next(request)


# Request ID + metrics middleware
@app.middleware("http")
async def add_request_id_header(request, call_next):
    start_time = time.perf_counter()
    # establish request id early so handlers/exception handler can use it
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id

    try:
        response = await call_next(request)
        status = str(response.status_code)
        end_time = time.perf_counter()
        duration = end_time - start_time
    except Exception:
        # record metrics for error path and re-raise
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

    # success path: record metrics and attach request id header
    method = request.method
    path = request.url.path
    http_requests_total.labels(method=method, path=path, status=status).inc()
    http_request_duration_seconds.labels(
        method=method, path=path, status=status
    ).observe(duration)

    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return a consistent JSON error with request_id for traceability."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "request_id": request_id},
        headers={"x-request-id": request_id},
    )


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


app.include_router(health_router)
app.include_router(proxy_router)
