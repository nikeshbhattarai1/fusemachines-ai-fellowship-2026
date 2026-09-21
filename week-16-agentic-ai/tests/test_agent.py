"""Tests for the W16 agent. All offline: lexical retriever + scripted LLM, no network, no embedding model."""
from __future__ import annotations

import json

import pytest

from app.agent.ledger import EvidenceLedger, normalize_text
from app.agent.loop import run_agent
from app.agent.models import AgentConfig, AgentState
from app.agent.runner import ToolRunner
from app.agent.tools import validate_args
from app.agent.verifier import derive_status, evaluate_finish, final_confidence
from eval.offline import build_offline_sources
from eval.scripted_llm import ExplodingLLM, ScriptedLLM, call

Q = "What is the API rate limit per client?"
SEARCH = call("kb_search", query="rate limit per client requests per minute")
FACTS = call("facts_lookup", entity="rate limiter", attribute="requests per minute")

# ids are deterministic for SEARCH then FACTS: E1 release_notes, E2 runbook(60), E3 architecture, E4 facts registry
GOOD_CLAIMS = [
    {"claim": "Current rate limit is 30 requests/minute per client", "verdict": "supported", "evidence": [
        {"id": "E1", "quote": "lowered from 60 to 30 requests per minute per client"},
        {"id": "E4", "quote": "requests_per_minute = 30"}]},
    {"claim": "The v0.9 runbook value of 60/min is outdated", "verdict": "supported", "evidence": [
        {"id": "E2", "quote": "limited to 60 requests per minute"}, {"id": "E1", "quote": "lowered from 60 to 30"}]},
]


def finish(claims=None, answer="The limit is 30 requests per minute.", confidence=0.9, **extra):
    return call("finish", answer=answer, claims=GOOD_CLAIMS if claims is None else claims, confidence=confidence, **extra)


@pytest.fixture
def sources():
    return build_offline_sources()


def run(steps, sources, **cfg):
    llm = ScriptedLLM(steps)
    return llm, run_agent(Q, [], llm, sources, AgentConfig(**cfg))


def tool_results_seen(llm):
    """All tool_result payloads (parsed) the model was shown, in order."""
    out = []
    for msgs in llm.seen_messages:
        for m in msgs:
            if isinstance(m["content"], list):
                out += [json.loads(b["content"]) for b in m["content"] if b.get("type") == "tool_result"]
    return out


# ledger
def test_ledger_dedup_cap_and_truncate():
    led = EvidenceLedger(max_entries=2, snippet_chars=20)
    a, st = led.add(source="a", kind="document", text="hello   world this is a long passage of text")
    assert st == "added" and a.id == "E1" and a.meta.get("truncated") == "true" and len(a.text) <= 20
    dup, st = led.add(source="a", kind="document", text="hello world this is a long passage of text")
    assert st == "duplicate" and dup.id == "E1"
    same_text_other_source, st = led.add(source="b", kind="document", text="hello world this is a long passage of text")
    assert st == "added"
    none, st = led.add(source="c", kind="document", text="third")
    assert none is None and st == "dropped_cap"


def test_normalize_text_ignores_markdown_and_case():
    assert normalize_text("The **Limit**  is `30`") == "the limit is 30"


def test_validate_args():
    assert validate_args("kb_search", {"query": "x"}) == []
    assert validate_args("kb_search", {}) and validate_args("kb_search", {"query": 3})
    assert validate_args("nope", {})


# runner
def make_runner(sources, **cfg):
    c = AgentConfig(**cfg)
    st = AgentState()
    return ToolRunner(sources, EvidenceLedger(c.ledger_max_entries, c.snippet_chars), c, st), st


def test_runner_invalid_args_and_duplicate_calls(sources):
    r, _ = make_runner(sources)
    bad = r.run("kb_search", {"query": 5}, 1)
    assert not bad.ok and not bad.arg_valid and bad.error_type == "invalid_arguments"
    first = r.run("kb_search", {"query": "rate limit"}, 1)
    again = r.run("kb_search", {"query": "rate limit"}, 2)
    assert first.ok and again.result.get("duplicate_call") and again.error_type == "duplicate"


