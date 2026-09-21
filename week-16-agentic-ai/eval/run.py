from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.agent.baseline import run_single_pass
from app.agent.loop import run_agent
from app.agent.models import AgentConfig, AgentResult
from eval.cases import CASES, Case
from eval.metrics import CaseEval, evaluate_run, summarize
from eval.offline import build_offline_sources
from eval.scripted_llm import ScriptedLLM
from eval.scripts import SCRIPTS, compile_script, unresolved_refs

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def make_cfg(live: bool, context_mode: str = "managed") -> AgentConfig:
    # Offline lexical scores are not cosine similarities, so their relevance floor is lower.
    return AgentConfig(max_iterations=8, token_budget=60_000, tool_timeout_seconds=10.0 if live else 1.0,
                       min_score=0.2 if live else 0.1, context_mode=context_mode)


# runners
def offline_runner(case: Case, cfg: AgentConfig) -> AgentResult:
    factory: Callable[[], Any] = lambda: build_offline_sources(
        case.fault, cfg.tool_timeout_seconds + 0.5)
    steps = compile_script(
        SCRIPTS[case.id], factory, dataclasses.replace(cfg, context_mode="managed"))
    bad = unresolved_refs(steps)
    if bad and not case.control:
        raise AssertionError(
            f"script for {case.id} cites evidence it never retrieved: {bad}")
    return run_agent(case.question, case.history, ScriptedLLM(steps), factory(), cfg)


def make_live_runner(baseline: bool = False):
    from app.config import get_settings
    from app.dependencies import get_retriever
    from app.llm.client import build_client
    from app.agent.faults import FaultSpec, FaultyAgentSources
    from app.agent.sources import AgentSources, FactsRegistry, SourceCatalog
    from scripts.ingest_corpus import ensure_ingested

    settings = get_settings()
    ensure_ingested(verbose=False)
    client = build_client(settings)
    base = AgentSources(get_retriever(), FactsRegistry(
        settings.facts_path), SourceCatalog(settings.manifest_path))

    def runner(case: Case, cfg: AgentConfig) -> AgentResult:
        spec = FaultSpec.parse(case.fault)
        if spec:
            spec.sleep_seconds = cfg.tool_timeout_seconds + 1.0
        sources = FaultyAgentSources(base, spec) if spec else base
        fn = run_single_pass if baseline else run_agent
        return fn(case.question, case.history, client, sources, cfg)

    return runner


def stress_scaling(cfg: AgentConfig) -> List[Dict[str, Any]]:
    """Offline only: token cost of the stress trajectory, managed vs raw, at different ingest chunk sizes."""
    case = next(c for c in CASES if c.id == "stress_overlapping_searches")
    rows = []
    for size, overlap in [(350, 40), (800, 120)]:
        def factory(size=size, overlap=overlap): return build_offline_sources(
            None, None, size, overlap)
        steps = compile_script(
            SCRIPTS[case.id], factory, dataclasses.replace(cfg, context_mode="managed"))
        assert not unresolved_refs(
            steps), f"stress script does not resolve at chunk size {size}"
        row: Dict[str, Any] = {"chunk_size": size}
        for mode in ("managed", "raw"):
            res = run_agent(case.question, [], ScriptedLLM(
                steps), factory(), dataclasses.replace(cfg, context_mode=mode))
            row[mode] = res.usage["total_tokens"]
        rows.append(row)
    return rows


def crash_result(exc: Exception) -> AgentResult:
    return AgentResult(status="error", answer=f"harness caught an exception: {type(exc).__name__}: {exc}", stop_reason="error",
                       error=str(exc), usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "estimated": True})


def run_suite(cases: List[Case], runner: Callable[[Case, AgentConfig], AgentResult], cfg: AgentConfig, mode: str,
              repeats: int = 1, tag: str = "") -> List[CaseEval]:
    out: List[CaseEval] = []
    for case in cases:
        for _ in range(repeats):
            try:
                res = runner(case, cfg)
            except Exception as exc:  # noqa: BLE001 - a crashing case is a hard failure, not a crashed harness
                res = crash_result(exc)
            ev = evaluate_run(case, res, mode)
            out.append(ev)
            if tag:
                print(f"  [{tag}] {case.id:32s} {'PASS' if ev.passed else 'FAIL':4s} status={ev.status:22s} iters={ev.iterations} tokens={ev.tokens_total}", flush=True)
    return out


