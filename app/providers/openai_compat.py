"""
OpenAI-compatible provider
-------------------------

This module provides `OpenAICompatibleProvider`, an implementation of the
`LLMProvider` interface that targets any server which exposes the OpenAI
Chat Completions API shape (i.e., `/v1/chat/completions`).

Key design points:
1) Scope and intent
   - This is NOT an official OpenAI provider. It exists to talk to local
     or third-party servers that emulate the OpenAI API (e.g., Ollama,
     LM Studio, LocalAI, llama.cpp server, vLLM). This lets us run and
     test the app without incurring paid API costs.

2) Base URL configuration
   - The base URL is configured via `OPENAI_COMPAT_BASE_URL` and defaults
     to `http://localhost:11434/v1` which is the typical Ollama endpoint.
   - We intentionally do not default to OpenAI's public endpoint to avoid
     accidental paid usage.

3) Authentication
   - Some compatible servers do not require authentication. If an
     Authorization header is supplied by the incoming request we forward
     it. Otherwise if `OPENAI_COMPAT_API_KEY` is set, we send it as a
     Bearer token for compatibility with servers that enforce auth.

4) Schema mapping
   - Input: we forward `model` and `messages` from our `ChatRequest` as-is
     into the OpenAI-compatible payload.
   - Non-stream response: we map the provider's response back into our
     `ChatResponse` structure, including choices and usage (with safe
     defaults).
   - Stream response: we read Server-Sent Events (SSE-like) lines, parse
     each JSON `data:` payload, and yield only `choices[0].delta.content`
     text chunks. Our router wraps these in SSE `data:` lines for clients.

5) Error handling
   - HTTP errors are surfaced via `response.raise_for_status()`. Any
     ill-formed streaming lines are ignored to keep the stream resilient.
"""

import os
import json
from typing import AsyncGenerator, Dict, Any, Optional, List

import httpx

from app.providers.base import (
    LLMProvider,
    ProviderModelNotFoundError,
    ProviderUnauthorizedError,
    ProviderForbiddenError,
    ProviderRateLimitError,
)
from app.schemas.chat import ChatRequest, ChatResponse, Choice, Message, Usage


