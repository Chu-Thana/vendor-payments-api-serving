import db
from fastapi import FastAPI, HTTPException, Query, Request
from schemas import DailySalesResponse, HealthDBResponse, MonthlySort, MonthlySalesResponse
from time import perf_counter
from datetime import datetime, timezone
from typing import Optional
import base64, json

app = FastAPI()

@app.get("/sales/daily",
         response_model=DailySalesResponse)
def get_sales_daily(
    date : str = Query(..., description="YYYY-MM-DD")
):
    result = db.get_daily_sales(date)

    if result is None:
        raise HTTPException(status_code=404, detail="No data for this date")

    return result

@app.get(
    "/sales/monthly",
    response_model=MonthlySalesResponse,
    responses={
        400: {"description": "Bad Request (invalid cursor/date/sort)"},
        404: {"description": "No data for this period"},
    },
)
def get_sales_monthly(
    request: Request,
    start: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    end: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    decimals: int = Query(2, ge=0, le=6, description="Decimal places (0-6), default 2"),
    sort : MonthlySort = Query(MonthlySort.month_asc),
    limit: int = Query(10, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="opaque cursor from previous response"),
):
    t0 = perf_counter()

    if start > end:
        raise HTTPException(
            status_code=400,
            detail="Start date must <= end date (YYYY-MM)"
        )

    try:
        data, has_more, next_cursor = db.get_sales_monthly_cursor(
            start=start,
            end=end,
            decimals=decimals,
            sort=sort.value,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as e:
        msg = str(e)
        try:
            detail = json.loads(msg)
        except json.JSONDecodeError:
            detail = {"error": "BAD_REQUEST", "message": msg}
        raise HTTPException(status_code=400, detail=detail)

    if not data:
        raise HTTPException(status_code=404, detail="No data for this period")

    query_ms = round((perf_counter() - t0) * 1000, 2)
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    next_curl = None
    next_url = None
    base_url = str(request.url).split("?")[0]
    if next_cursor:
        next_url = (
            f"{base_url}"
            f"?start={start}&end={end}&decimals={decimals}"
            f"&sort={sort.value}&limit={limit}"
            f"&cursor={next_cursor}"
        )

    return {
        "generated_at": generated_at,
        "query_ms": query_ms,
        "start": start,
        "end": end,
        "decimals": decimals,
        "sort": sort.value,
        "limit": limit,
        "cursor": cursor,
        "has_more": has_more,
        "next_cursor": next_cursor,
        "next_curl": next_curl,
        "next_url": next_url,
        "count": len(data),
        "data": data,
    }

def decode_cursor(cursor: str) -> dict:
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + pad).encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_CURSOR",
                "message": "cursor is not valid",
                "hint": "use next_cursor from previous response",
            },
        )


@app.get("/health/db",
         response_model=HealthDBResponse)
def health_db():
    tables = db.check_db()
    return {
        "status": "ok",
        "db_tables": tables,
        "has_superstore_clean": "superstore_clean" in tables,
    }