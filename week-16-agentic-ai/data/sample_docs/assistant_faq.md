# Internal FAQ: AI Assistant Project

## What is this project?
This project is a retrieval-augmented AI assistant. It combines a large
language model with a private knowledge base so it can answer questions
using documents that were never part of the model's training data.

## How does document ingestion work?
Uploaded files are split into overlapping chunks of roughly 800 characters,
converted into vector embeddings with a sentence-transformers model, and
stored in a local Chroma vector database. When a user asks a question, the
assistant embeds the query, finds the most similar chunks, and passes them
to the language model as context.

## How does the assistant decide when to search the knowledge base?
The system prompt instructs the model to call the `rag_search` tool whenever
a question might relate to ingested documents, before answering from general
knowledge. The model only cites a source if it actually came back from a
`rag_search` result.

## What happens if the primary LLM provider is down?
The assistant maintains a prioritized list of providers (for example:
Anthropic, then OpenAI, then a locally hosted model). If a provider fails or
times out, a circuit breaker temporarily skips it and the request is retried
against the next provider in the chain, so a single outage degrades service
quality rather than causing a hard failure.

## Is the knowledge base shared across users?
In this reference implementation, the knowledge base is a single shared
Chroma collection. A production multi-tenant deployment would namespace
collections per user or organization.
