import math

import pytest

from app.llm.tools import ToolExecutor, calculate
from app.rag.ingest import chunk_text
from app.reliability.cache import ResponseCache
from app.reliability.rate_limiter import TokenBucketRateLimiter


class FakeRetriever:
    def __init__(self, results=None):
        self._results = results or []

    def retrieve(self, query, k=4):
        return self._results


# calculator tool
def test_calculate_basic_arithmetic():
    assert calculate("2 + 2") == 4
    assert calculate("(3 + 4) * 2") == 14
    assert math.isclose(calculate("10 / 4"), 2.5)


def test_calculate_rejects_unsafe_input():
    with pytest.raises(Exception):
        calculate("__import__('os').system('echo hi')")


# tool executor dispatch 

def test_tool_executor_calculator():
    executor = ToolExecutor(FakeRetriever())
    result = executor.execute("calculator", {"expression": "6 * 7"})
    assert result["result"] == 42


def test_tool_executor_unknown_tool_returns_error():
    executor = ToolExecutor(FakeRetriever())
    result = executor.execute("not_a_real_tool", {})
    assert "error" in result


def test_tool_executor_current_time():
    executor = ToolExecutor(FakeRetriever())
    result = executor.execute("current_time", {})
    assert "+00:00" in result["utc_time"]


# chunking 

def test_chunk_text_respects_size_limit():
    text = "Sentence one. " * 200
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 140 for c in chunks)  # size + overlap + small slack


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text("   ", chunk_size=100, overlap=10) == []


def test_chunk_text_rejects_overlap_gte_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("hello world", chunk_size=10, overlap=10)


def test_chunk_text_overlap_shares_context_between_chunks():
    text = "AAAA. " * 50 + "BBBB. " * 50
    chunks = chunk_text(text, chunk_size=80, overlap=15)
    assert len(chunks) >= 2
    # Every chunk after the first should start with some tail of the previous one.
    for prev, cur in zip(chunks, chunks[1:]):
        assert cur[:5] in prev[-20:] or cur.startswith(prev[-15:].strip()[:5])


# rate limiter 
def test_rate_limiter_allows_then_blocks():
    limiter = TokenBucketRateLimiter(requests_per_minute=2)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False


def test_rate_limiter_keys_are_independent():
    limiter = TokenBucketRateLimiter(requests_per_minute=1)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-b") is True


# cache (in-memory fallback path, no Redis required) 

def test_response_cache_in_memory_roundtrip():
    cache = ResponseCache(redis_url=None, ttl_seconds=60)
    key = ResponseCache.make_key({"message": "hi"})
    assert cache.get(key) is None
    cache.set(key, {"answer": "hello"})
    assert cache.get(key) == {"answer": "hello"}


def test_response_cache_key_is_stable_regardless_of_dict_order():
    key1 = ResponseCache.make_key({"a": 1, "b": 2})
    key2 = ResponseCache.make_key({"b": 2, "a": 1})
    assert key1 == key2
