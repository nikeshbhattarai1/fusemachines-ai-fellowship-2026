# Architecture Overview (current)

## Provider fallback
The assistant tries LLM providers in this order: Anthropic, then OpenAI, then Groq, then a local vLLM model. A circuit breaker skips a failing provider for 60 seconds before it is tried again.

## Retry policy
Transient provider errors are retried up to 3 attempts using exponential backoff with jitter. Permanent errors such as authentication failures are not retried.

## Rate limiting
Each client, identified by session id or IP address, is limited to 30 requests per minute using a token bucket.

## Response caching
Chat responses are cached for 3600 seconds (one hour). Redis is used when available, otherwise an in-memory cache is used.

## Document ingestion
Documents are split into chunks of 800 characters with a 120 character overlap, embedded with all-MiniLM-L6-v2 and stored in ChromaDB. Retrieval returns the top 4 chunks.
