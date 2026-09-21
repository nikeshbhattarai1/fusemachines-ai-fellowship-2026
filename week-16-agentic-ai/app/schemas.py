from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

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


# ------------------------------------------------------------------ W16: /verify (agentic loop)
class VerifyRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, max_length=128)
    message: str = Field(min_length=1, max_length=8000)
    history: List[ChatMessage] = Field(default_factory=list)


class EvidenceRef(BaseModel):
    id: str
    source: str
    quote: str


class ClaimVerdict(BaseModel):
    claim: str
    verdict: Literal["supported", "contradicted", "conflicting", "insufficient"]
    evidence: List[EvidenceRef] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    corroborated: bool = False
    note: str = ""


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated: bool = False


class VerifyResponse(BaseModel):
    status: Literal["verified", "partial", "insufficient_evidence", "needs_clarification", "budget_exhausted", "error"]
    answer: str
    claims: List[ClaimVerdict] = Field(default_factory=list)
    confidence: float = 0.0
    limitations: List[str] = Field(default_factory=list)
    degraded: bool = False
    clarification_question: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    trajectory: List[Dict[str, Any]] = Field(default_factory=list)
    iterations: int = 0
    stop_reason: str = "finished"
    usage: TokenUsage = Field(default_factory=TokenUsage)
    provider_used: str = "unknown"
    repaired: bool = False
    latency_ms: int = 0
