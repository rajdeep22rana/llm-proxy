from fastapi import FastAPI
from dotenv import load_dotenv
from app.routers.health import router as health_router
from app.routers.proxy import router as proxy_router
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid

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


# Simple request ID middleware
@app.middleware("http")
async def add_request_id_header(request, call_next):
    response = await call_next(request)
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    response.headers["x-request-id"] = request_id
    return response


app.include_router(health_router)
app.include_router(proxy_router)
