from pydantic import BaseModel
from typing import List, Optional


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[Message]


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    id: str
    object: str
    created: int
    choices: List[Choice]
    usage: Usage
