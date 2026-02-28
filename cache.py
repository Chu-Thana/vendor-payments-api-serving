from __future__ import annotations

import json
import logging
from typing import Any, Optional, Tuple

import redis
from redis.exceptions import RedisError

from config import CACHE_ENABLED, CACHE_TTL_SECONDS, REDIS_HOST, REDIS_PORT

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Cache status constants
# -------------------------------------------------------------------
CACHE_HIT = "HIT"
CACHE_MISS = "MISS"
CACHE_BYPASS = "BYPASS"
CACHE_ERROR = "ERROR"
CACHE_OK = "OK"

# -------------------------------------------------------------------
# Redis client (singleton per process, lazy initialization)
# -------------------------------------------------------------------
_client: Optional[redis.Redis] = None

def get_client() -> redis.Redis:
    """
    Return a singleton Redis client.

    - Lazy init: create on first use
    - decode_responses=True => Redis returns str instead of bytes
    - Small timeouts to avoid blocking API too long if Redis is down
    """
    global _client

    if _client is None:
        _client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.5,
        )

    return _client


# -------------------------------------------------------------------
# Key builder
# -------------------------------------------------------------------
def make_key(prefix: str, **params: Any) -> str:
    """
    Build a stable cache key:
        prefix|k1=v1|k2=v2...

    Params are sorted for stability:
        make_key(a=1, b=2) == make_key(b=2, a=1)
    """
    parts = [prefix]
    for k in sorted(params.keys()):
        v = params[k]
        # Keep stable-ish representation for common container types
        if isinstance(v, (dict, list)):
            v = json.dumps(v, sort_keys=True, ensure_ascii=False)
        parts.append(f"{k}={v}")
    return "|".join(parts)


# -------------------------------------------------------------------
# Cache GET (with status)
# -------------------------------------------------------------------
def cache_try_get(key: str) -> Tuple[Optional[Any], str]:
    """
    Attempt to read from Redis.

    Returns:
        (value, status)

    Status:
        HIT      -> Key found
        MISS     -> Key not found
        BYPASS   -> Cache disabled
        ERROR    -> Redis/JSON error
    """
    if not CACHE_ENABLED:
        return None, CACHE_BYPASS

    try:
        raw = get_client().get(key)
        if raw is None:
            return None, CACHE_MISS
        return json.loads(raw), CACHE_HIT

    except (RedisError, json.JSONDecodeError) as e:
        logger.warning("cache_try_get failed key=%s err=%s", key, e)
        return None, CACHE_ERROR


# -------------------------------------------------------------------
# Cache SET (with status)
# -------------------------------------------------------------------
def cache_try_set(
    key: str,
    value: Any,
    ttl_seconds: int = CACHE_TTL_SECONDS,
) -> str:
    """
    Attempt to write to Redis with TTL.

    Returns:
        OK       -> Write success
        ERROR    -> Redis/JSON error
        BYPASS   -> Cache disabled (or TTL misconfig)
    """
    if not CACHE_ENABLED:
        return CACHE_BYPASS

    ttl = int(ttl_seconds)
    if ttl <= 0:
        # TTL misconfig should not break API; treat as bypass
        logger.warning("cache_try_set bypassed due to non-positive TTL ttl=%s", ttl_seconds)
        return CACHE_BYPASS

    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            default=str,  # allow datetime, Decimal, etc.
        )
        ok = get_client().setex(key, ttl, payload)
        return CACHE_OK if ok else CACHE_ERROR

    except (RedisError, TypeError, ValueError) as e:
        logger.warning("cache_try_set failed key=%s err=%s", key, e)
        return CACHE_ERROR


# -------------------------------------------------------------------
# Cache DELETE (invalidate)
# -------------------------------------------------------------------
def cache_delete(key: str) -> bool:
    """
    Delete cache key manually (invalidation use case).

    Returns:
        True if a key was deleted, False otherwise.
    """
    if not CACHE_ENABLED:
        return False

    try:
        deleted = get_client().delete(key)
        return deleted > 0
    except RedisError as e:
        logger.warning("cache_delete failed key=%s err=%s", key, e)
        return False


# -------------------------------------------------------------------
# Health Check
# -------------------------------------------------------------------
def cache_health() -> bool:
    """
    Health check for Redis.

    Behavior:
        - If cache disabled -> True (API should still function)
        - If cache enabled  -> True only if Redis ping works
    """
    if not CACHE_ENABLED:
        return True

    try:
        return bool(get_client().ping())
    except RedisError as e:
        logger.warning("cache_health failed err=%s", e)
        return False