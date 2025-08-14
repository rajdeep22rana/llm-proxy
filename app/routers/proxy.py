from fastapi import APIRouter
import time
from app.schemas.chat import ChatRequest, ChatResponse, Message, Choice, Usage

router = APIRouter(prefix="/proxy", tags=["proxy"])

@router.post("/", response_model=ChatResponse)
async def proxy(request: ChatRequest):
    # stub implementation
    resp = ChatResponse(
        id="stub",
        object="chat.completion",
        created=int(time.time()),
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content="stub response"),
                finish_reason="stop"
            )
        ],
        usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
    )
    return resp
