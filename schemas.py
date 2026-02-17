from enum import Enum
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import List, Optional
from pydantic import Field

# ===============================
# Enums
# ===============================

class ETLStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    WARNING = "WARNING"

class MonthlySort(str, Enum):
    """
    Defines sorting options for aggregated monthly sales results.
    """
    month_asc = "month_asc"
    month_desc = "month_desc"
    sales_desc = "sales_desc"
    profit_desc = "profit_desc"

class RegionSort(str, Enum):
    """
    Defines sorting options for sales results grouped by region.
    """
    region_asc = "region_asc"
    sales_desc = "sales_desc"
    profit_desc = "profit_desc"

class CategorySort(str, Enum):
    """
    Defines sorting options for sales results grouped by category.
    """
    category_asc = "category_asc"
    sales_desc = "sales_desc"
    profit_desc = "profit_desc"


# ===============================
# Health Models
# ===============================

class HealthDBResponse(BaseModel):
    """Response schema for /health/db endpoint."""
    status: str = Field(..., description="Service status, e.g. 'ok'")
    db_tables: list[str] = Field(..., description="List of table names in the DB")
    has_superstore_clean: bool = Field(..., description="Whether 'superstore_clean' table exists")


# ===============================
# Reusable Items (Sales)
# ===============================

class MonthlySalesItem(BaseModel):
    """
    Aggregated monthly sales metrics.
    Used as an item in monthly sales responses.
    """
    month: str = Field(
        ...,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Month in YYYY-MM format"
    )
    total_sales: float = Field(
        ...,
        ge=0,
        description="Total sales amount for the month"
    )
    total_profit: float = Field(
        ...,
        description="Total profit amount for the month (can be negative)"
    )

class RegionSalesItem(BaseModel):
    """
    Aggregate sales metrics grouped by region.
    """
    region: str
    total_sales: float = Field(...,ge=0, description="Total sales amount for the region")
    total_profit: float = Field(..., description="Total profit amount for the region")
    total_orders : int = Field(..., ge=0, description="Total order amount for the region")

class CategorySalesItem(BaseModel):
    """
    Aggregate sales metrics grouped by category.
    """
    category: str
    total_sales: float = Field(..., description="Total sales amount for the category")
    total_profit: float = Field(..., description="Total profit amount for the category")
    total_orders: int = Field(..., ge=0, description="Total order amount for the category")


# ===============================
# Sales Models
# ===============================

class DailySalesResponse(BaseModel):
    """
    API response model for daily sales summary.
    """
    sales_date: date
    total_orders: int
    total_revenue: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sales_date": "2011-11-09",
                "total_order": 2,
                "total_revenue": 1574.25
            }
        }
    )

class MonthlySalesResponse(BaseModel):
    """
    Offset-based paginated response for monthly sales aggregation.
    Returned by GET /sales/monthly.
    """

    # Metadata / observability
    generated_at: datetime = Field(..., description="UTC timestamp when the response was generated")
    query_ms: float = Field(..., ge=0, description="Database query execution time in milliseconds")

    # Echo request parameters (useful for debugging and caching)
    start: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Start month (YYYY-MM)")
    end: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="End month (YYYY-MM)")
    decimals: int = Field(..., ge=0, le=6, description="Decimal places applied to numeric fields")
    sort: MonthlySort = Field(..., description="Sort order for the result set")

    # Pagination request/derived fields
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    offset: int = Field(..., ge=0, description="Offset from the beginning of the result set")
    current_page: int = Field(..., ge=1, description="Current page number (1-based)")
    prev_page: Optional[int] = Field(None, ge=1, description="Previous page number, if exists")
    next_page: Optional[int] = Field(None, ge=1, description="Next page number, if exists")

    # Pagination summary
    count: int = Field(..., ge=0, description="Number of items in this response page")
    has_more: bool = Field(..., description="Whether more items exist after this page")
    total_count: int = Field(..., ge=0, description="Total number of items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")

    # Data
    data: List[MonthlySalesItem] = Field(..., description="Monthly aggregated metrics")

