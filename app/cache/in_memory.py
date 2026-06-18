from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class InMemoryCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)

            if entry is None:
                return None

            if monotonic() >= entry.expires_at:
                del self._entries[key]
                return None

            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: float,
    ) -> None:
        expires_at = monotonic() + ttl_seconds

        with self._lock:
            self._entries[key] = CacheEntry(
                value=value,
                expires_at=expires_at,
            )

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._entries)


api_response_cache = InMemoryCache()