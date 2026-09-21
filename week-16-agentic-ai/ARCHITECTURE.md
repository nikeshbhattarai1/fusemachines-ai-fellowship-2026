# Architecture

## 1. System overview

```mermaid
flowchart TB
    subgraph Client
        U[User]
    end

    subgraph UI["Streamlit UI (ui/streamlit_app.py)"]
        Chat[Chat window]
        Upload[Document upload]
        Settings[Temperature / top-p controls]
    end

    subgraph API["FastAPI backend (app/main.py)"]
        Health["/health"]
        ChatEP["/chat"]
        IngestEP["/ingest"]
        RL[Token-bucket\nrate limiter]
        Cache[(Response cache\nRedis + in-memory fallback)]
        Loop[Agent loop:\ntool calls -> emit_answer]
    end

    subgraph LLM["LLM layer (app/llm/)"]
        FB[FallbackLLMClient\n+ CircuitBreaker]
        A[AnthropicProvider]
        O[OpenAI-compatible\nProvider - hosted OpenAI]
        G[OpenAI-compatible\nProvider - Groq]
        L[OpenAI-compatible\nProvider - local vLLM]
    end

    subgraph RAG["RAG pipeline (app/rag/)"]
        Chunk[Chunker]
        Embed[Embedding model\nsentence-transformers]
        Vec[(ChromaDB\npersistent)]
    end

    subgraph Tools["Tool executor (app/llm/tools.py)"]
        RAGSearch[rag_search]
        Calc[calculator]
        Time[current_time]
        Emit[emit_answer\nforced structured output]
    end

    subgraph Ext["External"]
        AnthropicAPI[(Anthropic API)]
        OpenAIAPI[(OpenAI API)]
        GroqAPI[(Groq API)]
        VLLM[(vLLM server\nlocal open-source model)]
    end

    U --> Chat
    U --> Upload
    Chat --> ChatEP
    Upload --> IngestEP

    ChatEP --> RL
    ChatEP --> Cache
    ChatEP --> Loop
    Loop --> FB
    Loop --> Tools

    FB --> A --> AnthropicAPI
    FB -. fallback .-> O --> OpenAIAPI
    FB -. fallback .-> G --> GroqAPI
    FB -. fallback .-> L --> VLLM

    RAGSearch --> Vec
    IngestEP --> Chunk --> Embed --> Vec

    Cache -.-> ChatEP
```

**Request flow, in words:** the UI calls the FastAPI `/chat` endpoint → a
rate limiter and cache check gate the request → if not cached, the agent loop
sends the conversation to the LLM layer, which tries providers in priority
order (Anthropic, then OpenAI, then Groq, then a local vLLM model) behind a
circuit breaker → the model can call `rag_search` (hits the Chroma vector
store), `calculator`, or `current_time` before ending the loop by calling
`emit_answer`, which is the only way the loop terminates with a result → the
final structured JSON is cached and returned.

Groq and hosted OpenAI both go through the same `OpenAICompatibleProvider`
class (just a different `base_url`/model), since Groq's API is an
OpenAI-compatible `/v1/chat/completions` endpoint including function calling
— no separate integration code was needed.

## 2. RAG ingestion pipeline

```mermaid
sequenceDiagram
    participant U as User (UI)
    participant API as POST /ingest
    participant Ing as ingest.py
    participant Emb as EmbeddingModel
    participant DB as ChromaDB

    U->>API: upload file (.txt / .md / .pdf)
    API->>Ing: load_text(path)
    Ing-->>API: raw text
    API->>Ing: chunk_text(text, chunk_size, overlap)
    Ing-->>API: list[chunk]
    API->>Emb: embed(chunks)
    Emb-->>API: vectors
    API->>DB: add_documents(chunks, vectors, source)
    DB-->>API: doc_id
    API-->>U: {document_id, filename, chunks_indexed}
```

## 3. Chat request: agent loop + provider fallback

