# Week 15 – Applied AI and Engineering AI Systems

## AI Assistant — RAG + Tool Calling

A production-ready AI assistant that uses **RAG (Retrieval-Augmented Generation)**, **LLM tool calling**, structured JSON responses, and multiple LLM providers.

The system is built with a **FastAPI backend** and a **Streamlit chat UI**, with reliability features such as retries, rate limiting, caching, provider fallback, and graceful error handling.

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
| `GET /api/v1/health` | Check application and provider health |
| `/docs` | FastAPI Swagger documentation |

## Project Structure

```
.
├── app/
│   ├── api/                 # FastAPI routes
│   ├── llm/                 # LLM providers, prompts and tools
│   ├── rag/                 # RAG ingestion, embeddings and vector store
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
│   └── sample_docs/         # Sample knowledge-base documents
│
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

It covers both Applied AI development and Engineering AI systems for reliability, performance, and production deployment.

---