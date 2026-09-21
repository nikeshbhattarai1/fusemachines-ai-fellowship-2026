# Operations Runbook v0.9

## Provider fallback
Providers are tried in this order: OpenAI, then Anthropic, then a local model. The circuit breaker cooldown is 30 seconds.

## Retry policy
Failed provider calls are retried up to 5 attempts with exponential backoff.

## Rate limiting
Each client is limited to 60 requests per minute.

## Response caching
Responses are cached for 600 seconds (10 minutes) in memory.

## Document ingestion
Documents are split into chunks of 1000 characters with no overlap. Retrieval returns the top 3 chunks.
