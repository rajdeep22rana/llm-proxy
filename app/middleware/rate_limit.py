import os
import time
from collections import deque, defaultdict
from typing import Deque
from fastapi import Response

_rate_limit_buckets: dict[str, Deque[float]] = defaultdict(deque)
# Track last cleanup time to avoid per-request full scans
_last_cleanup_ts: float = 0.0


def _maybe_cleanup(now: float, window_seconds: int) -> None:
    """Periodically purge expired timestamps and empty buckets.

    This prevents unbounded growth of `_rate_limit_buckets` keys over time.
    Cleanup runs at a configurable interval and removes keys whose deques
    become empty after expiring old entries.
    """
    global _last_cleanup_ts
    cleanup_interval = int(os.getenv("RATE_LIMIT_CLEANUP_INTERVAL_SECONDS", "60") or 60)
    if now - _last_cleanup_ts < cleanup_interval:
        return
    _last_cleanup_ts = now
    window_start = now - window_seconds
    # Iterate over a snapshot of keys to allow deletions during traversal
    for key in list(_rate_limit_buckets.keys()):
        bucket = _rate_limit_buckets.get(key)
        if bucket is None:
            continue
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if not bucket:
            # Remove empty buckets to keep the dict from growing unbounded
            _rate_limit_buckets.pop(key, None)


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
    # Periodically cleanup old entries and empty buckets
    _maybe_cleanup(now, RATE_LIMIT_WINDOW_SECONDS)
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
