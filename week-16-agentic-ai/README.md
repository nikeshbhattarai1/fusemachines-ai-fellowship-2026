# Weeks 15–16 – Applied AI, Engineering AI Systems, and an Agentic Verification Loop

## AI Assistant — RAG + Tool Calling + Verified Answers

A production-ready AI assistant that uses **RAG (Retrieval-Augmented Generation)**, **LLM tool calling**, structured JSON responses and multiple LLM providers.

The system is built with a **FastAPI backend** and a **Streamlit chat UI** with reliability features such as retries, rate limiting, caching, provider fallback, and graceful error handling.

## Tasks

### Task 1 — Applied AI

- Integrated LLM providers
- Designed prompts and structured output
- Implemented tool calling
- Built a complete RAG pipeline
- Added local LLM serving using vLLM
- Containerized the application

### Task 2 — Engineering AI Systems

- Built Streamlit web UI
- Added response caching
- Implemented retry and rate limiting
- Added LLM provider fallback
- Added circuit breaker and graceful degradation
- Added Docker Compose deployment
- Optimized local inference with vLLM

### Task 3 (W16) — Agentify the Assistant

- Added a verification agent loop (`POST /api/v1/verify`, “Verify” mode in the UI) that cross-checks claims against
  documents *and* a structured facts registry, searches again when evidence is thin, and asks for clarification when needed
