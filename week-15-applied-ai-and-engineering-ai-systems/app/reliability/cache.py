from __future__ import annotations

import hashlib
import json
from typing import Optional

try:
    import redis
except ImportError:  # pragma: no cover - redis is an optional runtime dep
    redis = None  # type: ignore[assignment]


class ResponseCache:
    def __init__(self, redis_url: Optional[str], ttl_seconds: int):
        self._ttl = ttl_seconds
        self._memory: dict[str, str] = {}
        self._redis = None
        if redis_url and redis is not None:
            try:
                client = redis.from_url(redis_url, socket_connect_timeout=1)
                client.ping()
                self._redis = client
            except Exception:  # noqa: BLE001 - any connection issue -> fall back
                self._redis = None

    @staticmethod
    def make_key(payload: dict) -> str:
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        return "chat:" + hashlib.sha256(blob).hexdigest()

    def get(self, key: str) -> Optional[dict]:
        if self._redis is not None:
            raw = self._redis.get(key)
            return json.loads(raw) if raw else None
        raw = self._memory.get(key)
        return json.loads(raw) if raw else None

    def set(self, key: str, value: dict) -> None:
        raw = json.dumps(value)
        if self._redis is not None:
            self._redis.setex(key, self._ttl, raw)
        else:
            self._memory[key] = raw
