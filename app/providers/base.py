from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.schemas.chat import ChatRequest, ChatResponse


class ProviderError(Exception):
    """Base class for provider-specific errors raised intentionally.

    Providers should raise these to signal domain-specific failures that the
    API layer can map to precise HTTP responses (instead of a generic 500).
    """


class ProviderModelNotFoundError(ProviderError):
    """Raised when the requested model is not available on the provider side."""


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse: ...

    @abstractmethod
    async def chat_stream(
        self, request: ChatRequest, authorization: str
    ) -> AsyncGenerator[str, None]: ...