# report
def _table(headers: List[str], rows: List[List[Any]]) -> str:
    def line(r): return "| " + " | ".join(str(c) for c in r) + " |"
    return "\n".join([line(headers), line(["---"] * len(headers))] + [line(r) for r in rows])


def _mark(b: bool) -> str:
    return "yes" if b else "**no**"


def render_report(meta: Dict[str, Any], agent: List[CaseEval], raw: List[CaseEval], base: List[CaseEval],
                  scaling: Optional[List[Dict[str, Any]]] = None) -> str:
    real = [e for e in agent if not e.control and not e.fault]
    faults = [e for e in agent if e.fault]
    controls = [e for e in agent if e.control]
    s = summarize(real)
    est = " (token counts are ESTIMATED, ~4 chars/token)" if s[
        "tokens_estimated_any"] else " (provider-reported token counts)"
    L: List[str] = ["# W16 Evaluation Report", ""]
    L.append(_table(["", ""], [["Mode", meta["mode"]], ["Model / provider", meta["model"]], ["Date", meta["date"]],
                               ["Cases (real / fault-injection / controls)",
                                f"{len(real)} / {len(faults)} / {len(controls)}"],
                               ["Loop limits", "max_iterations=8, token_budget=60000, timeout=90s, tool_timeout=" + str(
                                   meta["tool_timeout"]) + "s"],
                               ["Repeats per case", meta["repeats"]]]))
    if meta["mode"].startswith("offline"):
        L += ["", "> **Read this first.** This is an OFFLINE run: a scripted policy stands in for the LLM and a lexical retriever "
                  "for the vector DB. It verifies the loop, tool runner, grounding gate, failure handling, metrics and failure "
                  "classifier deterministically. It does **not** measure how well any real model decides what to do next -- "
                  "run `python -m eval.run --live` for that and paste the live table over this one."]
    L += ["", "## 1. Headline results (real cases, no fault injection)", "",
          _table(["Metric", "Value"], [
              ["Task completion rate (all completion checks pass)",
               f"{s['task_completion_pct']}%"],
              ["Tool selection correct (required tools used, forbidden not)",
               f"{s['tool_selection_pct']}%"],
              ["Tool-call argument validity (valid / total calls)",
               f"{s['tool_arg_validity_pct']}%"],
              ["Fully passed (completion AND tool selection)",
               f"{s['passed_pct']}%"],
              ["Trajectory length: mean / median / max iterations",
                  f"{s['iterations_mean']} / {s['iterations_median']} / {s['iterations_max']}"],
              ["Trajectory within the expected range for the query",
                  f"{s['in_expected_range_pct']}%"],
              ["Tokens per query (mean) / total" + est,
               f"{s['tokens_mean']} / {s['tokens_total']}"],
              ["Grounding-gate rejections of `finish` / runs needing repair",
                  f"{s['grounding_rejections']} / {s['repaired_runs']}"],
              ["Repeated identical tool calls", s["duplicate_calls"]],
              ["Failures: hard / soft / cascading soft", f"{s['failures']['hard']} / {s['failures']['soft']} / {s['failures']['cascading_soft']}"]]), ""]

    L += ["## 2. Per-case results", "", _table(
        ["Case", "Category", "Result", "Status",
            "Iter (expected)", "Tools valid", "Tokens", "Path"],
        [[e.case_id, e.category, "pass" if e.passed else "**FAIL**", e.status, f"{e.iterations} ({e.iter_range[0]}-{e.iter_range[1]}){'' if e.in_range else ' **out**'}",
          f"{e.calls_valid}/{e.calls_total}", e.tokens_total, e.path] for e in real]), ""]

    L += ["## 3. Failure injection", "",
          "One source is made to misbehave below the tool runner. Pass = the run says so (degraded, limitations, capped "
          "confidence) and does not assert anything the failed source would have supplied.", "",
          _table(["Case", "Injected fault", "Result", "Status", "Degraded", "Confidence", "Answer (first 140 chars)"],
                 [[e.case_id, e.fault, "pass" if e.passed else "**FAIL**", e.status, _mark(e.degraded), e.confidence, e.answer[:140].replace("\n", " ")] for e in faults]), ""]

    if raw:
        rs, ms = summarize([e for e in raw if not e.control]), summarize(
            [e for e in agent if not e.control and not e.fault])
        same = [e for e in agent if not e.control and not e.fault]
        L += ["## 4. Context engineering ablation: evidence ledger (managed) vs W15-style transcript (raw)", "",
              "Identical tool-call trajectories" + (" (scripted)" if meta["mode"].startswith("offline") else " (independent live runs)") +
              "; the only difference is what the model is shown. `raw` returns full passage text in every tool result and keeps it in the transcript; "
              "`managed` returns ids only and shows deduplicated evidence once in the system prompt.", "",
              _table(["Metric", "managed (ledger)", "raw (transcript)"], [
                  ["Tokens per query (mean)", ms["tokens_mean"],
                   rs["tokens_mean"]],
                  ["Tokens total", ms["tokens_total"], rs["tokens_total"]],
                  ["Task completion", f"{ms['task_completion_pct']}%",
                      f"{rs['task_completion_pct']}%"],
                  ["Token change vs raw", f"{100 * (ms['tokens_total'] - rs['tokens_total']) / max(1, rs['tokens_total']):+.1f}%", "baseline"]]), "",
              _table(["Case", "managed tokens", "raw tokens", "iterations"],
                     [[a.case_id, a.tokens_total, b.tokens_total, a.iterations] for a in same for b in raw if b.case_id == a.case_id and not b.fault]), ""]

    if scaling:
        L += ["**How the effect scales (stress trajectory, 5 overlapping searches).** The ledger's benefit depends on how much "
              "passage text each search returns:", "",
              _table(["Ingest chunk size", "managed tokens", "raw tokens", "managed vs raw"],
                     [[r["chunk_size"], r["managed"], r["raw"], f"{100 * (r['managed'] - r['raw']) / r['raw']:+.1f}%"] for r in scaling]), ""]

    if base:
        bs = summarize(base)
        same = [e for e in agent if not e.control and not e.fault]
        ms = summarize(same)
        L += ["## 5. Agent vs fixed single-pass pipeline (one retrieval, one answer)", "",
              _table(["Metric", "agent loop", "single pass"], [
                  ["Task completion", f"{ms['task_completion_pct']}%",
                      f"{bs['task_completion_pct']}%"],
                  ["Tokens per query (mean)", ms["tokens_mean"],
                   bs["tokens_mean"]],
                  ["Failures hard / soft / cascading", "/".join(str(v) for v in ms["failures"].values()), "/".join(str(v) for v in bs["failures"].values())]]), "",
              _table(["Case", "agent", "single pass", "single-pass failure"],
                     [[a.case_id, "pass" if a.passed else "FAIL", "pass" if b.passed else "**FAIL**", b.failure_class or ""] for a in same for b in base if b.case_id == a.case_id]), ""]

    L += ["## 6. Failure log", "", "Definitions (operational; see `eval/metrics.py`): **hard** = run stopped without a usable answer; "
          "**soft** = normal-looking but wrong/ungrounded answer with no earlier misstep; **cascading soft** = wrong answer that an "
          "earlier misstep (empty search, invalid args, rejected `finish`, failed source) propagated into.", ""]
    fails = [e for e in agent + raw +
             base if not e.control and e.failure_class]
    if fails:
        L.append(_table(["Case", "Mode", "Class", "Why", "Anomalies before the end", "Path"],
                        [[e.case_id, e.mode, e.failure_class, "; ".join(e.fail_reasons + e.selection_reasons)[:200],
                          "; ".join(f"s{a['step']}:{a['kind']}" for a in e.anomalies) or "-", e.path] for e in fails]))
    else:
        L.append("_No failures among real and fault-injection cases in this run._")
    handled = [e for e in real + faults if e.passed and e.anomalies]
    if handled:
        L += ["", "Anomalies the agent handled (case still passed):", "",
              _table(["Case", "Anomalies"], [[e.case_id, "; ".join(f"s{a['step']}:{a['kind']}" for a in e.anomalies)] for e in handled])]
    L.append("")

    if controls:
        def ok(e): return e.failure_class == next(
            c.expected_failure_class for c in CASES if c.id == e.case_id)
        L += ["## 7. Harness self-test (deliberately bad agents)", "",
              "These scripted agents must FAIL, and the classifier must label them correctly; otherwise the harness cannot be trusted.", "",
              _table(["Control", "What it does", "Expected class", "Classified as", "Harness OK"],
                     [[e.case_id, {"control_fabricated_citation": "cites an invented quote", "control_stale_source": "trusts the outdated runbook, passes the 2-source gate",
                                   "control_never_finishes": "searches forever"}.get(e.case_id, ""),
                       next(c.expected_failure_class for c in CASES if c.id == e.case_id), e.failure_class, "yes" if ok(e) else "**NO**"] for e in controls]), ""]
    return "\n".join(L)


