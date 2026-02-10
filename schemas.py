from enum import Enum
from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional

class DailySalesResponse(BaseModel):
    sales_date: date
    total_order : int
    total_revenue: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "sales_date": "2011-11-09",
                "total_order": 2,
                "total_revenue": 1574.09
            }
        }
    }

class MonthlySalesItem(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
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

    limit: int
    offset: int
    page: int
    prev_page: Optional[int] = None
    next_page: Optional[int] = None

    count: int
    has_more: bool
    total_count: int
    total_pages: int

    data: List[MonthlySalesItem]


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
    next_url: Optional[str] = None
    next_curl: Optional[str] = None

    count: int
    total_count: int
    total_pages: int
    data : List[MonthlySalesItem]

class HealthDBResponse(BaseModel):
    status : str
    db_tables : List[str]
    has_superstore_clean : bool