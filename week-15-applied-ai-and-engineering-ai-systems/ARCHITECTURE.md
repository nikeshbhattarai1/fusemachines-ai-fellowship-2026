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
