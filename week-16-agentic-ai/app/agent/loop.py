from __future__ import annotations

import json
import math
import time
from typing import Any, Dict, List, Optional

from app.agent.ledger import EvidenceLedger
from app.agent.models import AgentConfig, AgentResult, AgentState, ToolOutcome
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.runner import ToolRunner
from app.agent.sources import FACTS_SOURCE
from app.agent.tools import AGENT_TOOLS, validate_args
from app.agent.verifier import Evaluation, Issue, derive_status, evaluate_finish, final_confidence


# helpers
def estimate_tokens(obj: Any) -> int:
    """~4 chars per token. Only used when the provider reports no usage (and then flagged as estimated)."""
    return int(math.ceil(len(json.dumps(obj, default=str)) / 4))


def _record_usage(state: AgentState, resp: Any, messages: List[Dict[str, Any]]) -> Dict[str, int]:
    if getattr(resp, "usage", None):
        t_in, t_out = int(resp.usage.get("input_tokens", 0)), int(
            resp.usage.get("output_tokens", 0))
    else:
        t_in = estimate_tokens(messages) + estimate_tokens(AGENT_TOOLS)
        t_out = estimate_tokens(
            [resp.text, [tc.input for tc in resp.tool_calls]])
        state.usage_estimated = True
    state.tokens_in += t_in
    state.tokens_out += t_out
    return {"in": t_in, "out": t_out}


def _tool_result(tool_use_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "tool_result", "tool_use_id": tool_use_id, "content": json.dumps(payload, default=str)}


def render_system(cfg: AgentConfig, ledger: EvidenceLedger, state: AgentState, force: bool, reason: Optional[str]) -> str:
    parts = [AGENT_SYSTEM_PROMPT,
             f"## Run status\nIteration {state.step} of {cfg.max_iterations}. "
             f"Tokens used so far: {state.total_tokens} of {cfg.token_budget}."]
    if force:
        parts.append(f"FINAL CALL ({reason}): your budget is used up. Call `finish` now with what you have verified; "
                     "mark anything unverified as `insufficient` and say so in `limitations`. Do not search again.")
    if state.unrecovered_failures:
        lines = [f"- {tool}: {err}" for tool,
                 err in state.unrecovered_failures.items()]
        parts.append("## Source failures (not recovered)\n" + "\n".join(lines))
    if cfg.context_mode == "managed":
        attempted = ", ".join(sorted(ledger.sources_attempted)) or "none yet"
        parts.append("## Evidence ledger (maintained by the application; cite only these ids)\n"
                     f"Sources consulted so far: {attempted}\n{ledger.render()}")
    else:
        parts.append(
            "Evidence ids (E1, E2, ...) appear in tool results; cite them in `finish`.")
    return "\n\n".join(parts)


def _reachable(state: AgentState) -> Optional[List[str]]:
    """Sources the cross-source gate may demand: a source whose tool is currently failing cannot be required."""
    if state.available_sources is None:
        return None
    down_docs = "kb_search" in state.unrecovered_failures
    down_facts = "facts_lookup" in state.unrecovered_failures
    return [s for s in state.available_sources
            if not (s == FACTS_SOURCE and down_facts) and not (s != FACTS_SOURCE and down_docs)]


def _call_record(o: ToolOutcome) -> Dict[str, Any]:
    args = {k: (v[:120] if isinstance(v, str) else v)
            for k, v in o.args.items()}
    return {"tool": o.name, "args": args, "ok": o.ok, "arg_valid": o.arg_valid, "error_type": o.error_type,
            "summary": o.summary, "empty": o.empty, "latency_ms": o.latency_ms}


def _usage_dict(state: AgentState) -> Dict[str, Any]:
    return {"input_tokens": state.tokens_in, "output_tokens": state.tokens_out,
            "total_tokens": state.total_tokens, "estimated": state.usage_estimated}