def test_runner_calculator_error_is_model_error_not_degradation(sources):
    r, st = make_runner(sources)
    out = r.run("calculator", {"expression": "import os"}, 1)
    assert not out.ok and out.error_type == "invalid_arguments" and not st.unrecovered_failures
    ok = r.run("calculator", {"expression": "3600 / 600"}, 1)
    assert ok.ok and ok.result["result"] == 6


@pytest.mark.parametrize("mode,expected", [("unavailable", "unavailable"), ("malformed", "malformed_output"), ("timeout", "timeout")])
def test_runner_normalises_source_failures(mode, expected):
    src = build_offline_sources(fault=f"{mode}:facts_lookup", fault_sleep=1.0)
    r, st = make_runner(src, tool_timeout_seconds=0.2)
    out = r.run("facts_lookup", {"entity": "rate limiter"}, 1)
    assert not out.ok and out.error_type == expected
    assert "facts_lookup" in st.unrecovered_failures
    assert "Do NOT guess" in out.result["hint"]
    # a working source recovers the state
    r2, st2 = make_runner(build_offline_sources())
    assert r2.run("facts_lookup", {"entity": "rate limiter"}, 1).ok and not st2.unrecovered_failures


def test_facts_lookup_unknown_entity_suggests_known_ones(sources):
    r, _ = make_runner(sources)
    out = r.run("facts_lookup", {"entity": "quantum flux"}, 1)
    assert out.ok and out.empty and "rate_limiter" in out.result["known_entities"]


def test_kb_search_source_filter(sources):
    r, _ = make_runner(sources)
    out = r.run("kb_search", {"query": "requests per minute", "source": "ops_runbook_v0_9.md"}, 1)
    assert out.ok and {a["source"] for a in out.result["added"]} == {"ops_runbook_v0_9.md"}


# verifier
def _ledger_after(sources):
    r, st = make_runner(sources)
    r.run("kb_search", SEARCH["input"], 1)
    r.run("facts_lookup", FACTS["input"], 2)
    return r.ledger, st


def test_verifier_accepts_grounded_claims(sources):
    led, _ = _ledger_after(sources)
    ev = evaluate_finish({"answer": "30/min", "claims": GOOD_CLAIMS, "confidence": 0.9}, led, available_sources=sources.source_names())
    assert not ev.issues and all(c.corroborated for c in ev.claims)


@pytest.mark.parametrize("bad_evidence,code", [
    ([{"id": "E99", "quote": "requests_per_minute = 30"}], "unknown_evidence_id"),
    ([{"id": "E1", "quote": "the limit is one million requests per hour"}], "quote_not_in_evidence"),
    ([{"id": "E1", "quote": "30"}], "quote_too_short"),
])
def test_verifier_rejects_ungrounded_citations(sources, bad_evidence, code):
    led, _ = _ledger_after(sources)
    payload = {"answer": "x", "confidence": 0.9, "claims": [{"claim": "c", "verdict": "supported", "evidence": bad_evidence}]}
    ev = evaluate_finish(payload, led, available_sources=sources.source_names())
    codes = {i.code for i in ev.issues}
    assert code in codes and "missing_evidence" in codes
    assert ev.claims[0].verdict == "insufficient"          # repaired, never shown as supported


def test_verifier_conflicting_needs_two_sources(sources):
    led, _ = _ledger_after(sources)
    one = [{"id": "E1", "quote": "lowered from 60 to 30 requests"}]
    ev = evaluate_finish({"answer": "x", "confidence": 0.5, "claims": [{"claim": "c", "verdict": "conflicting", "evidence": one}]},
                         led, available_sources=None)
    assert "conflict_needs_two_sources" in {i.code for i in ev.issues}


def test_cross_source_gate(sources):
    r, _ = make_runner(sources)
    r.run("kb_search", {"query": "vLLM GPU memory utilization", "source": "vllm_deployment.md"}, 1)
    ev = evaluate_finish({"answer": "0.90", "confidence": 0.9, "claims": [
        {"claim": "GPU util 0.90", "verdict": "supported", "evidence": [{"id": "E1", "quote": "GPU memory utilization of 0.90"}]}]},
        r.ledger, available_sources=sources.source_names())
    assert [i.code for i in ev.issues] == ["single_source_consulted"]


