"""Shared dataclasses for the agentic verification loop."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentConfig:
    # stopping conditions: the loop can never run indefinitely
    max_iterations: int = 8          # hard cap on LLM calls per request
    # soft cap: once exceeded, next call is forced to `finish`
    token_budget: int = 60_000
    timeout_seconds: float = 90.0    # wall-clock cap, same forcing behaviour
    tool_timeout_seconds: float = 10.0
    # grounding-gate rejections before we repair instead
    max_finish_rejections: int = 2
    max_nudges: int = 2              # "call a tool, don't reply in prose" reminders
    # context engineering
    # "managed" = evidence ledger; "raw" = W15-style ablation
    context_mode: str = "managed"
    ledger_max_entries: int = 20
    # must exceed the ingest chunk size (default 800) or evidence gets cut
    snippet_chars: int = 1000
    min_score: float = 0.2
    default_k: int = 4
    max_k: int = 6
    # generation
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 1200
    require_cross_source: bool = True

    @classmethod
    def from_settings(cls, s: Any) -> "AgentConfig":
        return cls(
            max_iterations=s.agent_max_iterations,
            token_budget=s.agent_token_budget,
            timeout_seconds=s.agent_timeout_seconds,
            tool_timeout_seconds=s.agent_tool_timeout_seconds,
            context_mode=s.agent_context_mode,
            ledger_max_entries=s.agent_ledger_max_entries,
            snippet_chars=s.agent_snippet_chars,
            min_score=s.agent_min_score,
            default_k=s.retrieval_k,
        )


# Tool failures that mean "a source is degraded" (as opposed to the model misusing a tool).
DEGRADING_ERRORS = {"unavailable", "timeout",
                    "malformed_output", "internal_error"}


@dataclass
class ToolOutcome:
    name: str
    args: Dict[str, Any]
    # exactly what is sent back to the model
    result: Dict[str, Any]
    ok: bool
    # invalid_arguments | unavailable | timeout | malformed_output | internal_error | duplicate
    error_type: Optional[str] = None
    summary: str = ""
    latency_ms: int = 0
    arg_valid: bool = True
    empty: bool = False                 # a search that produced nothing usable
    new_evidence: List[str] = field(default_factory=list)


@dataclass
class AgentState:
    step: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    usage_estimated: bool = False
    rejections: int = 0
    nudges: int = 0
    provider_used: str = "unknown"
    available_sources: Optional[List[str]] = None
    seen_calls: Dict[str, int] = field(default_factory=dict)
    unrecovered_failures: Dict[str, str] = field(
        default_factory=dict)  # tool -> last error
    failure_events: List[Dict[str, Any]] = field(default_factory=list)
    trajectory: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out


@dataclass
class AgentResult:
    # verified | partial | insufficient_evidence | needs_clarification | budget_exhausted | error
    status: str
    answer: str
    claims: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    limitations: List[str] = field(default_factory=list)
    degraded: bool = False
    clarification_question: Optional[str] = None
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    trajectory: List[Dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    # finished | asked_user | max_iterations | token_budget | timeout | error
    stop_reason: str = "finished"
    usage: Dict[str, Any] = field(default_factory=dict)
    provider_used: str = "unknown"
    repaired: bool = False          # final answer needed application-side downgrading
    error: Optional[str] = None
    latency_ms: int = 0
