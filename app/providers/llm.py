from abc import ABC, abstractmethod
import time

from app.schemas.chat import ChatRequest, ChatResponse, Choice, Message, Usage


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse: ...


class StubProvider(LLMProvider):
    async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse:
        """Default stub implementation returning a placeholder response"""
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


def get_llm_provider() -> LLMProvider:
    """Dependency to get the LLM provider (defaults to StubProvider)"""
    return StubProvider()