def test_status_and_confidence_policy(sources):
    led, _ = _ledger_after(sources)
    ev = evaluate_finish({"answer": "a", "confidence": 0.99, "claims": GOOD_CLAIMS}, led, available_sources=None)
    assert derive_status(ev.claims, degraded=False) == "verified"
    assert derive_status(ev.claims, degraded=True) == "partial"
    assert final_confidence(0.99, ev.claims, degraded=True, repaired=False) == 0.6
    assert final_confidence(0.99, ev.claims, degraded=False, repaired=False) == 0.99


# loop
def test_multi_iteration_happy_path(sources):
    llm, res = run([{"calls": [SEARCH]}, {"calls": [FACTS]}, {"calls": [finish()]}], sources)
    assert res.status == "verified" and res.iterations == 3 and res.stop_reason == "finished" and not res.repaired
    assert res.confidence == 0.9 and not res.degraded
    assert [len(t["calls"]) for t in res.trajectory] == [1, 1, 1]
    assert res.usage["estimated"] is True and res.usage["total_tokens"] > 0


def test_provider_reported_usage_is_used_verbatim(sources):
    llm = ScriptedLLM([{"calls": [SEARCH]}, {"calls": [FACTS]}, {"calls": [finish()]}], usage={"input_tokens": 100, "output_tokens": 10})
    res = run_agent(Q, [], llm, sources, AgentConfig())
    assert res.usage == {"input_tokens": 300, "output_tokens": 30, "total_tokens": 330, "estimated": False}


def test_fabricated_quote_is_rejected_then_recovers(sources):
    bad = finish(claims=[{"claim": "c", "verdict": "supported", "evidence": [{"id": "E1", "quote": "the limit is 500 requests per second"}]}])
    llm, res = run([{"calls": [SEARCH]}, {"calls": [FACTS]}, {"calls": [bad]}, {"calls": [finish()]}], sources)
    assert res.status == "verified" and res.iterations == 4 and not res.repaired
    rejection = [r for r in tool_results_seen(llm) if r.get("error_type") == "finish_rejected"]
    assert rejection and rejection[0]["issues"][0]["code"] == "quote_not_in_evidence"


def test_persistent_bad_finish_is_repaired_not_trusted(sources):
    bad = finish(claims=[{"claim": "c", "verdict": "supported", "evidence": [{"id": "E1", "quote": "the limit is 500 requests per second"}]}])
    llm, res = run([{"calls": [SEARCH]}, {"calls": [FACTS]}, {"calls": [bad]}], sources)   # script repeats the bad finish
    assert res.repaired and res.status == "insufficient_evidence" and res.confidence <= 0.6
    assert res.claims[0]["verdict"] == "insufficient"
    assert "downgraded" in res.answer.lower()


def test_ask_user_stops_the_loop(sources):
    llm, res = run([{"calls": [call("ask_user", question="Which limit do you mean?")]}], sources)
    assert res.status == "needs_clarification" and res.iterations == 1 and res.stop_reason == "asked_user"
    assert res.clarification_question == "Which limit do you mean?"


def test_max_iterations_forces_finish_and_terminates(sources):
    steps = [{"calls": [call("kb_search", query=f"rate limit variation {i}")]} for i in range(20)]
    llm, res = run(steps, sources, max_iterations=4)
    assert res.iterations == 4 and res.status == "budget_exhausted" and res.stop_reason == "max_iterations"
    assert llm.seen_tool_choice == [None, None, None, "finish"]      # last call is forced
    assert res.confidence == 0.0 and "No conclusion is asserted" in res.answer


def test_forced_final_call_can_still_produce_a_verified_answer(sources):
    steps = [{"calls": [SEARCH]}, {"calls": [FACTS]}, {"calls": [finish()]}]
    llm, res = run(steps, sources, max_iterations=3)
    assert llm.seen_tool_choice[-1] == "finish" and res.status == "verified"


