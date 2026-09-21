# Security and Data Handling Policy

## Credentials
API keys are read from environment variables and must never be committed to version control.

## Data sharing
The knowledge base is a single shared collection. All users of a deployment can retrieve every ingested document; there is no per-user isolation.

## Retention
Uploaded documents stay in ChromaDB until an administrator deletes the collection. Cached chat responses expire after the cache TTL.

## Authentication
The API has no built-in user authentication. Deployments that need access control must place the API behind a reverse proxy or gateway that provides it.
