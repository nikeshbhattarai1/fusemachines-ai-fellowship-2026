from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Expect:
    status_in: List[str]
    # regexes (case-insensitive) that must match the answer
    answer_all: List[str] = field(default_factory=list)
    # regexes that must NOT match (e.g. a fabricated value)
    answer_none: List[str] = field(default_factory=list)
    # tools that must be called at least once
    must_use: List[str] = field(default_factory=list)
    must_not_use: List[str] = field(default_factory=list)
    # "reasonable" number of LLM iterations for this query
    iter_range: Tuple[int, int] = (1, 8)
    # distinct independent sources across all claim evidence
    min_cited_sources: int = 0
    degraded: Optional[bool] = None
    confidence_max: Optional[float] = None
    # regexes over the joined limitations text
    limitations_all: List[str] = field(default_factory=list)
    verdicts_min: Dict[str, int] = field(default_factory=dict)


@dataclass
class Case:
    id: str
    category: str
    question: str
    expect: Expect
    history: List[Dict[str, str]] = field(default_factory=list)
    # e.g. "unavailable:facts_lookup"
    fault: Optional[str] = None
    # harness self-test (deliberately bad agent), offline only
    control: bool = False
    # what the classifier must say for a control
    expected_failure_class: Optional[str] = None


NEG = r"(not documented|no source|could not (find|verify)|couldn't (find|verify)|cannot verify|no information|insufficient|unable to verify|not found)"

CASES: List[Case] = [
    Case("rate_limit_conflict", "conflict resolution", "What is the API rate limit per client?",
         Expect(["verified"], [r"\b30\b"], must_use=["kb_search", "facts_lookup"], iter_range=(2, 5), min_cited_sources=2,
                verdicts_min={"supported": 1})),
    Case("cache_ttl_conflict", "conflict resolution", "How long are chat responses cached?",
         Expect(["verified"], [r"3600|one hour|1 hour"], must_use=["kb_search"], iter_range=(2, 6), min_cited_sources=2)),
    Case("provider_order", "cross-check", "In what order does the assistant fall back between LLM providers?",
         Expect(["verified"], [r"groq"], must_use=["kb_search"], iter_range=(2, 7), min_cited_sources=2)),
    Case("single_source_fact", "cross-check", "What GPU memory utilization does the local vLLM server use?",
         Expect(["verified", "partial"], [r"0\.9"], must_use=["kb_search"], iter_range=(2, 5), min_cited_sources=1,
                confidence_max=0.75)),
    Case("unanswerable", "insufficient evidence", "What is the maximum file size accepted by the ingest endpoint?",
         Expect(["insufficient_evidence"], [NEG], answer_none=[r"\b\d+\s?(mb|kb|gb)\b"], iter_range=(2, 5),
                verdicts_min={"insufficient": 1})),
    Case("false_premise_calc", "false premise", "Since the rate limit is 100 requests per minute, how many requests can one client send in 5 minutes?",
         Expect(["verified", "partial"], [r"\b150\b", r"\b30\b"], must_use=["calculator"], iter_range=(3, 6),
                verdicts_min={"contradicted": 1})),
    Case("calc_ttl_factor", "arithmetic over evidence", "By what factor did the cache TTL increase between v0.9 and the current version?",
         Expect(["verified", "partial"], [r"\b6\b|six"], must_use=["kb_search", "calculator"], iter_range=(2, 5))),
    Case("ambiguous", "clarification", "What is the limit?",
         Expect(["needs_clarification"], must_use=["ask_user"], iter_range=(1, 2))),
    Case("multi_claim", "multi-claim", "Verify: provider calls are retried up to 3 times, the circuit breaker cooldown is 60 seconds, and the default temperature is 0.9.",
         Expect(["verified", "partial"], [r"0\.4"], must_use=["facts_lookup"], iter_range=(3, 7),
                verdicts_min={"supported": 2, "contradicted": 1})),
    Case("historical_v09", "conflict resolution", "What was the circuit breaker cooldown in v0.9?",
         Expect(["verified"], [r"\b30\b"], must_use=["kb_search"], iter_range=(1, 5), min_cited_sources=2)),
    Case("multi_turn_followup", "multi-turn", "The API rate limit per client.",
         Expect(["verified"], [r"\b30\b"], must_use=["kb_search"],
                iter_range=(2, 5), min_cited_sources=2),
         history=[{"role": "user", "content": "What is the limit?"},
                  {"role": "assistant", "content": "Which limit do you mean: the API rate limit, the cache TTL, or something else?"}]),
    Case("reformulation", "query reformulation", "How many times will the system re-attempt a failed model call before giving up?",
         Expect(["verified"], [r"\b3\b|three"], must_use=["kb_search"], iter_range=(2, 6), min_cited_sources=2)),

    # ---- context stress: five overlapping re-searches, the regime the evidence ledger is designed for ----
    Case("stress_overlapping_searches", "context stress",
         "Summarise the current rate limit, cache TTL, retry attempts, circuit breaker cooldown and chunk size, checking each against the documents.",
         Expect(["verified"], [r"\b30\b", r"3600", r"\b3\b", r"\b60\b", r"\b800\b"], must_use=["kb_search"], iter_range=(4, 8), min_cited_sources=2,
                verdicts_min={"supported": 5})),

    # ---- failure injection: the harness makes ONE source misbehave and checks the run degrades honestly ----
    Case("fault_registry_unavailable", "failure injection", "What is the API rate limit per client?",
         Expect(["partial"], [r"\b30\b"], degraded=True, confidence_max=0.6, limitations_all=[r"facts_lookup"],
                iter_range=(2, 6)), fault="unavailable:facts_lookup"),
    Case("fault_search_malformed", "failure injection", "How long are chat responses cached?",
         Expect(["partial"], [r"3600|one hour|1 hour"], degraded=True, confidence_max=0.6, limitations_all=[r"kb_search"],
                iter_range=(2, 6)), fault="malformed:kb_search"),
    Case("fault_search_timeout", "failure injection", "What GPU memory utilization does the local vLLM server use?",
         Expect(["insufficient_evidence", "partial"], [NEG], answer_none=[r"0\.9"], degraded=True, confidence_max=0.6,
                limitations_all=[r"kb_search"], iter_range=(2, 6)), fault="timeout:kb_search"),

    # ---- harness self-tests: deliberately bad agents; the classifier must label them correctly ----
    Case("control_fabricated_citation", "control", "What is the API rate limit per client?",
         Expect(["verified"], [r"\b30\b"], iter_range=(2, 5)), control=True, expected_failure_class="cascading_soft"),
    Case("control_stale_source", "control", "What is the API rate limit per client?",
         Expect(["verified"], [r"\b30\b"], answer_none=[r"\b60\b"], iter_range=(2, 5)), control=True, expected_failure_class="soft"),
    Case("control_never_finishes", "control", "What is the API rate limit per client?",
         Expect(["verified"], [r"\b30\b"], iter_range=(2, 5)), control=True, expected_failure_class="hard"),
]

CASE_INDEX = {c.id: c for c in CASES}
