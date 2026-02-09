from enum import Enum
from pydantic import BaseModel
from datetime import date
from typing import List, Optional

class DailySalesResponse(BaseModel):
    sales_date: date
    total_order : int
    total_revenue: float

class MonthlySalesItem(BaseModel):
    month : str
    total_sales : float
    total_profit : float

class MonthlySort(str, Enum):
    month_asc = "month_asc"
    month_desc = "month_desc"
    sales_desc = "sales_desc"
    profit_desc = "profit_desc"

class MonthlySalesResponse(BaseModel):
    generated_at : str
    query_ms : float

    start : str
    end : str
    decimals : int
    sort: MonthlySort
    limit : int

    cursor : Optional[str] = None
    has_more : bool
    next_cursor : Optional[str] = None
    next_curl: Optional[str] = None

    next_cursor: str | None
    next_url: str | None

class MonthlySalesCursorResponse(BaseModel):
    generated_at : str
    query_ms : float

    start : str
    end : str
    decimals : int
    limit : int
    sort : MonthlySort

    cursor: Optional[str] = None
    has_more: bool
    next_cursor: Optional[str] = None
    next_curl: Optional[str] = None
    next_url: Optional[str] = None

    count: int
    data : List[MonthlySalesItem]

class HealthDBResponse(BaseModel):
    status : str
    db_tables : List[str]
    has_superstore_clean : bool