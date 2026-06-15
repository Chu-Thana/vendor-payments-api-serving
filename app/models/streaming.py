from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class StreamingEventItem(BaseModel):
    event_id: str
    event_type: str
    event_timestamp: datetime
    source_system: str
    fiscal_year: int
    supplier_name: str
    department: str
    vouchers_paid: float
    payment_amount: float
    dedup_status: str
    ingested_at: datetime


class StreamingEventsResponse(BaseModel):
    total_count: int
    count: int
    limit: int
    offset: int
    data: list[StreamingEventItem]

class StreamingYearCount(BaseModel):
    fiscal_year: int
    event_count: int


class StreamingDedupCount(BaseModel):
    dedup_status: str
    event_count: int


class StreamingSummaryResponse(BaseModel):
    total_events: int
    total_payment_amount: float
    unique_departments: int
    unique_suppliers: int
    minimum_fiscal_year: int
    maximum_fiscal_year: int
    events_by_fiscal_year: list[StreamingYearCount]
    events_by_dedup_status: list[StreamingDedupCount]

class StreamingDepartmentSummaryItem(BaseModel):
    department: str
    event_count: int
    total_payment_amount: float
    unique_suppliers: int
    minimum_fiscal_year: int
    maximum_fiscal_year: int


class StreamingDepartmentSummaryResponse(BaseModel):
    total_count: int
    count: int
    limit: int
    offset: int
    data: list[StreamingDepartmentSummaryItem]