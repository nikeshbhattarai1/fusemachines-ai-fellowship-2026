from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.agent.ledger import EvidenceLedger, normalize_text
from app.agent.tools import VERDICTS

MIN_QUOTE_CHARS = 10
NEEDS_EVIDENCE = {"supported", "contradicted", "conflicting"}


@dataclass
class Issue:
    code: str
    message: str


@dataclass
class ClaimResult:
    claim: str
    verdict: str
    evidence: List[Dict[str, str]] = field(default_factory=list)   # [{id, source, quote}]
    sources: List[str] = field(default_factory=list)
    corroborated: bool = False                                     # backed by >=2 distinct sources
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Evaluation:
    issues: List[Issue]
    claims: List[ClaimResult]
    answer: str
    limitations: List[str]
    model_confidence: float
    cross_source_ok: bool = True


def evaluate_finish(
    payload: Any,
    ledger: EvidenceLedger,
    *,
    available_sources: Optional[List[str]],
    require_cross_source: bool = True,
) -> Evaluation:
    """Never raises. Returns issues (for rejection) AND a repaired claim list (for graceful acceptance)."""
    issues: List[Issue] = []
    payload = payload if isinstance(payload, dict) else {}
    answer = payload.get("answer") if isinstance(payload.get("answer"), str) else ""
    if not answer.strip():
        issues.append(Issue("empty_answer", "`answer` is empty."))

    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        issues.append(Issue("no_claims", "Provide at least one claim with a verdict and evidence."))
        raw_claims = []

    claims: List[ClaimResult] = []
    for idx, rc in enumerate(raw_claims, start=1):
        rc = rc if isinstance(rc, dict) else {}
        text = rc.get("claim") if isinstance(rc.get("claim"), str) else ""
        verdict = rc.get("verdict")
        label = f"claim {idx}"
        if not text.strip():
            issues.append(Issue("empty_claim", f"{label}: `claim` text is empty."))
        if verdict not in VERDICTS:
            issues.append(Issue("bad_verdict", f"{label}: verdict must be one of {VERDICTS}."))
            verdict = "insufficient"

        valid: List[Dict[str, str]] = []
        for ev_ref in rc.get("evidence") or []:
            ev_ref = ev_ref if isinstance(ev_ref, dict) else {"id": str(ev_ref), "quote": ""}
            ev_id, quote = str(ev_ref.get("id", "")), str(ev_ref.get("quote", ""))
            ev = ledger.get(ev_id)
            if ev is None:
                issues.append(Issue("unknown_evidence_id", f"{label}: evidence id '{ev_id}' is not in the ledger."))
                continue
            nq = normalize_text(quote)
            if len(nq) < MIN_QUOTE_CHARS:
                issues.append(Issue("quote_too_short", f"{label}: quote for {ev_id} must be at least {MIN_QUOTE_CHARS} characters of exact text."))
                continue
            if nq not in normalize_text(ev.text):
                issues.append(Issue("quote_not_in_evidence",
                                    f"{label}: quote {quote[:60]!r} does not appear in {ev_id}. Copy the words exactly."))
                continue
            valid.append({"id": ev.id, "source": ev.source, "quote": quote.strip()})

        sources = sorted({v["source"] for v in valid})
        # derived values (calculator) are not independent sources of truth
        independent = {v["source"] for v in valid if (ledger.get(v["id"]) and ledger.get(v["id"]).kind != "calc")}
        note = rc.get("note") if isinstance(rc.get("note"), str) else ""
        if verdict in NEEDS_EVIDENCE:
            if not valid:
                issues.append(Issue("missing_evidence", f"{label}: a '{verdict}' verdict needs at least one valid evidence citation."))
                verdict, note = "insufficient", (note + " Downgraded: no valid citation.").strip()
            elif verdict == "conflicting" and len(independent) < 2:
                issues.append(Issue("conflict_needs_two_sources", f"{label}: 'conflicting' must cite evidence from two different sources."))
                verdict, note = "insufficient", (note + " Downgraded: conflict not shown across two sources.").strip()
        claims.append(ClaimResult(text.strip(), verdict, valid, sources, corroborated=len(independent) >= 2, note=note))

    attempted = ledger.sources_attempted
    cross_ok = True
    if require_cross_source and available_sources is not None and len(available_sources) >= 2 and len(attempted) < 2:
        cross_ok = False
        issues.append(Issue("single_source_consulted",
                            f"Only {len(attempted)} source consulted ({sorted(attempted) or 'none'}), but "
                            f"{len(available_sources)} exist. Cross-check with a different source, or explain why it "
                            "cannot help by searching it and reporting the result."))

    limitations = [str(x) for x in payload.get("limitations", []) if isinstance(x, str)] if isinstance(payload.get("limitations"), list) else []
    try:
        conf = float(payload.get("confidence", 0.5))
    except (TypeError, ValueError):
        conf = 0.5
    return Evaluation(issues, claims, answer.strip(), limitations, max(0.0, min(1.0, conf)), cross_ok)


def derive_status(claims: List[ClaimResult], degraded: bool) -> str:
    if not claims or all(c.verdict == "insufficient" for c in claims):
        return "insufficient_evidence"
    if all(c.verdict in ("supported", "contradicted") for c in claims) and not degraded:
        return "verified"
    return "partial"


def final_confidence(model_conf: float, claims: List[ClaimResult], degraded: bool, repaired: bool) -> float:
    """The application, not the model, has the last word on how confident an answer may be."""
    c = model_conf
    if degraded or repaired or any(x.verdict in ("insufficient", "conflicting") for x in claims):
        c = min(c, 0.6)
    if any(x.verdict in ("supported", "contradicted") and not x.corroborated for x in claims):
        c = min(c, 0.75)
    return round(c, 2)