- Added an evidence ledger (context engineering), a code-enforced grounding gate, and failure disclosure
- Built an evaluation harness from scratch (`eval/`), including failure injection and token accounting
- Details: [Task 3 write-up](#task-3--agentify-the-assistant-w16)

## Stack

**Python · FastAPI · Streamlit · ChromaDB · Sentence Transformers · Anthropic · OpenAI · Groq · vLLM · Redis · Docker**

## Architecture

```text
User
  ↓
Streamlit UI
  ↓
FastAPI Backend
  ↓
AI Agent
  ├── RAG Search
  ├── Calculator
  ├── Current Time
  └── Structured Answer
  ↓
LLM Provider
  ├── Anthropic
  ├── OpenAI
  ├── Groq
  └── Local vLLM
  ↓
Final Response
```

## Run

### Docker Compose — Recommended

```bash
cp .env.example .env
```

Set at least one LLM API key in `.env`:

```
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
GROQ_API_KEY=your_key
```

Start the application:

```bash
docker compose up --build
```

Open:

- API: http://localhost:8000/docs
- UI: http://localhost:8501

### Using Groq

Anthropic and OpenAI keys are not required if you use Groq.

Get a Groq API key and add it to `.env`:

```
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
```

Provider fallback order:

```
Anthropic → OpenAI → Groq → Local vLLM
```

### Local Setup — Without Docker

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
pip install -r ui/requirements.txt

API_URL=http://localhost:8000/api/v1 \
streamlit run ui/streamlit_app.py
```

Redis is optional. If Redis is unavailable, the application automatically falls back to an in-memory cache.

## RAG Pipeline

The assistant supports document ingestion and retrieval.

```text
Document
   ↓
Chunking
   ↓
Embeddings
   ↓
ChromaDB
   ↓
Similarity Search
   ↓
Relevant Context
   ↓
LLM
   ↓
Answer
```

Upload a document using the API:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@data/sample_docs/assistant_faq.md"
```

## Tool Calling

The AI assistant supports the following tools:

- `rag_search` — searches the knowledge base
- `calculator` — performs calculations
- `current_time` — returns the current time
- `emit_answer` — produces the final structured response

Example:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How does document ingestion work?"}'
```

Example response:

```json
{
  "answer": "Documents are uploaded, split into chunks, embedded, and stored in ChromaDB.",
  "sources": ["assistant_faq.md"],
  "used_tools": ["rag_search"],
  "confidence": 0.9,
  "provider_used": "groq",
  "cached": false
}
```

## Task 1 — Applied AI

| Requirement | Implementation |
|---|---|
| LLM Integration | Anthropic, OpenAI, Groq and vLLM |
| Prompt Engineering | System prompts + temperature/top-p controls |
| Structured Output | Forced `emit_answer` tool |
| Tool Calling | RAG, calculator, current time |
| RAG | Document chunking + embeddings + ChromaDB |
| Local LLM | vLLM |
| Containerization | Docker |

## Task 2 — Engineering AI Systems

| Requirement | Implementation |
|---|---|
| Web UI | Streamlit |
| Backend API | FastAPI |
| Caching | Redis + in-memory fallback |
| Retry | Exponential backoff + jitter |
| Rate Limiting | Token bucket |
| Provider Fallback | Anthropic → OpenAI → Groq → vLLM |
| Error Handling | Circuit breaker + graceful degradation |
| Concurrent Requests | FastAPI async handling |
| Inference Optimization | vLLM PagedAttention + continuous batching |
| Deployment | Docker Compose |

## Task 3 — Agentify the Assistant (W16)

**Feature.** `POST /api/v1/verify` (the "Verify" mode in the UI) checks a question or claim against two sources:
documents (vector search) and a structured facts registry. For each claim it gives a verdict (supported, contradicted,
conflicting, or insufficient) with exact quotes as evidence.

**Why a fixed pipeline is not enough.** Whether the agent needs a second source, a reworded query, or a clarifying question
depends on what the last tool call returned, and we cannot know that in advance.

**Skill vs. agent.** The checklist could have been a Skill. I did not use one because the feature needs tool calls that
depend on earlier results, and the app must enforce rules (quote checking, a source gate, failure disclosure) that a Skill
cannot enforce. I added no new agent, only tools.

**a. Context engineering: an evidence ledger.**
- **Where:** when tool results come back (`runner.py`, `ledger.py`). Each passage is saved once with an id. The model only
  gets ids in the tool result. The ledger is shown in the system prompt on every turn.
- **Problem it solves:** the agent re-searches with new wording, so the same passages come back. In a W15-style transcript,
  every copy stays in the history and is sent again on every call. The ledger also gives the grounding check one clean list
  to compare quotes against.
- **Effect (estimated tokens, same trajectories):** it is not a general saving. It costs +5.1% on short runs, because about
  1,300 tokens of every call are fixed prompt and tool definitions. It saves 3.9% (350-char chunks) and 21.5% (800-char
  chunks) on a stress case with five overlapping searches.

**b. Agentic pattern: single-agent loop.**
- *Context saturation:* the ledger keeps context small (at most 20 short passages).
- *Sequential bottleneck:* small, since a request has at most 5 claims. Parallel agents would each pay the 1,300-token prefix
  again. This is reasoning; I did not build a multi-agent version.
- *Skill dilution:* not an issue (one role, six tools).
- *Single point of failure:* covered by provider fallback, tool timeouts, and output validation.
- *Self-verification paradox:* the main risk, so the check is code, not a second model. `finish` is rejected unless every
  evidence id exists, every quote appears word for word in the ledger, and at least two sources were checked. Code cannot
  check that a quote truly supports its claim, so that risk remains.
- *Stopping:* at most 8 iterations (the last call is forced to `finish`), a token budget, and a timeout.

**c. Evaluation harness (`eval/`, written from scratch).** It has 13 real cases, 3 fault-injection cases, and 3 bad
"control" agents that test the harness itself. It measures:
- task completion rate (behavioural checks, not exact strings);
- tool-call correctness (valid arguments, right tools used);
- trajectory length compared with an expected range;
- tokens per query (estimated at about 4 characters per token);
- a failure log, classified as hard, soft, or cascading soft.

**Results.** I ran the harness in offline mode only. A scripted policy stands in for the LLM, so it tests the loop, the
grounding check, the fault handling, and the metrics, and it completes all 13 real cases by design. The 3 control agents
fail as intended and are classified correctly (fabricated citation: cascading soft; stale source: soft; endless search:
hard). It does not measure how well a real model behaves. Full output: `eval/results/report_offline.md`.

**Token accounting.** Tokens are recorded per iteration and per query. There is no multi-agent system, so the comparison is
the context-mode ablation above (ledger vs. raw transcript).

**Failure injection.** `AGENT_FAULT_INJECTION=unavailable:facts_lookup` makes the registry fail. The system responds like
this:
- the runner returns a tool error that tells the model not to guess;
- the failed source stays visible to the model on every later turn;
- the answer gets a `Limitations:` note, even if the model did not write one;
- status becomes `partial`, `degraded` is `true`, and confidence is capped at 0.6.

If the failed source was the only one that could answer, the correct result is `insufficient_evidence`. These rules are
enforced in code and covered by tests.

**Tool vs. agent boundary.** Every external service is a bounded tool call. Retrieval and the registry are single, stateless
calls with a timeout. The LLM provider chain has several steps inside (retry, backoff, circuit breaker, failover), but it
sits behind one `llm.chat` call. So the trajectory length shows the agent's reasoning, not infrastructure retries. A source
that was itself an agent would still be a bounded tool. I would only make it an agent-to-agent link if it had to negotiate
mid-task.

## Running the W16 agent

```bash
cp .env.example .env                      # set at least one provider key, e.g. GROQ_API_KEY
docker compose up --build
curl -X POST localhost:8000/api/v1/ingest-corpus   # loads data/sample_docs + data/corpus (inside the API process)
# UI: http://localhost:8501 → sidebar → Mode: "Verify (agent)"
curl -X POST localhost:8000/api/v1/verify -H "Content-Type: application/json" \
  -d '{"message": "What is the API rate limit per client?"}'
```

The demo corpus is deliberately conflicting: an old runbook says 60 requests/minute, while the release notes, architecture
doc and facts registry say 30. Dates and authority in `data/corpus/manifest.json` are synthetic test metadata. The registry
mirrors the real defaults in `app/config.py`, so answers can be checked against the code.

Evaluation (no Docker needed for offline; live needs a provider key and an ingested corpus):

```bash
python -m eval.run --offline                                   # deterministic; writes eval/results/report_offline.md
python -m eval.run --live --only rate_limit_conflict           # try one case first
docker compose exec api python -m eval.run --live --ablate --baseline --repeats 3
```

Live runs make roughly 4–8 LLM calls per case; free-tier rate limits (for example Groq's tokens-per-minute cap) may slow a
full run, so start with `--only` and `--repeats 1`. Do not run ingestion or evals against the same Chroma directory from a
second process while the API is writing to it; use `POST /ingest-corpus` for ingestion.

### Loop and Harness Details

**Loop:** Each iteration selects one or more tool calls. kb_search and facts_lookup write results to the ledger, ask_user ends the run with needs_clarification, and finish goes through the grounding gate. A rejected finish returns its issues so the model can retry; after two rejections or when iterations run out, the application repairs the answer by downgrading unsupported claims to insufficient. Identical tool calls return a duplicate hint instead of running again. Confidence is capped at 0.6 when a source fails or a claim is insufficient/conflicting, and 0.75 when a verified claim relies on a single source. If no usable answer is produced, the run reports budget_exhausted and returns no conclusion.

**Cases:** The harness covers conflict resolution, cross-checking, single-source facts, unanswerable claims, false premises with arithmetic, ambiguity requiring ask_user, multi-claim requests, multi-turn follow-ups, query reformulation, and context stress. Fault cases cover unavailable:facts_lookup, malformed:kb_search, and timeout:kb_search. Control agents test fabricated citations, stale-source handling, and never finishing.

**Failure taxonomy:** A hard failure means the run stops without a usable answer, such as from provider failure or budget exhaustion. A soft failure is a wrong or poorly grounded answer with no earlier failure. A cascading soft failure occurs when an earlier issue, such as an empty search, invalid arguments, rejected finish, or failed source, leads to an incorrect final answer.

### `POST /api/v1/verify` response (abridged)

```json
{
  "status": "verified | partial | insufficient_evidence | needs_clarification | budget_exhausted | error",
  "answer": "…", "confidence": 0.9, "degraded": false, "limitations": [],
  "claims": [{"claim": "…", "verdict": "supported", "corroborated": true,
              "evidence": [{"id": "E3", "source": "release_notes.md", "quote": "…"}]}],
  "clarification_question": null, "iterations": 3, "stop_reason": "finished",
  "usage": {"input_tokens": 5338, "output_tokens": 221, "total_tokens": 5559, "estimated": false},
  "trajectory": ["…one entry per LLM call: tools called, arguments, outcome, tokens…"], "evidence": ["…the ledger…"]
}
```

`/verify` is rate-limited like `/chat` (one token per request, although a request can make up to 8 LLM calls) and is
intentionally **not cached**: results depend on tool outcomes and clarification state, so replaying a stored answer could
serve a degraded one.


## Reliability

The application is designed to continue working when individual components fail.

```text
Request
  ↓
Cache Check
  ↓
LLM Provider
  ↓
Failure?
  ├── Retry
  ├── Circuit Breaker
  └── Try Next Provider
  ↓
Successful Response
```

### Retry

Transient failures are automatically retried using exponential backoff and jitter.

### Rate Limiting

A token-bucket rate limiter controls the number of requests per client.

### Provider Fallback

If the primary LLM provider fails, the system automatically tries the next configured provider.

```text
Anthropic
    ↓ failure
OpenAI
    ↓ failure
Groq
    ↓ failure
Local vLLM
```

### Caching

Responses are cached using Redis when available.

If Redis is unavailable, the system automatically falls back to an in-memory cache.

### Circuit Breaker

A circuit breaker temporarily skips providers that repeatedly fail, improving system reliability and reducing unnecessary requests.

### Local vLLM

A local open-source model can be served using vLLM on an NVIDIA GPU host.

```bash
docker compose --profile gpu up --build
```

vLLM provides inference optimizations such as:

- PagedAttention
- Continuous batching
- Efficient GPU memory management

The local model acts as the final fallback provider.

## Configuration

Important environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `GROQ_API_KEY` | Groq API key | - |
| `GROQ_MODEL` | Groq model | `openai/gpt-oss-120b` |
| `LOCAL_LLM_BASE_URL` | vLLM endpoint | `http://vllm:8001/v1` |
| `PROVIDER_PRIORITY` | Provider fallback order | Anthropic → OpenAI → Groq → Local |
| `DEFAULT_TEMPERATURE` | Default LLM temperature | `0.4` |
| `DEFAULT_TOP_P` | Default top-p | `0.9` |
| `MAX_TOOL_ITERATIONS` | Maximum tool iterations | `5` |
| `CHUNK_SIZE` | RAG chunk size | `800` |
| `CHUNK_OVERLAP` | Chunk overlap | `120` |
| `RETRIEVAL_K` | Retrieved chunks | `4` |
| `RATE_LIMIT_PER_MINUTE` | Request limit | `30` |
| `CACHE_TTL_SECONDS` | Cache duration | `3600` |

## Testing

Run the test suite:

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests cover:

- RAG chunking
- Calculator
- Tool dispatcher
- Rate limiter
- Cache fallback
- Core application logic
- **W16:** agent loop (multi-step, ask-user, budgets, forced finish, rejection and repair), grounding verifier, tool runner
  (validation, timeouts, malformed output), failure injection, context modes, `/verify`, the evaluation harness itself,
  and the retrieval-score fix

For an integration test:

```bash
uvicorn app.main:app --port 8000
```

Then ingest a document:

```bash
curl -X POST localhost:8000/api/v1/ingest \
  -F "file=@data/sample_docs/assistant_faq.md"
```

Test the chat endpoint:

```bash
curl -X POST localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What happens if the primary LLM provider is down?"}'
```

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/ingest` | Upload and index documents |
| `POST /api/v1/chat` | Chat with the AI assistant |
| `POST /api/v1/verify` | **W16:** agentic cross-source verification (per-claim verdicts, evidence, trajectory) |
| `POST /api/v1/ingest-corpus` | **W16:** load the demo verification corpus (idempotent) |
| `GET /api/v1/health` | Check application and provider health |
| `/docs` | FastAPI Swagger documentation |

## Project Structure

```
.
├── app/
│   ├── api/                 # FastAPI routes
│   ├── agent/               # W16: loop, ledger, tool runner, verifier, sources, fault injection, baseline
│   ├── llm/                 # LLM providers, prompts and tools
│   ├── rag/                 # RAG ingestion, embeddings, vector store (+ lexical retriever for offline eval)
│   ├── reliability/         # Cache, retry, rate limiter, circuit breaker
│   ├── config.py            # Application configuration
│   └── main.py              # FastAPI application
│
├── ui/
│   ├── streamlit_app.py     # Chat interface
│   └── Dockerfile
│
├── vllm/
│   └── Dockerfile.vllm      # Local model server
│
├── data/
│   ├── sample_docs/         # Sample knowledge-base documents
│   ├── corpus/              # W16 verification corpus + manifest (deliberately conflicting)
│   └── facts/facts.json     # W16 structured facts registry
│
├── eval/                    # W16 evaluation harness (cases, scripted policies, metrics, runner, results/)
├── scripts/ingest_corpus.py # W16 corpus ingestion (CLI; the API also exposes /ingest-corpus)
├── tests/                   # Automated tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md
└── DEPLOYMENT.md
```

## Known Limitations

- ChromaDB currently uses a shared collection rather than separate user/tenant collections.
- Rate limiting and circuit breakers are per application instance.
- Sentence Transformer models are downloaded from Hugging Face on first use.
- Local vLLM tool calling may vary depending on the selected model and prompt template.
- ONNX conversion is not used because the local LLM is optimized through vLLM instead.


## Summary

This project demonstrates a production-oriented AI assistant using:

LLMs + RAG + Tool Calling + Structured Output + FastAPI + Streamlit + Caching + Retry + Rate Limiting + Provider Fallback + vLLM + Docker

It covers both Applied AI development and Engineering AI systems for reliability, performance and production deployment.

---