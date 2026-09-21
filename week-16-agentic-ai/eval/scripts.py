from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Optional

from app.agent.ledger import EvidenceLedger, normalize_text
from app.agent.models import AgentConfig, AgentState
from app.agent.runner import ToolRunner
from eval.scripted_llm import call

# tiny DSL
def S(text: str, *calls: Dict[str, Any]) -> Dict[str, Any]:
    return {"text": text, "calls": list(calls)}


def ref(source: str, quote: str) -> Dict[str, str]:
    return {"source": source, "quote": quote}


def claim(text: str, verdict: str, *refs: Dict[str, str], note: str = "") -> Dict[str, Any]:
    return {"claim": text, "verdict": verdict, "evidence": list(refs), "note": note}


def fin(answer: str, claims: List[Dict[str, Any]], conf: float = 0.9, limits: Optional[List[str]] = None) -> Dict[str, Any]:
    return call("finish", answer=answer, claims=claims, confidence=conf, limitations=limits or [])


RN, ARCH, RB, VLLM_DOC, FACTS = "release_notes.md", "architecture_overview.md", "ops_runbook_v0_9.md", "vllm_deployment.md", "facts_registry"

RATE = [
    S("Search the documents for the rate limit.", call("kb_search", query="rate limit per client requests per minute")),
    S("Cross-check the structured registry.", call("facts_lookup", entity="rate limiter", attribute="requests per minute")),
    S("Two current sources agree on 30; the runbook's 60 is superseded.", fin(
        "The API rate limit is 30 requests per minute per client. The old v0.9 runbook says 60, but the v1.1 release notes record the change to 30.",
        [claim("The current per-client rate limit is 30 requests per minute", "supported",
               ref(RN, "lowered from 60 to 30 requests per minute per client"), ref(ARCH, "is limited to 30 requests per minute"),
               ref(FACTS, "requests_per_minute = 30")),
         claim("The v0.9 runbook's value of 60 requests per minute is outdated", "supported",
               ref(RB, "limited to 60 requests per minute"), ref(RN, "lowered from 60 to 30"))])),
]