```mermaid
sequenceDiagram
    participant U as User (UI)
    participant API as POST /chat
    participant RL as RateLimiter
    participant C as ResponseCache
    participant FB as FallbackLLMClient
    participant P as LLM Provider
    participant T as ToolExecutor
    participant V as ChromaDB

    U->>API: {message, history, temperature, top_p}
    API->>RL: allow(client_key)
    RL-->>API: true / 429
    API->>C: get(cache_key)
    alt cache hit
        C-->>API: cached response
        API-->>U: cached ChatResponse
    else cache miss
        loop up to MAX_TOOL_ITERATIONS
            API->>FB: chat(messages, tools, tool_choice)
            FB->>P: try current provider
            alt provider fails (transient)
                P--xFB: TransientProviderError (retried w/ backoff)
                FB->>FB: open circuit breaker, try next provider
            end
            P-->>FB: ProviderResponse (text and/or tool_calls)
            FB-->>API: response, provider_used
            alt tool_calls present (not emit_answer)
                API->>T: execute(tool_name, input)
                T->>V: (if rag_search) similarity query
                V-->>T: top-k chunks
                T-->>API: tool_result
                API->>API: append tool_result, continue loop
            else emit_answer called
                API->>API: parse StructuredAnswer, break loop
            end
        end
        API->>C: set(cache_key, result)
        API-->>U: ChatResponse (answer, sources, confidence, provider_used)
    end
```

## 4. Deployment topology (docker-compose.yml)

```mermaid
flowchart LR
    subgraph Host["Docker host"]
        UI["ui\n:8501"]
        API["api\n:8000"]
        Redis["redis\n:6379"]
        Vol[(chroma_data\nvolume)]
        VLLM["vllm\n:8001\n(profile: gpu)"]
    end

    Browser -->|8501| UI
    UI -->|HTTP| API
    API -->|cache| Redis
    API -->|persist| Vol
    API -.->|optional local model| VLLM
    API -->|HTTPS| AnthropicAPI[(Anthropic API)]
    API -->|HTTPS| OpenAIAPI[(OpenAI API)]
```

The `vllm` service is behind the `gpu` Compose profile (`docker compose
--profile gpu up`) since it requires an NVIDIA GPU and is optional — the
app runs fully with just Anthropic and/or OpenAI configured.

---

# Week 16 additions: the agentic verification loop

Sections 1–4 above are unchanged in structure. W16 adds one endpoint (`POST /verify`) and the `app/agent/` package.
It reuses the existing `FallbackLLMClient` (provider chain, retry, circuit breaker), the rate limiter and the vector store.
It deliberately bypasses the response cache.

## 5. Where the agent plugs into the system

```mermaid
flowchart TB
    subgraph UI["Streamlit UI"]
        Mode["Mode switch: Chat | Verify"]
        VView["Verify view:\nverdicts, quotes, limitations,\ntrajectory, tokens"]
    end

    subgraph API["FastAPI backend"]
        VerifyEP["POST /verify"]
        IngestC["POST /ingest-corpus"]
        RL["Token-bucket rate limiter\n(shared with /chat)"]
    end

    subgraph AGENT["app/agent  (single agent loop)"]
        Loop["Loop controller\nloop.py\nlimits: iterations, tokens, timeout"]
        Runner["Tool runner\nrunner.py\nvalidate args, timeout,\nvalidate output, dedup calls"]
        Ledger[("Evidence ledger\nledger.py\ndedup, caps, stable ids")]
        Gate["Grounding gate\nverifier.py\nids exist, quotes verbatim,\ncross-source rule"]
        Fault["Fault injector\nfaults.py (dev/test only)"]
    end

    subgraph SRC["Sources"]
        KB["Documents:\nvector search (ChromaDB)"]
        Facts["Structured facts registry\ndata/facts/facts.json"]
        Calc["Calculator"]
    end

    subgraph LLM["Existing LLM layer"]
        FB["FallbackLLMClient\nAnthropic > OpenAI > Groq > vLLM\nretry + circuit breaker"]
    end

    Mode --> VerifyEP
    VerifyEP --> RL --> Loop
    Loop -->|"messages + tools + ledger in system prompt"| FB
    FB -->|"tool calls"| Loop
    Loop --> Runner
    Runner --> Ledger
    Runner --> KB
    Runner --> Facts
    Runner --> Calc
    Fault -.->|"injects failure below the runner"| Runner
    Loop -->|"finish"| Gate
    Gate --> Ledger
    Gate -->|"issues (reject)"| Loop
    Loop --> VView
    IngestC --> KB
```

## 6. The loop: what the model decides and what the application guarantees

