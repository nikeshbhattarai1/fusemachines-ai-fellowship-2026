
from __future__ import annotations

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential


class TransientProviderError(Exception):
    """Retryable failure: network timeout, rate limit, 5xx server error."""


class PermanentProviderError(Exception):
    """Non-retryable failure: auth error, malformed request, 4xx client error."""


def with_retry(max_attempts: int = 3):
    """Exponential backoff with jitter, retrying only transient errors."""
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(multiplier=0.5, max=8),
        retry=retry_if_exception_type(TransientProviderError),
    )