# main
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--offline", action="store_true")
    g.add_argument("--live", action="store_true")
    ap.add_argument("--ablate", action="store_true",
                    help="also run context_mode=raw (always on in offline mode)")
    ap.add_argument("--baseline", action="store_true",
                    help="live only: also run the fixed single-pass pipeline")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--only", nargs="*", help="run only these case ids")
    ap.add_argument("--out", type=Path, default=RESULTS_DIR)
    args = ap.parse_args(argv)

    live = args.live
    cases = [c for c in CASES if (live is False or not c.control) and (
        not args.only or c.id in args.only)]
    cfg = make_cfg(live)
    t0 = time.time()
    print(
        f"Running {len(cases)} case(s) in {'LIVE' if live else 'OFFLINE'} mode ...")

    runner = make_live_runner() if live else offline_runner
    agent = run_suite(cases, runner, cfg, "agent", args.repeats, tag="agent")

    plain = [c for c in cases if not c.control and not c.fault]
    raw: List[CaseEval] = []
    if plain and (args.ablate or not live):
        print("Context ablation (raw transcript) ...")
        raw = run_suite(plain, runner, make_cfg(live, "raw"),
                        "agent_raw", args.repeats, tag="raw")
    base: List[CaseEval] = []
    if live and args.baseline and plain:
        print("Single-pass baseline ...")
        base = run_suite(plain, make_live_runner(baseline=True),
                         cfg, "single_pass", args.repeats, tag="base")

    model = "scripted policy (no LLM)" if not live else ", ".join(
        sorted({e.provider for e in agent if e.provider != "unknown"})) or "unknown"
    meta = {"mode": "offline (scripted policy + lexical retriever)" if not live else "LIVE", "model": model,
            "date": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "tool_timeout": cfg.tool_timeout_seconds, "repeats": args.repeats}
    scaling = stress_scaling(cfg) if not live else None
    args.out.mkdir(parents=True, exist_ok=True)
    # never let an offline (scripted) report be mistaken for a live one
    tag = "live" if live else "offline"
    (args.out / f"report_{tag}.md").write_text(render_report(meta,
                                                             agent, raw, base, scaling), encoding="utf-8")
    (args.out / f"results_{tag}.json").write_text(json.dumps({"meta": meta, "agent": [e.to_dict() for e in agent],
                                                              "raw": [e.to_dict() for e in raw], "baseline": [e.to_dict() for e in base],
                                                              "stress_scaling": scaling}, indent=2), encoding="utf-8")
    (args.out / f"failure_log_{tag}.json").write_text(json.dumps([e.to_dict(
    ) for e in agent + raw + base if e.failure_class], indent=2), encoding="utf-8")
    real = [e for e in agent if not e.control]
    print(f"\nDone in {time.time() - t0:.1f}s -> {args.out}/report_{tag}.md")
    print(json.dumps(summarize([e for e in real if not e.fault]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
