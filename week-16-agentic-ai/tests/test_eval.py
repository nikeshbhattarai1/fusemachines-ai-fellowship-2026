"""Tests for the evaluation harness itself: if the harness is wrong, every number it reports is wrong."""
from __future__ import annotations

import dataclasses

import pytest

from app.agent.models import AgentConfig, AgentResult
from eval.cases import CASES, CASE_INDEX, Expect
from eval.metrics import check_expectations, classify_failure, evaluate_run, find_anomalies, summarize
from eval.run import make_cfg, offline_runner, run_suite, stress_scaling
from eval.scripts import SCRIPTS, compile_script, unresolved_refs
from eval.offline import build_offline_sources


def result(**kw):
    base = dict(status="verified", answer="The limit is 30 requests per minute.", claims=[], confidence=0.9, iterations=3,
                trajectory=[], usage={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12, "estimated": False})
    base.update(kw)
    return AgentResult(**base)


def test_every_case_has_a_script_and_every_reference_resolves():
    cfg = make_cfg(live=False)
    for c in CASES:
        assert c.id in SCRIPTS, f"no offline script for {c.id}"
        steps = compile_script(SCRIPTS[c.id], lambda c=c: build_offline_sources(c.fault, 1.5), cfg)
        unresolved = unresolved_refs(steps)
        # the fabricated-citation control is SUPPOSED to cite something that was never retrieved
        assert bool(unresolved) == (c.id == "control_fabricated_citation"), (c.id, unresolved)


@pytest.fixture(scope="module")
def offline_evals():
    return run_suite(CASES, offline_runner, make_cfg(False), "agent")


def test_offline_real_and_fault_cases_pass(offline_evals):
    bad = [(e.case_id, e.fail_reasons + e.selection_reasons) for e in offline_evals if not e.control and not e.passed]
    assert not bad, bad


def test_controls_are_caught_and_classified_correctly(offline_evals):
    for e in (x for x in offline_evals if x.control):
        assert not e.passed, f"{e.case_id} should have failed"
        assert e.failure_class == CASE_INDEX[e.case_id].expected_failure_class, (e.case_id, e.failure_class)


def test_fault_cases_never_assert_the_missing_value(offline_evals):
    e = next(x for x in offline_evals if x.case_id == "fault_search_timeout")
    assert e.degraded and "0.9" not in e.answer and e.status == "insufficient_evidence"


def test_ledger_saves_tokens_at_production_chunk_size():
    rows = {r["chunk_size"]: r for r in stress_scaling(make_cfg(False))}
    assert rows[800]["managed"] < 0.9 * rows[800]["raw"]       # README claims a double-digit saving here


# ------------------------------------------------------------------ classifier / checker unit tests
def traj(*steps):
    return [{"step": i + 1, "calls": calls} for i, calls in enumerate(steps)]


def test_classifier_hard_soft_cascading():
    ok = {"tool": "kb_search", "ok": True, "arg_valid": True}
    empty = {"tool": "kb_search", "ok": True, "arg_valid": True, "empty": True}
    assert classify_failure(False, False, result(status="error"), []) == "hard"
    assert classify_failure(False, False, result(status="budget_exhausted"), []) == "hard"
    clean = result(trajectory=traj([ok], [ok], [{"tool": "finish", "ok": True}]))
    assert classify_failure(False, False, clean, find_anomalies(clean)) == "soft"
    dirty = result(trajectory=traj([empty], [ok], [{"tool": "finish", "ok": True}]))
    assert classify_failure(False, False, dirty, find_anomalies(dirty)) == "cascading_soft"
    assert classify_failure(True, True, dirty, find_anomalies(dirty)) is None


def test_anomaly_detection_kinds():
    r = result(trajectory=traj(
        [{"tool": "kb_search", "ok": False, "arg_valid": False, "error_type": "invalid_arguments", "summary": "x"}],
        [{"tool": "kb_search", "ok": True, "error_type": "duplicate"}],
        [{"tool": "facts_lookup", "ok": False, "error_type": "timeout", "summary": "t"}],
        [{"tool": "finish", "ok": False, "verifier_issues": ["quote_not_in_evidence"]}]))
    assert [a["kind"] for a in find_anomalies(r)] == ["invalid_arguments", "duplicate_call", "timeout", "finish_rejected"]


def test_expectation_checks():
    exp = Expect(["verified"], [r"\b30\b"], answer_none=[r"\b60\b"], min_cited_sources=2, confidence_max=0.8,
                 verdicts_min={"supported": 1}, limitations_all=["registry"], degraded=True)
    r = result(answer="It is 60.", confidence=0.95, claims=[{"claim": "c", "verdict": "insufficient",
               "evidence": [{"id": "E1", "source": "a.md", "quote": "q"}]}], limitations=[], degraded=False)
    why = " | ".join(check_expectations(r, exp))
    for fragment in ("missing /\\b30\\b/", "forbidden", "cited 1", "degraded=False", "confidence 0.95", "limitations missing", "needs >= 1 'supported'"):
        assert fragment in why, fragment


def test_summarize_rates():
    c = CASE_INDEX["rate_limit_conflict"]
    good = evaluate_run(c, result(claims=[{"claim": "c", "verdict": "supported", "evidence": [
        {"id": "E1", "source": "a.md", "quote": "q"}, {"id": "E2", "source": "b.md", "quote": "q"}]}],
        trajectory=traj([{"tool": "kb_search", "ok": True, "arg_valid": True}], [{"tool": "facts_lookup", "ok": True, "arg_valid": True}],
                        [{"tool": "finish", "ok": True, "arg_valid": True}])), "agent")
    bad = evaluate_run(c, result(status="error"), "agent")
    s = summarize([good, bad])
    assert s["cases"] == 2 and s["task_completion_pct"] == 50.0 and s["failures"]["hard"] == 1
