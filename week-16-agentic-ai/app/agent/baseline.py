"""Fixed single-pass baseline: ONE retrieval with the raw question, then ONE forced answer.

This is what a non-agentic pipeline can do. It exists so the harness can show where the agentic loop
earns its extra tokens (conflicting sources, false premises, missing evidence) -- and where it doesn't.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.agent.ledger import EvidenceLedger
from app.agent.loop import _base, _finalize, _partial, _record_usage, render_system
from app.agent.models import AgentConfig, AgentState
from app.agent.prompts import SINGLE_PASS_PROMPT
from app.agent.runner import ToolRunner
from app.agent.tools import FINISH_TOOL
from app.agent.verifier import evaluate_finish


def run_single_pass(question: str, history: List[Dict[str, str]], llm: Any, sources: Any, cfg: Optional[AgentConfig] = None):
    cfg = cfg or AgentConfig()
    t0 = time.monotonic()
    state = AgentState(step=1)
    ledger = EvidenceLedger(cfg.ledger_max_entries, cfg.snippet_chars)
    runner = ToolRunner(sources, ledger, cfg, state)
    outcome = runner.run("kb_search", {"query": question}, 1)
    state.trajectory.append({"step": 0, "calls": [{"tool": "kb_search", "args": {"query": question[:120]}, "ok": outcome.ok,
                                                   "arg_valid": True, "error_type": outcome.error_type,
                                                   "summary": outcome.summary, "empty": outcome.empty, "latency_ms": outcome.latency_ms}]})
    system = (SINGLE_PASS_PROMPT + "\n\n## Evidence ledger\n" + ledger.render())
    messages = [{"role": "system", "content": system}]
    messages += [{"role": h["role"], "content": [{"type": "text",
                                                  "text": h["content"]}]} for h in history]
    messages.append({"role": "user", "content": [
                    {"type": "text", "text": question}]})
    try:
        resp, provider = llm.chat(messages=messages, tools=[FINISH_TOOL], temperature=cfg.temperature, top_p=cfg.top_p,
                                  max_tokens=cfg.max_tokens, tool_choice="finish")
    except RuntimeError as exc:
        return _partial(state, ledger, t0, "error", f"no language model available ({str(exc)[:100]})", status="error")
    state.provider_used = provider
    tokens = _record_usage(state, resp, messages)
    call = next((c for c in resp.tool_calls if c.name == "finish"), None)
    state.trajectory.append({"step": 1, "provider": provider, "forced": True, "tokens": tokens, "calls":
                             [{"tool": "finish", "ok": call is not None, "arg_valid": call is not None}]})
    if call is None:
        return _partial(state, ledger, t0, "error", "the model did not produce an answer", status="error")
    # single-pass has no retry: whatever the gate objects to is downgraded, not fixed
    ev = evaluate_finish(call.input, ledger,
                         available_sources=None, require_cross_source=False)
    return _finalize(state, ledger, ev, t0, "finished", repaired=bool(ev.issues))
