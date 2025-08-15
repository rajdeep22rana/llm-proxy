import os
import time
from collections import deque, defaultdict
from typing import Deque
from fastapi import Response

_rate_limit_buckets: dict[str, Deque[float]] = defaultdict(deque)


async def rate_limit_middleware(request, call_next):
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60") or 60)
    RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60") or 60)
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    key = (
        request.headers.get("authorization")
        or (request.client.host if request.client else None)
        or "anonymous"
    )
    bucket = _rate_limit_buckets[key]
    while bucket and bucket[0] < window_start:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        resp = Response(status_code=429)
        resp.headers["Retry-After"] = str(RATE_LIMIT_WINDOW_SECONDS)
        return resp
    bucket.append(now)
    return await call_next(request)