def test_token_budget_forces_finish(sources):
    steps = [{"calls": [SEARCH]}, {"calls": [FACTS]}, {"calls": [finish()]}]
    llm, res = run(steps, sources, token_budget=1)
    assert llm.seen_tool_choice[1] == "finish" and res.stop_reason == "token_budget"


def test_prose_instead_of_tool_call_is_nudged_then_fails_gracefully(sources):
    llm, res = run([{"text": "The limit is 30."}], sources)
    assert res.status == "error" and res.stop_reason == "error" and res.iterations == 3   # 1 + 2 nudges tolerated
    assert res.confidence == 0.0


def test_llm_outage_degrades_gracefully(sources):
    res = run_agent(Q, [], ExplodingLLM(), sources, AgentConfig())
    assert res.status == "error" and "no language model available" in res.answer


def test_history_is_passed_for_multi_turn(sources):
    hist = [{"role": "user", "content": "What is the limit?"}, {"role": "assistant", "content": "Which limit?"}]
    llm = ScriptedLLM([{"calls": [call("ask_user", question="x")]}])
    run_agent("The rate limit.", hist, llm, sources, AgentConfig())
    roles = [m["role"] for m in llm.seen_messages[0]]
    assert roles == ["system", "user", "assistant", "user"]


# failure injection
@pytest.mark.parametrize("mode", ["unavailable", "malformed", "timeout"])
def test_failed_source_is_disclosed_and_caps_confidence(mode):
    src = build_offline_sources(fault=f"{mode}:facts_lookup", fault_sleep=1.0)
    only_kb = [{"claim": "Current rate limit is 30/min", "verdict": "supported", "evidence": [
        {"id": "E1", "quote": "lowered from 60 to 30 requests per minute per client"},
        {"id": "E3", "quote": "limited to 30 requests per minute"}]}]
    steps = [{"calls": [SEARCH]}, {"calls": [FACTS]}, {"calls": [finish(claims=only_kb, confidence=0.95)]}]
    llm, res = run(steps, src, tool_timeout_seconds=0.2)
    assert res.degraded and res.status == "partial" and res.confidence <= 0.6
    assert any("facts_lookup" in l for l in res.limitations) and "Limitations:" in res.answer
    failed = [r for r in tool_results_seen(llm) if r.get("ok") is False]
    assert failed and failed[0]["error_type"] in ("unavailable", "malformed_output", "timeout")
    assert "Source failures (not recovered)" in llm.seen_messages[2][0]["content"]


def test_source_that_never_recovers_is_disclosed():
    src = build_offline_sources(fault="unavailable:kb_search")
    llm = ScriptedLLM([{"calls": [SEARCH]}, {"calls": [FACTS]}, {"calls": [finish(claims=[GOOD_CLAIMS[0]])]}])
    res = run_agent(Q, [], llm, src, AgentConfig())
    assert res.degraded      # kb_search never recovered -> disclosed


# context engineering ablation
def test_managed_context_is_smaller_and_hides_raw_text_in_tool_results(sources):
    steps = [{"calls": [call("kb_search", query=q)]} for q in
             ["rate limit per client requests per minute", "client limited requests minute", "requests per minute limit",
              "rate limiting per client"]] + [{"calls": [FACTS]}, {"calls": [finish()]}]
    # NOTE: raw and managed must see identical ledger ids for the same script
    managed_llm, managed = run(steps, sources, context_mode="managed")
    raw_llm, raw = run(steps, build_offline_sources(), context_mode="raw")
    assert managed.status == raw.status
    assert managed.usage["total_tokens"] < raw.usage["total_tokens"]
    first_managed = tool_results_seen(managed_llm)[0]
    first_raw = tool_results_seen(raw_llm)[0]
    assert "text" not in json.dumps(first_managed["added"]) and all("text" in r for r in first_raw["results"])
    assert "Evidence ledger" in managed_llm.seen_messages[-1][0]["content"]
    assert "Evidence ledger" not in raw_llm.seen_messages[-1][0]["content"]


