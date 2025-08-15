from fastapi import APIRouter, Header, Depends, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.providers.llm import LLMProvider, get_llm_provider
from app.providers.registry import resolve_provider_for_model

router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.post("/", response_model=ChatResponse)
async def proxy(
    request: ChatRequest,
    authorization: str = Header(...),
    provider: LLMProvider = Depends(get_llm_provider),
):
    """Proxy endpoint that delegates chat requests to an LLM provider"""
    # Basic semantic validation
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

    # Allow dependency override to take precedence for tests
    if (
        isinstance(provider, LLMProvider)
        and provider.__class__.__name__ != "StubProvider"
    ):
        chosen_provider = provider
    else:
        # Choose provider based on model mapping (env MODEL_PROVIDER_MAP) or default
        chosen_provider = resolve_provider_for_model(request.model)

    return await chosen_provider.chat(request, authorization)
