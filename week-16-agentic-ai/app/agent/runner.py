"""Tool runner: the boundary between the model's tool calls and the real sources.

Responsibilities (each one is a failure mode we saw or expect in agent loops):
  * validate arguments   -> a precise error the model can act on, not an exception
  * enforce a deadline   -> a hung source cannot hang the whole request
  * validate the output  -> a malformed backend response cannot become "evidence"
  * detect repeat calls  -> stops the model re-issuing the identical search
  * write the ledger     -> dedup + caps + relevance floor (context engineering)
  * track failures       -> the loop/verifier can tell the user what could not be checked
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, Callable, Dict, List, Tuple

from app.agent.errors import MalformedToolOutput, ToolTimeout, ToolUnavailable
from app.agent.ledger import EvidenceLedger
from app.agent.models import DEGRADING_ERRORS, AgentConfig, AgentState, ToolOutcome
from app.agent.sources import FACTS_SOURCE
from app.agent.tools import validate_args
from app.llm.tools import calculate

SOURCE_TOOLS = {"kb_search", "facts_lookup", "list_sources"}


# output validation
def _validate_chunks(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        raise MalformedToolOutput(f"search returned {type(raw).__name__}, expected a list of passages")
    out = []
    for item in raw:
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not isinstance(item.get("source"), str):
            raise MalformedToolOutput("a passage is missing 'text' or 'source'")
        try:
            score = float(item.get("score", 0.0))
        except (TypeError, ValueError) as exc:
            raise MalformedToolOutput("passage score is not numeric") from exc
        if not 0.0 <= score <= 1.0001:
            raise MalformedToolOutput(f"passage score {score} outside [0, 1]")
        out.append({"text": item["text"], "source": item["source"], "score": score})
    return out


def _validate_facts(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get("matches"), list):
        raise MalformedToolOutput("facts lookup did not return an object with a 'matches' list")
    for m in raw["matches"]:
        if not isinstance(m, dict) or not {"entity", "attribute", "value"} <= set(m):
            raise MalformedToolOutput("a facts match is missing entity/attribute/value")
    return raw


def _validate_sources(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list) or not all(isinstance(s, dict) and isinstance(s.get("name"), str) for s in raw):
        raise MalformedToolOutput("list_sources did not return a list of {name, ...} objects")
    return raw


def _fmt_number(x: float) -> str:
    return str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)


class ToolRunner:
    def __init__(self, sources: Any, ledger: EvidenceLedger, cfg: AgentConfig, state: AgentState):
        self.sources, self.ledger, self.cfg, self.state = sources, ledger, cfg, state
        self._impl: Dict[str, Callable[[Dict[str, Any], int], Tuple[Dict[str, Any], str, bool, List[str]]]] = {
            "list_sources": self._list_sources,
            "kb_search": self._kb_search,
            "facts_lookup": self._facts_lookup,
            "calculator": self._calculator,
        }

    # public
    def run(self, name: str, args: Any, step: int) -> ToolOutcome:
        t0 = time.monotonic()
        args = args if isinstance(args, dict) else {}
        problems = validate_args(name, args)
        if problems or name not in self._impl:
            msg = "; ".join(problems) or f"tool '{name}' cannot be called here"
            return self._fail(name, args, "invalid_arguments", msg, t0, arg_valid=False,
                              hint="Fix the arguments and call again.")

        key = json.dumps([name, args], sort_keys=True, default=str)
        seen = self.state.seen_calls.get(key, 0)
        self.state.seen_calls[key] = seen + 1
        if seen >= 1:
            return ToolOutcome(
                name, args,
                {"ok": True, "duplicate_call": True,
                 "hint": "You already made this exact call; its evidence is already in the ledger. "
                         "Change the query or the source, or finish."},
                ok=True, error_type="duplicate", summary="duplicate call", latency_ms=self._ms(t0),
            )
        try:
            result, summary, empty, new_ids = self._impl[name](args, step)
        except ToolTimeout as exc:
            return self._fail(name, args, "timeout", str(exc), t0)
        except MalformedToolOutput as exc:
            return self._fail(name, args, "malformed_output", str(exc), t0)
        except (ToolUnavailable, ConnectionError, OSError) as exc:
            return self._fail(name, args, "unavailable", str(exc) or "source unavailable", t0)
        except Exception as exc:  # noqa: BLE001 - an unexpected bug in a tool must not crash the loop
            return self._fail(name, args, "internal_error", f"{type(exc).__name__}: {exc}", t0)

        self.state.unrecovered_failures.pop(name, None)  # the source works again
        ok = bool(result.get("ok", True))
        etype = None if ok else result.get("error_type")
        return ToolOutcome(name, args, result, ok=ok, error_type=etype, summary=summary, latency_ms=self._ms(t0),
                           arg_valid=etype != "invalid_arguments", empty=empty, new_evidence=new_ids)

    # helpers
    @staticmethod
    def _ms(t0: float) -> int:
        return int((time.monotonic() - t0) * 1000)

    def _timed(self, fn: Callable[..., Any], *a: Any) -> Any:
        # One throw-away worker per call: a hung source is abandoned, never joined.
        ex = ThreadPoolExecutor(max_workers=1)
        fut = ex.submit(fn, *a)
        try:
            return fut.result(timeout=self.cfg.tool_timeout_seconds)
        except FutureTimeout as exc:
            raise ToolTimeout(f"no answer within {self.cfg.tool_timeout_seconds:g}s") from exc
        finally:
            ex.shutdown(wait=False, cancel_futures=True)

    def _fail(self, name: str, args: Dict[str, Any], error_type: str, message: str, t0: float,
              arg_valid: bool = True, hint: str = "") -> ToolOutcome:
        if error_type in DEGRADING_ERRORS and name in SOURCE_TOOLS:
            self.state.unrecovered_failures[name] = f"{error_type}: {message}"
            self.state.failure_events.append({"tool": name, "error_type": error_type, "message": message})
            hint = hint or ("This source failed. Do NOT guess what it would have said. Use another source if one "
                            "can answer, and disclose the gap in `limitations` when you finish.")
        result = {"ok": False, "error_type": error_type, "error": message}
        if hint:
            result["hint"] = hint
        return ToolOutcome(name, args, result, ok=False, error_type=error_type, summary=f"{error_type}: {message}"[:160],
                           latency_ms=self._ms(t0), arg_valid=arg_valid)

    @property
    def _managed(self) -> bool:
        return self.cfg.context_mode == "managed"

    # tools
    def _list_sources(self, args: Dict[str, Any], step: int):
        raw = _validate_sources(self._timed(self.sources.list_sources))
        self.state.available_sources = [s["name"] for s in raw]
        return {"ok": True, "sources": raw}, f"{len(raw)} sources", False, []

    def _kb_search(self, args: Dict[str, Any], step: int):
        query, source = args["query"], args.get("source")
        k = max(1, min(int(args.get("k") or self.cfg.default_k), self.cfg.max_k))
        chunks = _validate_chunks(self._timed(lambda: self.sources.search(query, source=source, k=k)))
        if source:
            self.ledger.mark_attempted(source)
        for c in chunks:
            self.ledger.mark_attempted(c["source"])

        added, dups, filtered, capped, shown = [], [], 0, 0, []
        for c in sorted(chunks, key=lambda c: c["score"], reverse=True):
            if c["score"] < self.cfg.min_score:  # relevance floor applies in both context modes
                filtered += 1
                continue
            meta = {"last_updated": self.sources.meta_for(c["source"]).get("last_updated", "")} if hasattr(self.sources, "meta_for") else {}
            ev, status = self.ledger.add(source=c["source"], kind="document", text=c["text"], score=c["score"],
                                         meta={k_: v for k_, v in meta.items() if v}, query=query, step=step)
            if status == "dropped_cap":
                capped += 1
            elif status == "duplicate":
                dups.append(ev.id)
                shown.append((ev, c, "duplicate"))
            else:
                added.append({"id": ev.id, "source": ev.source, "score": ev.score})
                shown.append((ev, c, "added"))

        if self._managed:
            result: Dict[str, Any] = {"ok": True, "query": query, "added": added, "already_in_ledger": dups,
                                      "filtered_low_relevance": filtered, "dropped_ledger_full": capped}
            result["hint"] = ("Read the text of new evidence in the ledger (system prompt)." if added else
                              "Nothing new. Rephrase the query, or try another source (facts_lookup / a specific document).")
        else:  # raw mode == W15 behaviour: full text of every hit goes into the transcript, duplicates included
            result = {"ok": True, "results": [{"id": ev.id, "source": c["source"], "score": c["score"], "text": c["text"]}
                                               for ev, c, _ in shown]}
        empty = not added and not dups
        return result, f"+{len(added)} new, {len(dups)} dup, {filtered} low-relevance", empty, [a["id"] for a in added]

    def _facts_lookup(self, args: Dict[str, Any], step: int):
        raw = _validate_facts(self._timed(lambda: self.sources.lookup_facts(args["entity"], args.get("attribute"))))
        self.ledger.mark_attempted(FACTS_SOURCE)
        added, dups, shown = [], [], []
        for m in raw["matches"]:
            unit = f" {m.get('unit')}" if m.get("unit") else ""
            text = (f"{m['entity']}.{m['attribute']} = {m['value']}{unit} "
                    f"(source of truth: {m.get('source_of_truth', 'n/a')}; updated {m.get('last_updated', 'n/a')})")
            ev, status = self.ledger.add(source=FACTS_SOURCE, kind="structured", text=text,
                                         meta={"last_updated": str(m.get("last_updated", ""))}, query=args["entity"], step=step)
            if status == "dropped_cap":
                continue
            (dups if status == "duplicate" else added).append({"id": ev.id, "entity": m["entity"], "attribute": m["attribute"]}
                                                              if status == "added" else ev.id)
            shown.append(ev)
        result: Dict[str, Any] = {"ok": True}
        if self._managed:
            result.update({"added": added, "already_in_ledger": dups})
            result["hint"] = ("Read the new entries in the ledger." if added else
                              "No matching entity. Try one of known_entities, or another source.")
        else:
            result["matches"] = [{"id": e.id, "text": e.text} for e in shown]
        if not raw["matches"] or not added:
            result["known_entities"] = raw.get("known_entities", [])
        if raw.get("note"):
            result["note"] = raw["note"]
        return result, f"+{len(added)} new, {len(dups)} dup", not raw["matches"], [a["id"] for a in added if isinstance(a, dict)]

    def _calculator(self, args: Dict[str, Any], step: int):
        expr = args["expression"]
        try:
            value = calculate(expr)
        except Exception as exc:  # noqa: BLE001 - bad expression is the model's error, not a degraded source
            return ({"ok": False, "error_type": "invalid_arguments", "error": f"Could not evaluate: {exc}"},
                    "bad expression", True, [])
        ev, status = self.ledger.add(source="calculator", kind="calc", text=f"{expr} = {_fmt_number(value)}", query=expr, step=step)
        result: Dict[str, Any] = {"ok": True, "result": value, "evidence_id": ev.id if ev else None}
        return result, f"{expr} = {_fmt_number(value)}", False, [ev.id] if ev and status == "added" else []
