# ===============================
# PostgreSQL utilities (psycopg v3)
# ===============================

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from psycopg.rows import dict_row
from psycopg import sql as pg_sql
from urllib.parse import quote_plus

import psycopg


# -------------------------------
# DSN / Connection helpers
# -------------------------------

def get_pg_dsn() -> str:
    """
    Build Postgres DSN from env.

    Priority:
    1) PG_DSN (full DSN)
    2) PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD
    """
    dsn = os.getenv("PG_DSN")
    if dsn:
        return dsn

    host = os.getenv("PG_HOST", "postgres")
    port = os.getenv("PG_PORT", "5432")
    db = os.getenv("PG_DB", "app_db")
    user = os.getenv("PG_USER", "app")
    pw = os.getenv("PG_PASSWORD", "app_password")

    return (
        f"postgresql://{quote_plus(user)}:"
        f"{quote_plus(pw)}@{host}:{port}/{quote_plus(db)}"
    )


def pg_conn() -> psycopg.Connection:
    """
    Create psycopg connection (autocommit enabled).
    Suitable for logging / infra operations.
    """
    return psycopg.connect(
        get_pg_dsn(),
        connect_timeout=2,
        autocommit=True,
    )


# -------------------------------
# Init / Health
# -------------------------------

def init_api_run_log_pg() -> None:
    """
    Ensure api_run_log table exists and is forward/backward compatible.
    Safe to run multiple times.
    """
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS api_run_log (
                    id BIGSERIAL PRIMARY KEY,
                    run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    status TEXT NOT NULL
                );
                """
            )

            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS request_id TEXT;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS method TEXT;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS endpoint TEXT;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS query_string TEXT;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS status_code INTEGER;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS request_ms DOUBLE PRECISION;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS query_ms DOUBLE PRECISION;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS rows_processed INTEGER;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS message TEXT;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS error TEXT;")

            # metrics support
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS cache_status TEXT;")
            cur.execute("ALTER TABLE api_run_log ADD COLUMN IF NOT EXISTS cache_key TEXT;")

            # helpful indexes
            # noinspection PyTypeChecker
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_run_log_run_at "
                "ON api_run_log (run_at);"
            )

            # noinspection PyTypeChecker
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_run_log_endpoint_run_at "
                "ON api_run_log (endpoint, run_at);"
            )


def health_pg() -> bool:
    """
    Return True if Postgres is reachable.
    """
    try:
        with pg_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True
    except psycopg.Error:
        return False


# -------------------------------
# Logging
# -------------------------------

def log_api_run_pg(
    *,
    status: str,
    rows_processed: Optional[int] = None,
    request_ms: Optional[float] = None,
    query_ms: Optional[float] = None,
    status_code: Optional[int] = None,
    request_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    query_string: Optional[str] = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
    cache_status: Optional[str] = None,
    cache_key: Optional[str] = None,
) -> None:
    """
    Insert one api_run_log row (keyword-only to prevent positional mistakes).
    """
    with pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_run_log (
                    run_at, status, status_code,
                    request_id, method, endpoint, query_string,
                    request_ms, query_ms,
                    rows_processed, message, error
                    cache_status, cache_key
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    datetime.now(timezone.utc),
                    status,
                    status_code,
                    request_id,
                    method,
                    endpoint,
                    query_string,
                    request_ms,
                    query_ms,
                    rows_processed,
                    message,
                    error,
                    cache_status,
                    cache_key,
                ),
            )


# -------------------------------
# Metrics
# -------------------------------
def get_metrics_summary_pg(window_minutes: int = 60) -> Dict[str, Any]:
    """
    Metrics summary over the last N minutes from api_run_log (Postgres).
    """
    query = pg_sql.SQL( """
    WITH base AS (
        SELECT
            method,
            endpoint,
            status,
            status_code,
            request_ms,
            cache_status,
            run_at
        FROM api_run_log
        WHERE run_at >= NOW() - (%s || ' minutes')::interval
    ),
    agg AS (
        SELECT
            COUNT(*)::int AS requests_total,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END)::int AS success_total,
            SUM(CASE WHEN status = 'FAILED'  THEN 1 ELSE 0 END)::int AS failed_total,
            AVG(request_ms)::float AS avg_request_ms,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY request_ms)::float AS p95_request_ms
        FROM base
    ),
    cache AS (
        SELECT
            COALESCE(SUM(CASE WHEN cache_status = 'HIT'    THEN 1 ELSE 0 END), 0)::int AS hit,
            COALESCE(SUM(CASE WHEN cache_status = 'MISS'   THEN 1 ELSE 0 END), 0)::int AS miss,
            COALESCE(SUM(CASE WHEN cache_status = 'BYPASS' THEN 1 ELSE 0 END), 0)::int AS bypass,
            COALESCE(SUM(CASE WHEN cache_status = 'ERROR'  THEN 1 ELSE 0 END), 0)::int AS error
        FROM base
    ),
    slow AS (
        SELECT
            endpoint,
            method,
            AVG(request_ms)::float AS avg_request_ms,
            COUNT(*)::int AS count
        FROM base
        GROUP BY endpoint, method
        ORDER BY AVG(request_ms) DESC
        LIMIT 5
    )
    SELECT
        (SELECT row_to_json(agg) FROM agg) AS agg,
        (SELECT row_to_json(cache) FROM cache) AS cache,
        (SELECT COALESCE(json_agg(slow), '[]'::json) FROM slow) AS slow
    ;
    """)

    with pg_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (window_minutes,))
            row = cur.fetchone() or {}

    agg = row.get("agg") or {}
    cache = row.get("cache") or {}
    slow = row.get("slow") or []

    # compute derived rates safely
    requests_total = int(agg.get("requests_total") or 0)
    failed_total = int(agg.get("failed_total") or 0)

    hit = int(cache.get("hit") or 0)
    miss = int(cache.get("miss") or 0)
    bypass = int(cache.get("bypass") or 0)
    error = int(cache.get("error") or 0)

    cache_total = hit + miss + bypass + error
    hit_rate = (hit / cache_total) if cache_total > 0 else 0.0
    error_rate = (failed_total / requests_total) if requests_total > 0 else 0.0

    return {
        "window_minutes": window_minutes,
        "requests_total": requests_total,
        "success_total": int(agg.get("success_total") or 0),
        "failed_total": failed_total,
        "error_rate": round(error_rate, 4),
        "avg_request_ms": round(float(agg.get("avg_request_ms") or 0.0), 2),
        "p95_request_ms": round(float(agg.get("p95_request_ms") or 0.0), 2),
        "cache": {
            "HIT": hit,
            "MISS": miss,
            "BYPASS": bypass,
            "ERROR": error,
            "hit_rate": round(hit_rate, 4),
        },
        "top_slowest_endpoints": slow,
    }