def _base(state: AgentState, ledger: EvidenceLedger, t0: float, stop_reason: str, **kw: Any) -> AgentResult:
    return AgentResult(evidence=ledger.dump(), trajectory=state.trajectory, iterations=state.step, stop_reason=stop_reason,
                       usage=_usage_dict(state), provider_used=state.provider_used,
                       latency_ms=int((time.monotonic() - t0) * 1000), **kw)


def _finalize(state: AgentState, ledger: EvidenceLedger, ev: Evaluation, t0: float, stop_reason: str, repaired: bool) -> AgentResult:
    degraded = bool(state.unrecovered_failures)
    app_notes: List[str] = []
    for tool, err in state.unrecovered_failures.items():
        app_notes.append(
            f"Source '{tool}' failed during this run ({err}); anything that depends on it is unverified.")
    if any(i.code == "single_source_consulted" for i in ev.issues):
        app_notes.append(
            "Only one source could be consulted, so results are not cross-checked.")
    if any(i.code not in ("single_source_consulted",) for i in ev.issues):
        app_notes.append(
            "Some cited evidence could not be validated; affected claims were downgraded to 'insufficient'.")
    limitations = ev.limitations + \
        [n for n in app_notes if n not in ev.limitations]
    answer = ev.answer or "I could not produce a verified answer."
    if app_notes:  # the user always sees what the application detected, whether or not the model mentioned it
        answer += "\n\nLimitations: " + " ".join(app_notes)
    return _base(
        state, ledger, t0, stop_reason,
        status=derive_status(ev.claims, degraded), answer=answer, claims=[c.to_dict() for c in ev.claims],
        confidence=final_confidence(
            ev.model_confidence, ev.claims, degraded, repaired or bool(app_notes)),
        limitations=limitations, degraded=degraded, repaired=repaired,
    )


def _partial(state: AgentState, ledger: EvidenceLedger, t0: float, stop_reason: str, why: str, status: str = "budget_exhausted") -> AgentResult:
    listed = "; ".join(f"{e.source}: \"{e.text[:90]}\"" for e in ledger.items()[
                       :5]) or "nothing usable"
    return _base(state, ledger, t0, stop_reason, status=status,
                 answer=f"I could not finish verifying this ({why}). No conclusion is asserted. Evidence gathered so far: {listed}.",
                 confidence=0.0, limitations=[why], degraded=bool(state.unrecovered_failures),
                 error=why if status == "error" else None)


