from pydantic import BaseModel


class SpendingByFiscalYearItem(BaseModel):
    fiscal_year: int
    total_vouchers_paid: float
    total_vouchers_pending: float
    total_encumbrance_balance: float
    total_pending_retainage: float
    record_count: int
    unique_suppliers: int
    negative_paid_records: int
    large_paid_1m_records: int
    missing_po_date_records: int


class SpendingByFiscalYearResponse(BaseModel):
    count: int
    data: list[SpendingByFiscalYearItem]