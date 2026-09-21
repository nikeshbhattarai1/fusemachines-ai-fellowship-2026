from __future__ import annotations

import re
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.agent.models import AgentResult
from eval.cases import Case, Expect


@dataclass
class CaseEval:
    case_id: str
    category: str
    mode: str                      # agent | agent_raw | single_pass
    control: bool
    fault: Optional[str]
    status: str
    stop_reason: str
    iterations: int
    iter_range: Tuple[int, int]
    in_range: bool
    completed: bool
    fail_reasons: List[str]
    tool_selection_ok: bool
    selection_reasons: List[str]
    calls_total: int
    calls_valid: int
    duplicate_calls: int
    grounding_rejections: int
    repaired: bool
    degraded: bool
    confidence: float
    cited_sources: int
    tokens_in: int
    tokens_out: int
    tokens_total: int
    tokens_estimated: bool
    latency_ms: int
    provider: str
    failure_class: Optional[str]
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    path: str = ""
    answer: str = ""

    @property
    def passed(self) -> bool:
        return self.completed and self.tool_selection_ok

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# per-run analysis
def _calls(result: AgentResult) -> List[Dict[str, Any]]:
    return [c for st in result.trajectory for c in st.get("calls", [])]


def tools_used(result: AgentResult) -> List[str]:
    return [c["tool"] for c in _calls(result)]


def find_anomalies(result: AgentResult) -> List[Dict[str, Any]]:
    """Steps where something went wrong or was wasted, whether or not the agent later recovered."""
    out: List[Dict[str, Any]] = []
    for st in result.trajectory:
        step = st.get("step", 0)
        for c in st.get("calls", []):
            if c["tool"] == "finish":
                if c.get("verifier_issues"):
                    out.append({"step": step, "kind": "finish_rejected",
                               "detail": ",".join(c["verifier_issues"])})
            elif not c.get("ok", True):
                out.append({"step": step, "kind": c.get("error_type") or "tool_error",
                           "detail": f"{c['tool']}: {c.get('summary', '')}"[:100]})
            elif c.get("error_type") == "duplicate":
                out.append(
                    {"step": step, "kind": "duplicate_call", "detail": c["tool"]})
            elif c.get("empty"):
                out.append({"step": step, "kind": "empty_result",
                           "detail": f"{c['tool']}: {c.get('args')}"[:100]})
        if st.get("note") == "no tool call":
            out.append({"step": step, "kind": "no_tool_call", "detail": ""})
    return out


def check_expectations(result: AgentResult, exp: Expect) -> List[str]:
    """Task-completion checks. Returns the list of failed checks (empty == completed)."""
    why: List[str] = []
    if result.status not in exp.status_in:
        why.append(f"status {result.status!r} not in {exp.status_in}")
    for pat in exp.answer_all:
        if not re.search(pat, result.answer, re.I):
            why.append(f"answer missing /{pat}/")
    for pat in exp.answer_none:
        if re.search(pat, result.answer, re.I):
            why.append(f"answer contains forbidden /{pat}/")
    cited = {e["source"] for c in result.claims for e in c.get(
        "evidence", []) if e["source"] != "calculator"}
    if len(cited) < exp.min_cited_sources:
        why.append(
            f"cited {len(cited)} independent source(s), need {exp.min_cited_sources}")
    if exp.degraded is not None and result.degraded != exp.degraded:
        why.append(f"degraded={result.degraded}, expected {exp.degraded}")
    if exp.confidence_max is not None and result.confidence > exp.confidence_max:
        why.append(
            f"confidence {result.confidence} above cap {exp.confidence_max}")
    lim = " ".join(result.limitations)
    for pat in exp.limitations_all:
        if not re.search(pat, lim, re.I):
            why.append(f"limitations missing /{pat}/")
    counts: Dict[str, int] = {}
    for c in result.claims:
        counts[c["verdict"]] = counts.get(c["verdict"], 0) + 1
    for verdict, n in exp.verdicts_min.items():
        if counts.get(verdict, 0) < n:
            why.append(
                f"needs >= {n} '{verdict}' claim(s), got {counts.get(verdict, 0)}")
    return why