```mermaid
flowchart TD
    Start(["Request: question + history"]) --> Limits{"Limits reached?\niteration = last,\ntokens >= budget, or timeout"}
    Limits -->|"no"| CallLLM["LLM call\nsystem prompt = instructions + run status\n+ failed sources + evidence ledger"]
    Limits -->|"yes"| Force["LLM call with tool_choice = finish\n(no more searching)"]

    CallLLM --> Decide{"Model's choice"}
    Force --> Decide

    Decide -->|"no tool call"| Nudge{"Nudges left?"}
    Nudge -->|"yes"| CallLLM
    Nudge -->|"no"| ErrOut(["status: error\nno conclusion asserted"])

    Decide -->|"kb_search / facts_lookup /\nlist_sources / calculator"| Runner["Tool runner:\nvalidate args > skip duplicate >\ncall with timeout > validate output"]
    Runner -->|"ok"| WriteL["Write evidence to ledger\n(dedup, relevance floor, caps)"]
    Runner -->|"failed"| MarkF["Record failure:\nsource marked degraded"]
    WriteL --> Result["Tool result to model:\nids only"]
    MarkF --> Result2["Tool result to model:\nerror + do not guess"]
    Result --> Limits
    Result2 --> Limits

    Decide -->|"ask_user"| Ask(["status: needs_clarification"])

    Decide -->|"finish"| Gate{"Grounding gate\n1 evidence ids exist\n2 quotes verbatim in ledger\n3 conflicting cites 2 sources\n4 at least 2 reachable sources consulted"}
    Gate -->|"pass"| Final["Finalize:\nderive status, cap confidence,\nappend limitations for failed sources"]
    Gate -->|"fail, rejections < 2\nand not forced"| Reject["Tool result: issues to fix"]
    Reject --> Limits
    Gate -->|"fail, out of retries\nor forced"| Repair["Repair: downgrade unsupported\nclaims to insufficient"]
    Repair --> Final
    Final --> Done(["verified | partial |\ninsufficient_evidence"])

    Limits -.->|"loop ends without finish"| Budget(["status: budget_exhausted"])
```

## 7. Failure handling at each boundary

| Where | Failure | What the system does |
|---|---|---|
| Tool arguments | wrong type / missing field | `invalid_arguments` result naming the problem; model can retry |
| Tool call | source down, or hangs past `AGENT_TOOL_TIMEOUT_SECONDS` | `unavailable` / `timeout` result; source recorded as degraded |
| Tool output | wrong shape (`malformed_output`) | rejected before it can become evidence; treated like an outage |
| Search | nothing relevant, or the same passages again | empty / duplicate hint; ledger dedups; model reformulates or switches source |
| `finish` | fabricated id or quote, single source, weak conflict | rejected with specific issues (max 2), then repaired by downgrade |
| Degraded run | any unrecovered source failure | `Limitations:` appended, `degraded: true`, confidence ≤ 0.6, status ≤ `partial` |
| LLM | every provider fails | `status: error` with the evidence gathered so far, HTTP 200 |
| Budget | iterations / tokens / time | last call forced to `finish`; otherwise `budget_exhausted`, no conclusion asserted |

## 8. Evaluation harness

```mermaid
flowchart LR
    Cases["eval/cases.py\n19 cases + expectations"] --> Run["eval/run.py"]
    Scripts["eval/scripts.py\nscripted policies (offline)"] --> Sc["ScriptedLLM"]
    Sc --> Run
    Live["Real LLM + real retriever\n(--live)"] --> Run
    Run -->|"same run_agent code path"| Agent["app/agent"]
    Agent --> Metrics["eval/metrics.py\ncompletion, tool-call correctness,\ntrajectory, tokens, failure class"]
    Metrics --> Reports["eval/results/\nreport_offline.md, report_live.md,\nresults_*.json, failure_log_*.json"]
```

The harness calls `run_agent` directly (no HTTP), so live and offline runs execute the same loop, runner and gate. Only the
model and the retriever are swapped.

## 9. Deployment delta

`docker-compose.yml` gains one bind mount (`./eval/results` → `/app/eval/results`) so reports written inside the container
appear on the host. The image now also copies `scripts/` and `eval/`. Load the demo corpus with
`POST /api/v1/ingest-corpus` (in-process; do not open the Chroma directory from a second writing process).

