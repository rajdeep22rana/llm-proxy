import os
from fastapi import Response


async def max_body_size_middleware(request, call_next):
    MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", "0") or 0)
    if MAX_REQUEST_BYTES > 0:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    return Response(status_code=413)
            except ValueError:
                pass
    return await call_next(request)
