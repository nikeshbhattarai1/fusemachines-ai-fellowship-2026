from __future__ import annotations

from app.config import get_settings
from app.reliability.cache import ResponseCache
from app.reliability.rate_limiter import TokenBucketRateLimiter

_settings = get_settings()

_embedding_model = None
_vector_store = None
_retriever = None
_tool_executor = None
_llm_client = None

_cache = ResponseCache(_settings.redis_url, _settings.cache_ttl_seconds)
_rate_limiter = TokenBucketRateLimiter(_settings.rate_limit_per_minute)


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from app.rag.embeddings import EmbeddingModel

        _embedding_model = EmbeddingModel(_settings.embedding_model_name)
    return _embedding_model


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        from app.rag.vectorstore import ChromaVectorStore

        _vector_store = ChromaVectorStore(_settings.chroma_persist_dir, _settings.chroma_collection)
    return _vector_store


def get_retriever():
    global _retriever
    if _retriever is None:
        from app.rag.retriever import Retriever

        _retriever = Retriever(get_embedding_model(), get_vector_store())
    return _retriever


def get_tool_executor():
    global _tool_executor
    if _tool_executor is None:
        from app.llm.tools import ToolExecutor

        _tool_executor = ToolExecutor(get_retriever())
    return _tool_executor


def get_llm_client():
    global _llm_client
    if _llm_client is None:
        from app.llm.client import build_client

        _llm_client = build_client(_settings)
    return _llm_client


def get_response_cache() -> ResponseCache:
    return _cache


def get_rate_limiter() -> TokenBucketRateLimiter:
    return _rate_limiter
