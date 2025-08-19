from fastapi import APIRouter, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from typing import Optional
from app.providers.base import LLMProvider
from app.providers.registry import resolve_provider_for_model

router = APIRouter(prefix="/proxy", tags=["proxy"])


def get_provider_override() -> Optional[LLMProvider]:
    """Dependency hook for tests to inject a provider instance.

    In production this returns None so the registry-based resolver is used.
    Tests can override this dependency to inject custom provider behavior
    (e.g., raising exceptions) without depending on a specific provider module.
    """
    return None


def _validate_request(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages must not be empty")
    allowed_roles = {"system", "user", "assistant"}
    for msg in request.messages:
        if msg.role not in allowed_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role: {msg.role}")
        if not msg.content:
            raise HTTPException(
                status_code=400, detail="Message content must not be empty"
            )
    if request.messages[-1].role != "user":
        raise HTTPException(
            status_code=400, detail='Last message must be from role "user"'
        )


@router.post("/", response_model=ChatResponse)
async def proxy(
    request: ChatRequest,
    authorization: str = Header(...),
    provider: Optional[LLMProvider] = Depends(get_provider_override),
):
    """Proxy endpoint that delegates chat requests to an LLM provider"""
    _validate_request(request)
    # Allow dependency override to take precedence for tests
    chosen_provider = provider or resolve_provider_for_model(request.model)
    return await chosen_provider.chat(request, authorization)


@router.post("/stream")
async def proxy_stream(
    request: ChatRequest,
    authorization: str = Header(...),
    provider: Optional[LLMProvider] = Depends(get_provider_override),
):
    """Stream chunks from provider as plain text (SSE-friendly)."""
    _validate_request(request)
    chosen_provider = provider or resolve_provider_for_model(request.model)

    async def event_gen():
        async for chunk in chosen_provider.chat_stream(request, authorization):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