SCRIPTS: Dict[str, List[Dict[str, Any]]] = {
    "rate_limit_conflict": RATE,

    "cache_ttl_conflict": [
        S("Check what sources exist and how fresh they are.", call("list_sources")),
        S("Search for caching.", call("kb_search", query="response cache TTL seconds cached")),
        S("Confirm with the registry.", call("facts_lookup", entity="cache", attribute="ttl")),
        S("Current docs and registry agree.", fin(
            "Chat responses are cached for 3600 seconds (one hour). The old runbook's 600 seconds was raised in v1.1.",
            [claim("Chat responses are cached for 3600 seconds", "supported", ref(ARCH, "cached for 3600 seconds"), ref(FACTS, "ttl_seconds = 3600")),
             claim("The v0.9 value of 600 seconds is outdated", "supported", ref(RB, "cached for 600 seconds"), ref(RN, "raised from 600 seconds to 3600 seconds"))])),
    ],

    "provider_order": [
        S("Search for the fallback order.", call("kb_search", query="fallback order of providers")),
        S("Older docs disagree; check the release notes specifically.", call("kb_search", query="Groq fallback order", source=RN)),
        S("Confirm with the registry.", call("facts_lookup", entity="provider fallback")),
        S("Current order includes Groq.", fin(
            "Anthropic first, then OpenAI, then Groq, then the local vLLM model. The v0.9 runbook's order (OpenAI, Anthropic, local) is outdated.",
            [claim("Fallback order is Anthropic, OpenAI, Groq, then local vLLM", "supported",
                   ref(ARCH, "Anthropic, then OpenAI, then Groq, then a local vLLM model"), ref(RN, "the fallback order is now Anthropic, OpenAI, Groq, local vLLM"),
                   ref(FACTS, "order = anthropic, openai, groq, local")),
             claim("The v0.9 runbook order is outdated", "supported", ref(RB, "OpenAI, then Anthropic, then a local model"), ref(RN, "Groq was added"))])),
    ],

    "single_source_fact": [
        S("Search for the vLLM setting.", call("kb_search", query="GPU memory utilization vLLM")),
        S("Check whether the registry also records it.", call("facts_lookup", entity="vllm", attribute="gpu memory utilization")),
        S("Only the vLLM document states it.", fin(
            "The local vLLM server runs with a GPU memory utilization of 0.90. Only the vLLM deployment document states this.",
            [claim("vLLM GPU memory utilization is 0.90", "supported", ref(VLLM_DOC, "GPU memory utilization of 0.90"))],
            conf=0.9, limits=["Single source: the facts registry has no vLLM entry, so this could not be cross-checked."])),
    ],

    "unanswerable": [
        S("Search for an upload limit.", call("kb_search", query="maximum file size upload ingest endpoint")),
        S("Try the registry too.", call("facts_lookup", entity="upload", attribute="max file size")),
        S("Nothing documents this.", fin(
            "The maximum upload size for the ingest endpoint is not documented in any available source, so I cannot verify a number.",
            [claim("The ingest endpoint has a documented maximum file size", "insufficient")],
            conf=0.3, limits=["No source documents an upload size limit."])),
    ],

    "false_premise_calc": [
        S("Look up the actual limit.", call("facts_lookup", entity="rate limiter", attribute="requests per minute")),
        S("Cross-check in documents.", call("kb_search", query="rate limit per client requests per minute")),
        S("Compute with the real value.", call("calculator", expression="30 * 5")),
        S("The premise is wrong.", fin(
            "The premise is wrong: the limit is 30 requests per minute, not 100. A client can send 150 requests in 5 minutes.",
            [claim("The rate limit is 100 requests per minute", "contradicted", ref(FACTS, "requests_per_minute = 30"), ref(ARCH, "is limited to 30 requests per minute")),
             claim("At the actual limit a client can send 150 requests in 5 minutes", "supported", ref("calculator", "30 * 5 = 150"), ref(FACTS, "requests_per_minute = 30"))])),
    ],

    "calc_ttl_factor": [
        S("Find both TTL values.", call("kb_search", query="response cache TTL seconds cached")),
        S("Compute the ratio.", call("calculator", expression="3600 / 600")),
        S("Six times.", fin(
            "The cache TTL increased by a factor of 6 (600 s in v0.9 to 3600 s now).",
            [claim("Cache TTL rose from 600 s to 3600 s", "supported", ref(RN, "raised from 600 seconds to 3600 seconds"), ref(RB, "cached for 600 seconds")),
             claim("That is a factor of 6", "supported", ref("calculator", "3600 / 600 = 6"))])),
    ],

    "ambiguous": [
        S("This could mean several limits.", call("ask_user", question="Which limit do you mean: the API rate limit, the cache TTL, or something else?",
                                                  reason="Different limits have different values.")),
    ],

    "multi_claim": [
        S("Check retries.", call("facts_lookup", entity="provider retry", attribute="max attempts")),
        S("Check the breaker.", call("facts_lookup", entity="circuit breaker")),
        S("Check temperature.", call("facts_lookup", entity="temperature", attribute="default temperature")),
        S("Corroborate retries in documents.", call("kb_search", query="retried attempts exponential backoff")),
        S("Corroborate the cooldown in documents.", call("kb_search", query="circuit breaker cooldown seconds provider")),
        S("Two supported, one contradicted.", fin(
            "Retries (3) and cooldown (60 s) are correct. The default temperature is 0.4, not 0.9 (0.9 is the default top_p).",
            [claim("Provider calls are retried up to 3 times", "supported", ref(FACTS, "max_attempts = 3"), ref(ARCH, "retried up to 3 attempts")),
             claim("The circuit breaker cooldown is 60 seconds", "supported", ref(FACTS, "cooldown_seconds = 60"), ref(ARCH, "for 60 seconds before it is tried again")),
             claim("The default temperature is 0.9", "contradicted", ref(FACTS, "default_temperature = 0.4"))])),
    ],

    "historical_v09": [
        S("Search for the historical value.", call("kb_search", query="circuit breaker cooldown v0.9")),
        S("Confirm the change in the release notes.", call("kb_search", query="circuit breaker cooldown raised", source=RN)),
        S("The runbook and the release notes agree.", fin(
            "In v0.9 the circuit breaker cooldown was 30 seconds; v1.1 raised it to 60 seconds.",
            [claim("The v0.9 circuit breaker cooldown was 30 seconds", "supported", ref(RB, "circuit breaker cooldown is 30 seconds"),
                   ref(RN, "cooldown was raised from 30 seconds to 60 seconds"))])),
    ],

    "multi_turn_followup": RATE,

    "reformulation": [
        S("First attempt, worded like the question.", call("kb_search", query="re-attempt failed model call giving up")),
        S("Weak hits; use the document's own vocabulary.", call("kb_search", query="provider retry attempts backoff")),
        S("Confirm in the registry.", call("facts_lookup", entity="retry")),
        S("Three attempts.", fin(
            "Failed provider calls are retried up to 3 attempts. The v0.9 runbook said 5, reduced to 3 in v1.1.",
            [claim("Provider calls are retried up to 3 attempts", "supported", ref(ARCH, "retried up to 3 attempts"), ref(FACTS, "max_attempts = 3")),
             claim("The older value of 5 attempts was reduced", "supported", ref(RB, "retried up to 5 attempts"), ref(RN, "reduced from 5 attempts to 3 attempts"))])),
    ],

    "stress_overlapping_searches": [
        S("Rate limit.", call("kb_search", query="rate limit requests per minute")),
        S("Cache TTL.", call("kb_search", query="response cache TTL seconds cached")),
        S("Retries.", call("kb_search", query="retried attempts exponential backoff")),
        S("Cooldown.", call("kb_search", query="circuit breaker cooldown seconds provider")),
        S("Chunking.", call("kb_search", query="chunk size overlap characters retrieval")),
        S("All five current values are stated by the architecture doc and confirmed as changes by the release notes.", fin(
            "Current settings: rate limit 30 requests/minute, cache TTL 3600 s, up to 3 retry attempts, circuit breaker cooldown 60 s, chunks of 800 characters.",
            [claim("Rate limit is 30 requests per minute", "supported", ref(ARCH, "is limited to 30 requests per minute"), ref(RN, "lowered from 60 to 30 requests per minute per client")),
             claim("Cache TTL is 3600 seconds", "supported", ref(ARCH, "cached for 3600 seconds"), ref(RN, "raised from 600 seconds to 3600 seconds")),
             claim("Provider calls are retried up to 3 attempts", "supported", ref(ARCH, "retried up to 3 attempts"), ref(RN, "reduced from 5 attempts to 3 attempts")),
             claim("Circuit breaker cooldown is 60 seconds", "supported", ref(ARCH, "for 60 seconds before it is tried again"), ref(RN, "cooldown was raised from 30 seconds to 60 seconds")),
             claim("Chunks are 800 characters", "supported", ref(ARCH, "chunks of 800 characters"), ref(RN, "800 characters with 120 characters of overlap"))])),
    ],

    # ---- failure injection: honest degradation ----
    "fault_registry_unavailable": [
        S("Search documents.", call("kb_search", query="rate limit per client requests per minute")),
        S("Try the registry (it is down).", call("facts_lookup", entity="rate limiter", attribute="requests per minute")),
        S("Answer from documents only, and say what could not be checked.", fin(
            "The rate limit is 30 requests per minute per client (documents only; the structured registry could not be checked).",
            [claim("The current per-client rate limit is 30 requests per minute", "supported",
                   ref(RN, "lowered from 60 to 30 requests per minute per client"), ref(ARCH, "is limited to 30 requests per minute"))],
            conf=0.95, limits=["facts_lookup was unavailable, so the registry value was not checked."])),
    ],
    "fault_search_malformed": [
        S("Search documents (returns garbage).", call("kb_search", query="how long responses are cached")),
        S("Fall back to the registry.", call("facts_lookup", entity="cache", attribute="ttl")),
        S("Only one source was reachable.", fin(
            "Chat responses are cached for 3600 seconds, per the facts registry. Document search failed, so this is not cross-checked.",
            [claim("Chat responses are cached for 3600 seconds", "supported", ref(FACTS, "ttl_seconds = 3600"))],
            conf=0.9, limits=["kb_search returned malformed output; document sources were not checked."])),
    ],
    "fault_search_timeout": [
        S("Search documents (hangs).", call("kb_search", query="GPU memory utilization vLLM")),
        S("The registry has no vLLM entry.", call("facts_lookup", entity="vllm", attribute="gpu memory utilization")),
        S("Refuse to guess.", fin(
            "I could not verify the vLLM GPU memory setting: the document search timed out and the registry has no entry for it.",
            [claim("vLLM GPU memory utilization value", "insufficient")], conf=0.2,
            limits=["kb_search timed out."])),
    ],

    # ---- controls ----
    "control_fabricated_citation": [
        S("Search.", call("kb_search", query="rate limit per client requests per minute")),
        S("Registry.", call("facts_lookup", entity="rate limiter", attribute="requests per minute")),
        S("Finish with an invented quote (repeated).", fin("The limit is 30 per minute.", [
            claim("The limit is 30 per minute", "supported", ref(RN, "the enterprise plan allows one million requests per minute"))])),
    ],
    "control_stale_source": [
        S("Only look at the old runbook.", call("kb_search", query="requests per minute rate limit", source=RB)),
        S("And an unrelated policy doc, only to pass the two-source gate.", call("kb_search", query="shared knowledge base users documents", source="security_policy.md")),
        S("Trust the stale value.", fin("The rate limit is 60 requests per minute.", [
            claim("The rate limit is 60 requests per minute", "supported", ref(RB, "limited to 60 requests per minute"))])),
    ],
    "control_never_finishes": [S("Keep searching.", call("kb_search", query=f"rate limit variation {i}")) for i in range(30)],
}


