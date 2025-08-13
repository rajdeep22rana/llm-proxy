from fastapi import FastAPI
from app.routers.health import router as health_router
from app.routers.proxy import router as proxy_router

app = FastAPI()
app.include_router(health_router)
app.include_router(proxy_router)
