from abc import ABC, abstractmethod
import time
import os
from typing import AsyncGenerator
from app.schemas.chat import ChatRequest, ChatResponse, Choice, Message, Usage


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse: ...

    @abstractmethod
    async def chat_stream(
        self, request: ChatRequest, authorization: str
    ) -> AsyncGenerator[str, None]: ...


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

    async def chat_stream(
        self, request: ChatRequest, authorization: str
    ) -> AsyncGenerator[str, None]:
        # Simple two-part stub stream
        for part in ["stub ", "response"]:
            yield part
        return


def get_llm_provider() -> LLMProvider:
    """Dependency to get the LLM provider based on the LLM_PROVIDER env var."""
    provider_name = os.getenv("LLM_PROVIDER", "stub").lower()
    if provider_name == "stub":
        return StubProvider()
    raise RuntimeError(f"Unknown LLM_PROVIDER '{provider_name}'.")
