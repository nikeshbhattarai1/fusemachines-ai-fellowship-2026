# W16 Evaluation Report

|  |  |
| --- | --- |
| Mode | offline (scripted policy + lexical retriever) |
| Model / provider | scripted policy (no LLM) |
| Date | 2026-09-20 03:28 |
| Cases (real / fault-injection / controls) | 13 / 3 / 3 |
| Loop limits | max_iterations=8, token_budget=60000, timeout=90s, tool_timeout=1.0s |
| Repeats per case | 1 |

> **Read this first.** This is an OFFLINE run: a scripted policy stands in for the LLM and a lexical retriever for the vector DB. It verifies the loop, tool runner, grounding gate, failure handling, metrics and failure classifier deterministically. It does **not** measure how well any real model decides what to do next -- run `python -m eval.run --live` for that and paste the live table over this one.

## 1. Headline results (real cases, no fault injection)

| Metric | Value |
| --- | --- |
| Task completion rate (all completion checks pass) | 100.0% |
| Tool selection correct (required tools used, forbidden not) | 100.0% |
| Tool-call argument validity (valid / total calls) | 100.0% |
| Fully passed (completion AND tool selection) | 100.0% |
| Trajectory length: mean / median / max iterations | 3.62 / 3 / 6 |
| Trajectory within the expected range for the query | 100.0% |
| Tokens per query (mean) / total (token counts are ESTIMATED, ~4 chars/token) | 7332 / 95321 |
| Grounding-gate rejections of `finish` / runs needing repair | 0 / 0 |
| Repeated identical tool calls | 0 |
| Failures: hard / soft / cascading soft | 0 / 0 / 0 |

## 2. Per-case results

| Case | Category | Result | Status | Iter (expected) | Tools valid | Tokens | Path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rate_limit_conflict | conflict resolution | pass | verified | 3 (2-5) | 3/3 | 5810 | kb_search > facts_lookup > finish |
| cache_ttl_conflict | conflict resolution | pass | verified | 4 (2-6) | 4/4 | 8487 | list_sources > kb_search > facts_lookup > finish |
| provider_order | cross-check | pass | verified | 4 (2-7) | 4/4 | 8092 | kb_search > kb_search > facts_lookup > finish |
| single_source_fact | cross-check | pass | verified | 3 (2-5) | 3/3 | 5585 | kb_search > facts_lookup > finish |
| unanswerable | insufficient evidence | pass | insufficient_evidence | 3 (2-5) | 3/3 | 4942 | kb_search > facts_lookup > finish |
| false_premise_calc | false premise | pass | verified | 4 (3-6) | 4/4 | 7663 | facts_lookup > kb_search > calculator > finish |
| calc_ttl_factor | arithmetic over evidence | pass | verified | 3 (2-5) | 3/3 | 5668 | kb_search > calculator > finish |
| ambiguous | clarification | pass | needs_clarification | 1 (1-2) | 1/1 | 1422 | ask_user |
| multi_claim | multi-claim | pass | verified | 6 (3-7) | 6/6 | 12306 | facts_lookup > facts_lookup > facts_lookup > kb_search > kb_search > finish |
| historical_v09 | conflict resolution | pass | verified | 3 (1-5) | 3/3 | 5785 | kb_search > kb_search > finish |
| multi_turn_followup | multi-turn | pass | verified | 3 (2-5) | 3/3 | 5972 | kb_search > facts_lookup > finish |
| reformulation | query reformulation | pass | verified | 4 (2-6) | 4/4 | 8111 | kb_search > kb_search > facts_lookup > finish |
| stress_overlapping_searches | context stress | pass | verified | 6 (4-8) | 6/6 | 15478 | kb_search > kb_search > kb_search > kb_search > kb_search > finish |

## 3. Failure injection

One source is made to misbehave below the tool runner. Pass = the run says so (degraded, limitations, capped confidence) and does not assert anything the failed source would have supplied.

| Case | Injected fault | Result | Status | Degraded | Confidence | Answer (first 140 chars) |
| --- | --- | --- | --- | --- | --- | --- |
| fault_registry_unavailable | unavailable:facts_lookup | pass | partial | yes | 0.6 | The rate limit is 30 requests per minute per client (documents only; the structured registry could not be checked).  Limitations: Source 'fa |
| fault_search_malformed | malformed:kb_search | pass | partial | yes | 0.6 | Chat responses are cached for 3600 seconds, per the facts registry. Document search failed, so this is not cross-checked.  Limitations: Sour |
| fault_search_timeout | timeout:kb_search | pass | insufficient_evidence | yes | 0.2 | I could not verify the vLLM GPU memory setting: the document search timed out and the registry has no entry for it.  Limitations: Source 'kb |

## 4. Context engineering ablation: evidence ledger (managed) vs W15-style transcript (raw)

Identical tool-call trajectories (scripted); the only difference is what the model is shown. `raw` returns full passage text in every tool result and keeps it in the transcript; `managed` returns ids only and shows deduplicated evidence once in the system prompt.

| Metric | managed (ledger) | raw (transcript) |
| --- | --- | --- |
| Tokens per query (mean) | 7332 | 7082 |
| Tokens total | 95321 | 92070 |
| Task completion | 100.0% | 100.0% |
| Token change vs raw | +3.5% | baseline |

| Case | managed tokens | raw tokens | iterations |
| --- | --- | --- | --- |
| rate_limit_conflict | 5810 | 5481 | 3 |
| cache_ttl_conflict | 8487 | 8102 | 4 |
| provider_order | 8092 | 7712 | 4 |
| single_source_fact | 5585 | 5278 | 3 |
| unanswerable | 4942 | 4738 | 3 |
| false_premise_calc | 7663 | 7211 | 4 |
| calc_ttl_factor | 5668 | 5367 | 3 |
| ambiguous | 1422 | 1405 | 1 |
| multi_claim | 12306 | 11531 | 6 |
| historical_v09 | 5785 | 5544 | 3 |
| multi_turn_followup | 5972 | 5642 | 3 |
| reformulation | 8111 | 7961 | 4 |
| stress_overlapping_searches | 15478 | 16098 | 6 |

**How the effect scales (stress trajectory, 5 overlapping searches).** The ledger's benefit depends on how much passage text each search returns:

| Ingest chunk size | managed tokens | raw tokens | managed vs raw |
| --- | --- | --- | --- |
| 350 | 15478 | 16098 | -3.9% |
| 800 | 15026 | 19132 | -21.5% |

## 6. Failure log

Definitions (operational; see `eval/metrics.py`): **hard** = run stopped without a usable answer; **soft** = normal-looking but wrong/ungrounded answer with no earlier misstep; **cascading soft** = wrong answer that an earlier misstep (empty search, invalid args, rejected `finish`, failed source) propagated into.

_No failures among real and fault-injection cases in this run._

Anomalies the agent handled (case still passed):

| Case | Anomalies |
| --- | --- |
| single_source_fact | s2:empty_result |
| unanswerable | s2:empty_result |
| fault_registry_unavailable | s2:unavailable |
| fault_search_malformed | s1:malformed_output |
| fault_search_timeout | s1:timeout; s2:empty_result |

## 7. Harness self-test (deliberately bad agents)

These scripted agents must FAIL, and the classifier must label them correctly; otherwise the harness cannot be trusted.

| Control | What it does | Expected class | Classified as | Harness OK |
| --- | --- | --- | --- | --- |
| control_fabricated_citation | cites an invented quote | cascading_soft | cascading_soft | yes |
| control_stale_source | trusts the outdated runbook, passes the 2-source gate | soft | soft | yes |
| control_never_finishes | searches forever | hard | hard | yes |