class MonthlySalesCursorResponse(BaseModel):
    """
    Cursor-based paginated response for monthly sales aggregation.
    Used by GET /sales/monthly/cursor endpoint.
    """

    # Metadata / observability
    generated_at: datetime = Field(..., description="UTC timestamp when the response was generated")
    query_ms: float = Field(..., ge=0, description="Database query execution time in milliseconds")

    # Echo request parameters
    start: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Start month (YYYY-MM)")
    end: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="End month (YYYY-MM)")
    decimals: int = Field(..., ge=0, le=6, description="Decimal places applied to numeric fields")
    limit: int = Field(..., ge=1, le=100, description="Maximum number of records returned")
    sort: MonthlySort = Field(..., description="Sort order applied to results")

    # Cursor pagination
    cursor: Optional[str] = Field(None, description="Cursor representing the current position")
    next_cursor: Optional[str] = Field(None, description="Cursor to retrieve the next page")
    next_url: Optional[str] = Field(None,description="Convenience URL for fetching the next page (optional helper for clients)")
    has_more: bool = Field(..., description="Whether more records are available after this page")

    # Results
    count: int = Field(..., ge=0, description="Number of records in this response")
    data: List[MonthlySalesItem] = Field(..., description="Monthly aggregated sales metrics")

class RegionSalesResponse(BaseModel):
    """
    Sorting options for sales grouped by region.
    Used by GET /sales/by-region endpoint.
    """

    # Metadata / observability
    generated_at: datetime = Field(..., description="UTC timestamp when the response was generated")
    query_ms: float = Field(..., description="Database query execution time in milliseconds")

    # Echo request parameters (useful for debugging and caching)
    start: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Start month (YYYY-MM)")
    end: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="End month (YYYY-MM)")
    decimals: int = Field(..., ge=0, le=6, description="Decimal places applied to numeric fields")
    sort: RegionSort = Field(..., description="Sort order for the result set")

    # Pagination request/derived fields
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    offset: int = Field(..., ge=0, description="Offset from the beginning of the result set")

    # Pagination summary
    count: int = Field(...,ge=0 , description="Number of items in this response page")
    has_more: bool = Field(..., description="Whether more items exist after this page")
    total_count: int = Field(..., ge=0, description="Total number of items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    page: int = Field(..., ge=1, description="Current page number (1-based)")
    prev_page: Optional[int] = Field(None, ge=1, description="Previous page number, if exists")
    next_page: Optional[int] = Field(None, ge=1, description="Next page number, if exists")

    # Data
    data: List[RegionSalesItem] = Field(..., description="Monthly aggregated sales metrics")

class CategorySalesResponse(BaseModel):
    """
    Sorting options for sales grouped by category.
    Used by GET /sales/by-category endpoint.
    """

    # Metadata / observability
    generated_at: datetime = Field(..., description="UTC timestamp when the response was generated")
    query_ms: float = Field(..., description="Database query execution time in milliseconds")

    # Echo request parameters (useful for debugging and caching)
    start: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Start month (YYYY-MM)")
    end: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="End month (YYYY-MM)")
    decimals: int = Field(..., ge=0, le=6, description="Decimal places applied to numeric fields")
    sort: CategorySort = Field(..., description="Sort order for the result set")

    # Pagination request/derived fields
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    offset: int = Field(..., ge=0, description="Offset from the beginning of the result set")

    # Pagination summary
    count: int = Field(...,ge=0 , description="Number of items in this response page")
    has_more: bool = Field(..., description="Whether more items exist after this page")
    total_count: int = Field(..., ge=0, description="Total number of items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    page: int = Field(..., ge=1, description="Current page number (1-based)")
    prev_page: Optional[int] = Field(None, ge=1, description="Previous page number, if exists")
    next_page: Optional[int] = Field(None, ge=1, description="Next page number, if exists")

    # Data
    data: List[CategorySalesItem] = Field(..., description="Monthly aggregated sales metrics")