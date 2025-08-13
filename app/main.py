from fastapi import FastAPI

app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}