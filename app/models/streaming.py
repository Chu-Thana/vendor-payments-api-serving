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