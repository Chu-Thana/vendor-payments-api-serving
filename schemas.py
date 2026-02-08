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

class MonthlySalesResponse(BaseModel):
    generated_at : str
    query_ms : float

    start : str
    end : str
    decimals : int

    limit : int
    offset : int
    page : int

    prev_page : Optional[int]
    next_page : Optional[int]

    count : int
    has_more : bool

    total_count : int
    total_pages : int

    data : List[MonthlySalesItem]

class MonthlySort(str, Enum):
    month_asc = "month_asc"
    month_desc = "month_desc"
    sales_desc = "sales_desc"
    profit_desc = "profit_desc"

class HealthDBResponse(BaseModel):
    status : str
    db_tables : List[str]
    has_superstore_clean : bool