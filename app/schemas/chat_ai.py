from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str


class ChatStreamChunk(BaseModel):
    content: str
    full_response: str
    is_complete: bool
    session_id: str


class ChatHistory(BaseModel):
    role: str  # "user" or "assistant"
    message: str
    timestamp: str