# the loop
def run_agent(question: str, history: List[Dict[str, str]], llm: Any, sources: Any, cfg: Optional[AgentConfig] = None) -> AgentResult:
    cfg = cfg or AgentConfig()
    t0 = time.monotonic()
    state = AgentState()
    managed = cfg.context_mode == "managed"
    ledger = EvidenceLedger(cfg.ledger_max_entries,
                            cfg.snippet_chars if managed else None)
    runner = ToolRunner(sources, ledger, cfg, state)
    try:  # internal call, not a tool call: used only by the cross-source gate
        state.available_sources = list(sources.source_names())
    except Exception:  # noqa: BLE001
        state.available_sources = None

    messages: List[Dict[str, Any]] = [{"role": "system", "content": ""}]
    for turn in history:
        messages.append({"role": turn["role"], "content": [
                        {"type": "text", "text": turn["content"]}]})
    messages.append({"role": "user", "content": [
                    {"type": "text", "text": question}]})

    last = cfg.max_iterations - 1
    stop_reason = "max_iterations"
    for step in range(cfg.max_iterations):
        state.step = step + 1
        reason: Optional[str] = None
        if step == last:
            reason = "max_iterations"
        elif state.total_tokens >= cfg.token_budget:
            reason = "token_budget"
        elif time.monotonic() - t0 >= cfg.timeout_seconds:
            reason = "timeout"
        force = reason is not None
        if reason:
            stop_reason = reason

        messages[0] = {"role": "system", "content": render_system(
            cfg, ledger, state, force, reason)}
        try:
            resp, provider = llm.chat(messages=messages, tools=AGENT_TOOLS, temperature=cfg.temperature, top_p=cfg.top_p,
                                      max_tokens=cfg.max_tokens, tool_choice="finish" if force else None)
        except RuntimeError as exc:  # every provider failed or is cooling down
            state.trajectory.append(
                {"step": state.step, "error": str(exc)[:200], "calls": []})
            return _partial(state, ledger, t0, "error", f"no language model available ({str(exc)[:120]})", status="error")
        state.provider_used = provider
        tokens = _record_usage(state, resp, messages)

        blocks: List[Dict[str, Any]] = [
            {"type": "text", "text": resp.text}] if resp.text else []
        blocks += [{"type": "tool_use", "id": tc.id, "name": tc.name,
                    "input": tc.input} for tc in resp.tool_calls]
        messages.append({"role": "assistant", "content": blocks or [
                        {"type": "text", "text": "(no output)"}]})
        rec: Dict[str, Any] = {"step": state.step, "provider": provider, "forced": force, "tokens": tokens,
                               "thought": (resp.text or "")[:300], "calls": []}
        state.trajectory.append(rec)

        if not resp.tool_calls:  # protocol violation: prose instead of a tool call
            state.nudges += 1
            rec["note"] = "no tool call"
            if force or state.nudges > cfg.max_nudges:
                return _partial(state, ledger, t0, "error", "the model did not call a tool", status="error")
            messages.append({"role": "user", "content": [{"type": "text", "text":
                             "Reply only by calling a tool. To answer, call `finish`; to ask the user, call `ask_user`."}]})
            continue

        results: List[Dict[str, Any]] = []
        finish_call = ask_call = None
        for tc in resp.tool_calls:
            if tc.name == "finish" and finish_call is None and ask_call is None:
                finish_call = tc
            elif tc.name == "ask_user" and finish_call is None and ask_call is None:
                ask_call = tc
            elif tc.name in ("finish", "ask_user"):
                results.append(_tool_result(
                    tc.id, {"ok": False, "error": "Only one terminal call per turn."}))
            else:
                outcome = runner.run(tc.name, tc.input, state.step)
                rec["calls"].append(_call_record(outcome))
                results.append(_tool_result(tc.id, outcome.result))

        if ask_call is not None:
            problems = validate_args("ask_user", ask_call.input)
            rec["calls"].append({"tool": "ask_user", "args": ask_call.input,
                                "ok": not problems, "arg_valid": not problems})
            if not problems:
                q = ask_call.input["question"].strip()
                return _base(state, ledger, t0, "asked_user", status="needs_clarification", answer=q,
                             clarification_question=q, confidence=0.0)
            results.append(_tool_result(
                ask_call.id, {"ok": False, "error": "; ".join(problems)}))

        if finish_call is not None:
            payload = finish_call.input if isinstance(
                finish_call.input, dict) else {}
            ev = evaluate_finish(payload, ledger, available_sources=_reachable(state),
                                 require_cross_source=cfg.require_cross_source)
            schema_problems = validate_args("finish", payload)
            issues: List[Issue] = ev.issues + \
                [Issue("bad_arguments", p) for p in schema_problems]
            rec["calls"].append({"tool": "finish", "ok": not issues, "arg_valid": not schema_problems,
                                 "verifier_issues": [i.code for i in issues]})
            if not issues:
                return _finalize(state, ledger, ev, t0, "finished" if not force else stop_reason, repaired=False)
            if state.rejections < cfg.max_finish_rejections and not force and step < last:
                state.rejections += 1
                results.append(_tool_result(finish_call.id, {
                    "ok": False, "error_type": "finish_rejected",
                    "issues": [{"code": i.code, "message": i.message} for i in issues][:6],
                    "instruction": "Fix these problems and call `finish` again. Mark claims you cannot support as "
                                   "`insufficient`, or gather the missing evidence first."}))
            # out of retries or out of iterations: accept a repaired (downgraded) answer, never a bad one
            else:
                rec["note"] = "accepted after application-side repair"
                return _finalize(state, ledger, ev, t0, "finished" if not force else stop_reason, repaired=True)

        messages.append({"role": "user", "content": results})

    return _partial(state, ledger, t0, stop_reason, f"iteration budget ({cfg.max_iterations}) exhausted before a verified answer")