def check_tool_selection(result: AgentResult, exp: Expect) -> List[str]:
    used = set(tools_used(result))
    why = [
        f"never used required tool {t}" for t in exp.must_use if t not in used]
    why += [f"used forbidden tool {t}" for t in exp.must_not_use if t in used]
    return why


def classify_failure(passed: bool, completed: bool, result: AgentResult, anomalies: List[Dict[str, Any]]) -> Optional[str]:
    if passed:
        return None
    if not completed and result.status in ("error", "budget_exhausted"):
        return "hard"
    earlier = [a for a in anomalies if a["step"] < result.iterations]
    return "cascading_soft" if earlier else "soft"


def evaluate_run(case: Case, result: AgentResult, mode: str) -> CaseEval:
    calls = _calls(result)
    non_terminal = [c for c in calls if c["tool"] not in ("finish",)]
    all_calls = calls
    anomalies = find_anomalies(result)
    why = check_expectations(result, case.expect)
    sel = check_tool_selection(result, case.expect)
    completed, sel_ok = not why, not sel
    lo, hi = case.expect.iter_range
    cited = {e["source"] for c in result.claims for e in c.get(
        "evidence", []) if e["source"] != "calculator"}
    path = " > ".join(t for t in tools_used(result)) or "(none)"
    return CaseEval(
        case_id=case.id, category=case.category, mode=mode, control=case.control, fault=case.fault,
        status=result.status, stop_reason=result.stop_reason, iterations=result.iterations, iter_range=(
            lo, hi),
        in_range=lo <= result.iterations <= hi, completed=completed, fail_reasons=why,
        tool_selection_ok=sel_ok, selection_reasons=sel,
        calls_total=len(all_calls), calls_valid=sum(1 for c in all_calls if c.get("arg_valid", True)),
        duplicate_calls=sum(1 for c in non_terminal if c.get(
            "error_type") == "duplicate"),
        grounding_rejections=sum(
            1 for a in anomalies if a["kind"] == "finish_rejected"),
        repaired=result.repaired, degraded=result.degraded, confidence=result.confidence, cited_sources=len(
            cited),
        tokens_in=result.usage.get("input_tokens", 0), tokens_out=result.usage.get("output_tokens", 0),
        tokens_total=result.usage.get("total_tokens", 0), tokens_estimated=bool(result.usage.get("estimated")),
        latency_ms=result.latency_ms, provider=result.provider_used,
        failure_class=classify_failure(
            completed and sel_ok, completed, result, anomalies),
        anomalies=anomalies, path=path, answer=result.answer[:400],
    )


# aggregation
def _rate(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def summarize(evals: List[CaseEval]) -> Dict[str, Any]:
    n = len(evals)
    calls, valid = sum(e.calls_total for e in evals), sum(
        e.calls_valid for e in evals)
    toks = [e.tokens_total for e in evals]
    iters = [e.iterations for e in evals]
    return {
        "cases": n,
        "task_completion_pct": _rate(sum(e.completed for e in evals), n),
        "tool_selection_pct": _rate(sum(e.tool_selection_ok for e in evals), n),
        "tool_arg_validity_pct": _rate(valid, calls),
        "passed_pct": _rate(sum(e.passed for e in evals), n),
        "iterations_mean": round(statistics.mean(iters), 2) if iters else 0,
        "iterations_median": statistics.median(iters) if iters else 0,
        "iterations_max": max(iters) if iters else 0,
        "in_expected_range_pct": _rate(sum(e.in_range for e in evals), n),
        "tokens_mean": int(statistics.mean(toks)) if toks else 0,
        "tokens_total": sum(toks),
        "tokens_estimated_any": any(e.tokens_estimated for e in evals),
        "grounding_rejections": sum(e.grounding_rejections for e in evals),
        "repaired_runs": sum(e.repaired for e in evals),
        "duplicate_calls": sum(e.duplicate_calls for e in evals),
        "failures": {k: sum(1 for e in evals if e.failure_class == k) for k in ("hard", "soft", "cascading_soft")},
    }
