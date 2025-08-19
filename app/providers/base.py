from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.schemas.chat import ChatRequest, ChatResponse


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse: ...

    @abstractmethod
    async def chat_stream(
        self, request: ChatRequest, authorization: str
    ) -> AsyncGenerator[str, None]: ...
