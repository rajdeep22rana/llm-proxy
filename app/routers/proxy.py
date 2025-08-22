from fastapi import APIRouter, Header, Depends, HTTPException, Request
import logging
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from typing import Optional
from app.providers.base import LLMProvider
from app.providers.registry import resolve_provider_for_model
import json

router = APIRouter(prefix="/proxy", tags=["proxy"])
logger = logging.getLogger("llm_proxy.proxy")


def get_provider_override() -> Optional[LLMProvider]:
    """Dependency hook for tests to inject a provider instance.

    In production this returns None so the registry-based resolver is used.
    Tests can override this dependency to inject custom provider behavior
    (e.g., raising exceptions) without depending on a specific provider module.
    """
    return None


def _validate_request(request: ChatRequest):
    # model must be a non-empty string after trimming
    if not getattr(request, "model", None) or not str(request.model).strip():
        raise HTTPException(status_code=400, detail="Model must not be empty")
    # messages must be non-empty
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages must not be empty")
    allowed_roles = {"system", "user", "assistant"}
    # normalize and validate each message
    for msg in request.messages:
        role = (msg.role or "").strip().lower()
        content = (msg.content or "").strip()
        if role not in allowed_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role: {msg.role}")
        if not content:
            raise HTTPException(
                status_code=400, detail="Message content must not be empty"
            )
        # mutate to normalized values so providers receive trimmed content/role
        msg.role = role
        msg.content = content
    # relaxed final-turn rule: last role must NOT be assistant
    if request.messages[-1].role == "assistant":
        raise HTTPException(
            status_code=400, detail='Last message must not be from role "assistant"'
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
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "proxy.chat model=%s provider=%s messages=%d has_auth=%s",
            request.model,
            type(chosen_provider).__name__,
            len(request.messages),
            bool(authorization),
        )
    return await chosen_provider.chat(request, authorization)


@router.post("/stream")
async def proxy_stream(
    request: ChatRequest,
    authorization: str = Header(...),
    provider: Optional[LLMProvider] = Depends(get_provider_override),
    http_request: Request = None,
):
    """Stream chunks from provider as plain text (SSE-friendly)."""
    _validate_request(request)
    chosen_provider = provider or resolve_provider_for_model(request.model)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "proxy.stream model=%s provider=%s messages=%d has_auth=%s",
            request.model,
            type(chosen_provider).__name__,
            len(request.messages),
            bool(authorization),
        )

    async def event_gen():
        try:
            async for chunk in chosen_provider.chat_stream(request, authorization):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            # Log and emit an SSE error payload followed by DONE so clients can
            # close gracefully
            rid = (
                getattr(http_request.state, "request_id", "-") if http_request else "-"
            )
            logger.exception(
                "proxy.stream error rid=%s model=%s: %s",
                rid,
                request.model,
                str(exc),
            )
            err = {"error": "stream_error", "message": str(exc), "request_id": rid}
            yield f"data: {json.dumps(err)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
