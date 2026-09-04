from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Client-supplied id used for rate-limit/cache correlation")
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class RetrievedSource(BaseModel):
    text: str
    source: str
    score: float


class StructuredAnswer(BaseModel):
    """The JSON schema the model is forced to emit (via the `emit_answer` tool)
    as its final response. This is what guarantees valid, parseable JSON output
    regardless of provider."""
    answer: str
    sources: List[str] = Field(default_factory=list)
    used_tools: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    used_tools: List[str] = Field(default_factory=list)
    confidence: float
    provider_used: str
    cached: bool = False
    retrieved_context: List[RetrievedSource] = Field(default_factory=list)


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    chunks_indexed: int


class HealthResponse(BaseModel):
    status: str
    providers: Dict[str, Any]
