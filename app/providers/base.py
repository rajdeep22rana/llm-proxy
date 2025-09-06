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


class ProviderUnauthorizedError(ProviderError):
    """Raised when the provider indicates the caller is unauthorized (401)."""


class ProviderForbiddenError(ProviderError):
    """Raised when the provider forbids access (403)."""


class ProviderRateLimitError(ProviderError):
    """Raised when the provider rate limits the request (429).

    Optionally carries a Retry-After value (seconds).
    """

    def __init__(self, message: str = "", retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse: ...

    @abstractmethod
    async def chat_stream(
        self, request: ChatRequest, authorization: str
    ) -> AsyncGenerator[str, None]: ...
