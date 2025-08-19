from fastapi import APIRouter, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.providers.base import LLMProvider
from app.providers.llm import get_llm_provider
from app.providers.registry import resolve_provider_for_model

router = APIRouter(prefix="/proxy", tags=["proxy"])


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
    provider: LLMProvider = Depends(get_llm_provider),
):
    """Proxy endpoint that delegates chat requests to an LLM provider"""
    _validate_request(request)
    # Allow dependency override to take precedence for tests
    if (
        isinstance(provider, LLMProvider)
        and provider.__class__.__name__ != "StubProvider"
    ):
        chosen_provider = provider
    else:
        chosen_provider = resolve_provider_for_model(request.model)
    return await chosen_provider.chat(request, authorization)


@router.post("/stream")
async def proxy_stream(
    request: ChatRequest,
    authorization: str = Header(...),
    provider: LLMProvider = Depends(get_llm_provider),
):
    """Stream chunks from provider as plain text (SSE-friendly)."""
    _validate_request(request)
    if (
        isinstance(provider, LLMProvider)
        and provider.__class__.__name__ != "StubProvider"
    ):
        chosen_provider = provider
    else:
        chosen_provider = resolve_provider_for_model(request.model)

    async def event_gen():
        async for chunk in chosen_provider.chat_stream(request, authorization):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