class OpenAICompatibleProvider(LLMProvider):
    """Provider that speaks the OpenAI Chat Completions API shape.

    This class enables using local/compatible servers (e.g., Ollama) via a
    single implementation, keeping our app independent from any specific
    vendor. It implements both non-streaming and streaming chat calls.

    Attributes:
        base_url: Base URL for the compatible API, e.g.,
                  "http://localhost:11434/v1" for Ollama.
        env_api_key: Optional API key used if the caller did not supply
                     an Authorization header; useful for servers enforcing
                     auth even in local/dev scenarios.
    """

    def __init__(self) -> None:
        # Prefer explicit compat var; default is the common Ollama endpoint.
        # We avoid defaulting to OpenAI's public API to prevent accidental costs.
        self.base_url = os.getenv(
            "OPENAI_COMPAT_BASE_URL", "http://localhost:11434/v1"
        ).rstrip("/")
        # Optional key used only if the inbound request did not already include
        # an Authorization header. Many local servers ignore this.
        self.env_api_key = os.getenv("OPENAI_COMPAT_API_KEY")
        # Default to a generous timeout for non-streaming requests (seconds)
        try:
            self.timeout_seconds = float(
                os.getenv("OPENAI_COMPAT_TIMEOUT_SECONDS", "600") or 600
            )
        except ValueError:
            self.timeout_seconds = 600.0

    def _headers(self, authorization: Optional[str]) -> Dict[str, str]:
        """Construct request headers for the downstream compatible API.

        Precedence:
        1) If the inbound request provided an Authorization header, forward it.
        2) Else, if `OPENAI_COMPAT_API_KEY` is set, send it as a Bearer token.
        3) Otherwise, omit Authorization entirely (many local servers allow this).
        """
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        token: Optional[str] = None

        if authorization and authorization.strip():
            token = authorization
        elif self.env_api_key:
            token = f"Bearer {self.env_api_key}"

        if token:
            headers["Authorization"] = token
        return headers

    async def chat(self, request: ChatRequest, authorization: str) -> ChatResponse:
        """Perform a non-streaming chat completion request.

        Process:
        - Build a minimal OpenAI-compatible payload from our `ChatRequest`.
        - POST to `/chat/completions` at the configured base URL.
        - Map the response into our `ChatResponse` schema with safe defaults.

        Notes:
        - We set `stream` to False here explicitly.
        - If the remote server omits `usage`, we provide zeroed counters.
        """
        payload: Dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": m.role, "content": m.content} for m in request.messages
            ],
            "stream": False,
        }
        # Forward optional OpenAI-compatible parameters if present
        temperature = getattr(request, "temperature", None)
        if temperature is not None:
            payload["temperature"] = temperature
        top_p = getattr(request, "top_p", None)
        if top_p is not None:
            payload["top_p"] = top_p
        max_tokens = getattr(request, "max_tokens", None)
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        frequency_penalty = getattr(request, "frequency_penalty", None)
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty
        presence_penalty = getattr(request, "presence_penalty", None)
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        stop = getattr(request, "stop", None)
        if stop is not None:
            payload["stop"] = stop
        n = getattr(request, "n", None)
        if n is not None:
            payload["n"] = n
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout_seconds
        ) as client:
            response = await client.post(
                "/chat/completions",
                headers=self._headers(authorization),
                json=payload,
            )
            # Map common auth/rate-limit errors explicitly before raise_for_status
            if response.status_code in (401, 403, 429):
                try:
                    err = response.json()
                except Exception:
                    err = {}
                message = str(err.get("error") or err.get("message") or "")
                if response.status_code == 401:
                    raise ProviderUnauthorizedError(message or "Unauthorized")
                if response.status_code == 403:
                    raise ProviderForbiddenError(message or "Forbidden")
                if response.status_code == 429:
                    retry_after = None
                    try:
                        retry_after = int(response.headers.get("Retry-After"))
                    except Exception:
                        retry_after = None
                    raise ProviderRateLimitError(message or "Rate Limited", retry_after_seconds=retry_after)
            # Map a narrow 404 case to a ProviderModelNotFoundError. We only
            # do this if the downstream body explicitly indicates an unknown
            # model, to avoid conflating unrelated 404s.
            if response.status_code == 404:
                try:
                    err = response.json()
                except Exception:
                    err = {}
                message = str(err.get("error") or err.get("message") or "")
                # Common shapes seen across compat servers
                lower_msg = message.lower()
                if (
                    any(
                        key in lower_msg
                        for key in ["model", "not found", "unknown model"]
                    )
                    and request.model.replace(" ", "") in lower_msg
                ):
                    raise ProviderModelNotFoundError(
                        message or f"Model not found: {request.model}"
                    )
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

        # Convert provider response into our response model.
        # We tolerate missing/empty `choices` by returning a single empty choice.
        choices_raw: List[Dict[str, Any]] = data.get("choices", [])
        if not choices_raw:
            choices_raw = [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ""},
                    "finish_reason": "stop",
                }
            ]

        choices: List[Choice] = []
        for choice in choices_raw:
            message_raw = choice.get("message") or {}
            choices.append(
                Choice(
                    index=choice.get("index", 0),
                    message=Message(
                        role=message_raw.get("role", "assistant"),
                        content=message_raw.get("content", ""),
                    ),
                    finish_reason=choice.get("finish_reason"),
                )
            )

        # Some compatible servers omit `usage`; default to zeros in that case.
        usage_raw = data.get("usage") or {}
        usage = Usage(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
        )

        return ChatResponse(
            id=str(data.get("id", "ollama")),
            object=str(data.get("object", "chat.completion")),
            created=int(data.get("created", 0)),
            choices=choices,
            usage=usage,
        )

    async def chat_stream(
        self, request: ChatRequest, authorization: str
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the compatible API and yield raw content chunks.

        Process:
        - POST to `/chat/completions` with `stream=True`.
        - Read the response as a text stream of SSE-like lines.
        - Each meaningful line begins with `data: ` followed by a JSON object
          containing a standard OpenAI streaming delta payload.
        - For each object, extract `choices[0].delta.content` (if present) and
          yield it as a plain text chunk.

        Why yield plain text only?
        - Our FastAPI router (`/proxy/stream`) is responsible for wrapping
          these raw chunks in proper SSE `data:` lines for clients.
        - This separation keeps the provider focused on model-token emission.
        """
        payload: Dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": m.role, "content": m.content} for m in request.messages
            ],
            "stream": True,
        }
        # Forward optional OpenAI-compatible parameters if present
        temperature = getattr(request, "temperature", None)
        if temperature is not None:
            payload["temperature"] = temperature
        top_p = getattr(request, "top_p", None)
        if top_p is not None:
            payload["top_p"] = top_p
        max_tokens = getattr(request, "max_tokens", None)
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        frequency_penalty = getattr(request, "frequency_penalty", None)
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty
        presence_penalty = getattr(request, "presence_penalty", None)
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        stop = getattr(request, "stop", None)
        if stop is not None:
            payload["stop"] = stop
        n = getattr(request, "n", None)
        if n is not None:
            payload["n"] = n
        async with httpx.AsyncClient(base_url=self.base_url, timeout=None) as client:
            async with client.stream(
                "POST",
                "/chat/completions",
                headers=self._headers(authorization),
                json=payload,
            ) as response:
                if response.status_code in (401, 403, 429):
                    # read body to extract message if available
                    try:
                        text = await response.aread()
                        data_str = text.decode("utf-8", errors="ignore")
                        obj = json.loads(data_str)
                    except Exception:
                        obj = {}
                    message = str(obj.get("error") or obj.get("message") or "")
                    if response.status_code == 401:
                        raise ProviderUnauthorizedError(message or "Unauthorized")
                    if response.status_code == 403:
                        raise ProviderForbiddenError(message or "Forbidden")
                    if response.status_code == 429:
                        retry_after = None
                        # httpx stream response may not expose headers; attempt to access
                        try:
                            retry_after = int(response.headers.get("Retry-After"))
                        except Exception:
                            retry_after = None
                        raise ProviderRateLimitError(message or "Rate Limited", retry_after_seconds=retry_after)
                if response.status_code == 404:
                    # Attempt to parse an explicit unknown-model message
                    try:
                        text = await response.aread()
                        data_str = text.decode("utf-8", errors="ignore")
                        obj = json.loads(data_str)
                    except Exception:
                        obj = {}
                    message = str(obj.get("error") or obj.get("message") or "")
                    lower_msg = message.lower()
                    if (
                        any(
                            key in lower_msg
                            for key in ["model", "not found", "unknown model"]
                        )
                        and request.model.replace(" ", "") in lower_msg
                    ):
                        raise ProviderModelNotFoundError(
                            message or f"Model not found: {request.model}"
                        )
                response.raise_for_status()
                async for line in response.aiter_lines():
                    # The stream typically emits a sequence of lines, many of which
                    # are empty heartbeats. We skip empty lines early.
                    if not line:
                        continue
                    # Compatible servers often send SSE frames prefixed with `data: `.
                    # Normalize by stripping the prefix if present, so `data_str`
                    # contains just the JSON payload.
                    data_str = line
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                    # The `[DONE]` sentinel indicates the server is finished.
                    if data_str == "[DONE]":
                        break
                    # Parse the JSON payload. If a malformed line is encountered,
                    # ignore it to preserve a resilient stream for clients.
                    try:
                        obj = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    # Standard OpenAI streaming payload shape includes a `choices`
                    # array where each element may carry a `delta` with incremental
                    # content. We currently stream only the first choice.
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    # Only yield when actual textual content is present. Other fields
                    # such as role changes or tool calls would require additional
                    # handling which we intentionally omit in this generic provider.
                    if content:
                        yield content
