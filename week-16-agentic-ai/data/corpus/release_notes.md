# Release Notes

## v1.1 (2026-08-20)

Groq was added as a third hosted provider; the fallback order is now Anthropic, OpenAI, Groq, local vLLM.

The default rate limit was lowered from 60 to 30 requests per minute per client.

The response cache TTL was raised from 600 seconds to 3600 seconds.

The circuit breaker cooldown was raised from 30 seconds to 60 seconds.

Provider retries were reduced from 5 attempts to 3 attempts.

Chunking changed from 1000 characters without overlap to 800 characters with 120 characters of overlap; retrieval now returns the top 4 chunks instead of 3.
