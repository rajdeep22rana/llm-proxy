from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import logging
from app.routers.health import router as health_router
from app.routers.proxy import router as proxy_router
from app.metrics import (
    registry,
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from app.middleware.max_body_size import max_body_size_middleware
from app.middleware.request_id import request_id_and_metrics_middleware
from app.middleware.logging import request_logging_middleware
from app.middleware.rate_limit import rate_limit_middleware
from app.providers.base import ProviderModelNotFoundError

app = FastAPI()

# CORS configuration
raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
# When origins is wildcard, browsers disallow credentials with ACAO "*".
# Disable credentials in that case to avoid confusing/invalid behavior.
is_wildcard = len(origins) == 1 and origins[0] == "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=not is_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register middlewares (order matters)
@app.middleware("http")
async def _max_body_size(request, call_next):
    return await max_body_size_middleware(request, call_next)


@app.middleware("http")
async def _request_id_and_metrics(request, call_next):
    return await request_id_and_metrics_middleware(request, call_next)


@app.middleware("http")
async def _request_logging(request, call_next):
    return await request_logging_middleware(request, call_next)


@app.middleware("http")
async def _rate_limit(request, call_next):
    return await rate_limit_middleware(request, call_next)


# Global exception handler
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    # Provide a more precise error for known provider conditions
    if isinstance(exc, ProviderModelNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": "Model Not Found",
                "detail": str(exc) or "Requested model is not available",
                "request_id": request_id,
            },
            headers={"x-request-id": request_id},
        )
    # Log unhandled exceptions with request correlation for debugging
    logging.getLogger("llm_proxy.errors").exception(
        "unhandled_exception rid=%s path=%s method=%s", request_id, request.url.path, request.method
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "request_id": request_id},
        headers={"x-request-id": request_id},
    )


# Metrics endpoint
@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


# Routers
app.include_router(health_router)
app.include_router(proxy_router)
