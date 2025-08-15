from fastapi import FastAPI, Response
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


# Simple request ID + metrics middleware
@app.middleware("http")
async def add_request_id_header(request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    end_time = time.perf_counter()
    duration = end_time - start_time

    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    response.headers["x-request-id"] = request_id

    status = str(response.status_code)
    method = request.method
    path = request.url.path
    http_requests_total.labels(method=method, path=path, status=status).inc()
    http_request_duration_seconds.labels(
        method=method, path=path, status=status
    ).observe(duration)
    return response


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


app.include_router(health_router)
app.include_router(proxy_router)