# compilation
def compile_script(steps: List[Dict[str, Any]], sources_factory: Callable[[], Any], cfg: AgentConfig) -> List[Dict[str, Any]]:
    """Execute the script's tool calls on scratch state to learn ledger ids, then rewrite (source, quote) refs as ids."""
    steps = copy.deepcopy(steps)
    state = AgentState()
    ledger = EvidenceLedger(cfg.ledger_max_entries, cfg.snippet_chars)
    runner = ToolRunner(sources_factory(), ledger, cfg, state)

    def resolve(source: str, quote: str) -> str:
        nq = normalize_text(quote)
        for ev in ledger.items():
            if ev.source == source and nq in normalize_text(ev.text):
                return ev.id
        return "E?"          # unresolved: the verifier will reject it, which is exactly what should happen

    for n, step in enumerate(steps, start=1):
        for c in step["calls"]:
            if c["name"] == "finish":
                for cl in c["input"]["claims"]:
                    cl["evidence"] = [{"id": resolve(r["source"], r["quote"]), "quote": r["quote"]} for r in cl["evidence"]]
            elif c["name"] != "ask_user":
                runner.run(c["name"], c["input"], n)
    return steps


def unresolved_refs(steps: List[Dict[str, Any]]) -> List[str]:
    return [f"{cl['claim'][:50]} -> {e['quote'][:40]}" for st in steps for c in st["calls"] if c["name"] == "finish"
            for cl in c["input"]["claims"] for e in cl["evidence"] if e["id"] == "E?"]
