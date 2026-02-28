from __future__ import annotations

import os


# =========================
# Helpers
# =========================

def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"Invalid integer for env var {name}: {raw}")


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()

    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False

    raise RuntimeError(f"Invalid boolean for env var {name}: {raw}")


# =========================
# Logging
# =========================

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

LOG_LEVEL = env("LOG_LEVEL", "INFO").upper()

if LOG_LEVEL not in _VALID_LOG_LEVELS:
    raise RuntimeError(f"Invalid LOG_LEVEL: {LOG_LEVEL}")


# =========================
# PostgreSQL (api_run_log)
# =========================

# Allow full DSN override (useful in production/cloud)
PG_DSN_ENV = os.getenv("PG_DSN")

if PG_DSN_ENV:
    PG_DSN = PG_DSN_ENV
else:
    PG_HOST = env("PG_HOST", "postgres")
    PG_PORT = env_int("PG_PORT", 5432)
    PG_DB = env("PG_DB", "app_db")
    PG_USER = env("PG_USER", "app")
    PG_PASSWORD = env("PG_PASSWORD", "app_password")

    PG_DSN = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"


# =========================
# Redis (Cache)
# =========================

CACHE_ENABLED = env_bool("CACHE_ENABLED", False)
CACHE_TTL_SECONDS = env_int("CACHE_TTL_SECONDS", 300)

if CACHE_ENABLED and CACHE_TTL_SECONDS <= 0:
    raise RuntimeError("CACHE_TTL_SECONDS must be > 0 when CACHE_ENABLED=true")

REDIS_HOST = env("REDIS_HOST", "redis")
REDIS_PORT = env_int("REDIS_PORT", 6379)