# API route
def test_verify_route_end_to_end(monkeypatch, sources):
    from fastapi.testclient import TestClient

    import app.api.routes as routes
    from app.config import get_settings
    from app.main import app

    llm = ScriptedLLM([{"calls": [SEARCH]}, {"calls": [FACTS]}, {"calls": [finish()]}])

    class Wrapper:                       # FallbackLLMClient returns (response, provider) -- same as ScriptedLLM
        def chat(self, **kw):
            return llm.chat(**kw)

    monkeypatch.setattr(routes, "get_llm_client", lambda: Wrapper())
    monkeypatch.setattr(routes, "get_agent_sources", lambda: sources)
    client = TestClient(app)
    r = client.post(f"{get_settings().api_prefix}/verify", json={"session_id": "t1", "message": Q})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "verified" and body["iterations"] == 3 and len(body["claims"]) == 2
    assert body["usage"]["total_tokens"] > 0 and body["claims"][0]["evidence"][0]["quote"]


# regressions found while building the harness
def test_calculator_is_not_an_independent_source(sources):
    r, _ = make_runner(sources)
    r.run("kb_search", {"query": "cache TTL raised from 600 seconds to 3600 seconds", "source": "release_notes.md"}, 1)
    r.run("calculator", {"expression": "3600 / 600"}, 2)
    payload = {"answer": "6x", "confidence": 0.9, "claims": [{"claim": "TTL rose 6x", "verdict": "supported", "evidence": [
        {"id": "E1", "quote": "raised from 600 seconds to 3600 seconds"}, {"id": "E3", "quote": "3600 / 600 = 6"}]}]}
    ev = evaluate_finish(payload, r.ledger, available_sources=None)
    assert not ev.issues and ev.claims[0].corroborated is False     # docs + calculator != two sources


def test_gate_does_not_demand_a_source_that_is_down():
    src = build_offline_sources(fault="malformed:kb_search")
    only_facts = [{"claim": "Cache TTL is 3600 seconds", "verdict": "supported",
                   "evidence": [{"id": "E1", "quote": "ttl_seconds = 3600 seconds"}]}]
    steps = [{"calls": [call("kb_search", query="cache ttl")]}, {"calls": [call("facts_lookup", entity="cache")]},
             {"calls": [call("finish", answer="3600 s", claims=only_facts, confidence=0.9)]}]
    llm = ScriptedLLM(steps)
    res = run_agent("How long are responses cached?", [], llm, src, AgentConfig())
    assert res.iterations == 3 and not res.repaired          # accepted first time, no pointless rejection loop
    assert res.degraded and res.status == "partial" and res.confidence <= 0.6


def test_ingest_corpus_endpoint_is_idempotent_wrapper(monkeypatch):
    from fastapi.testclient import TestClient

    import scripts.ingest_corpus as ic
    from app.config import get_settings
    from app.main import app

    monkeypatch.setattr(ic, "ensure_ingested", lambda verbose=True: ["release_notes.md"])
    r = TestClient(app).post(f"{get_settings().api_prefix}/ingest-corpus")
    assert r.status_code == 200 and r.json() == {"ingested": ["release_notes.md"]}


# W15 bug found while building W16: retrieval scores
@pytest.mark.parametrize("cosine", [0.9, 0.6, 0.5, 0.3])
def test_retrieval_score_is_true_cosine_on_chromas_default_metric(tmp_path, cosine):
    """Chroma's default metric is squared L2; W15 read `1 - dist` as cosine, zeroing every passage with cosine <= 0.5."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("chromadb")
    from app.rag.retriever import Retriever
    from app.rag.vectorstore import ChromaVectorStore

    def unit(v):
        v = np.array(v, dtype="float32")
        return v / np.linalg.norm(v)

    doc_vec = unit([cosine, np.sqrt(1 - cosine ** 2), 0, 0])

    class Embed:
        def embed(self, texts):
            return np.array([doc_vec if t == "doc" else unit([1, 0, 0, 0]) for t in texts])

    store = ChromaVectorStore(str(tmp_path), "metric_test")
    store.add_documents(["doc"], Embed().embed(["doc"]), source="x.md")
    (hit,) = Retriever(Embed(), store).retrieve("query", k=1)
    assert hit.score == pytest.approx(cosine, abs=1e-3)
