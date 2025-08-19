import time
from typing import AsyncGenerator

from app.providers.base import LLMProvider
from app.schemas.chat import ChatRequest, ChatResponse, Choice, Message, Usage


class StubProvider(LLMProvider):
    async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse:
        return ChatResponse(
            id="stub",
            object="chat.completion",
            created=int(time.time()),
            choices=[
                Choice(
                    index=0,
                    message=Message(role="assistant", content="stub response"),
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

    async def chat_stream(
        self, request: ChatRequest, authorization: str
    ) -> AsyncGenerator[str, None]:
        for part in ["stub ", "response"]:
            yield part
        return
