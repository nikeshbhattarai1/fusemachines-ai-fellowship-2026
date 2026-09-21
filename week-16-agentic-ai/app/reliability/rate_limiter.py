from __future__ import annotations

import time
from threading import Lock
from typing import Dict


class TokenBucketRateLimiter:
    def __init__(self, requests_per_minute: int):
        self._capacity = max(1, requests_per_minute)
        self._refill_rate = self._capacity / 60.0  # tokens per second
        self._buckets: Dict[str, float] = {}
        self._last_refill: Dict[str, float] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        with self._lock:
            now = time.monotonic()
            if key not in self._last_refill:
                # First request for this key: start with a full bucket rather
                # than racing a lazily-created "last refill" timestamp against
                # `now` (which could otherwise produce a negative elapsed time
                # and incorrectly reject the very first request).
                self._last_refill[key] = now
                self._buckets[key] = float(self._capacity)

            elapsed = now - self._last_refill[key]
            self._last_refill[key] = now
            self._buckets[key] = min(self._capacity, self._buckets[key] + elapsed * self._refill_rate)
            if self._buckets[key] >= 1:
                self._buckets[key] -= 1
                return True
            return False
