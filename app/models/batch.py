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

class SpendingByDepartmentItem(BaseModel):
    fiscal_year: int
    organization_group: str
    department: str
    total_vouchers_paid: float
    total_vouchers_pending: float
    total_encumbrance_balance: float
    total_pending_retainage: float
    record_count: int
    unique_suppliers: int
    negative_paid_records: int
    large_paid_1m_records: int
    missing_po_date_records: int


class SpendingByDepartmentResponse(BaseModel):
    total_count: int
    count: int
    limit: int
    offset: int
    data: list[SpendingByDepartmentItem]

class TopSupplierItem(BaseModel):
    supplier_name: str
    total_vouchers_paid: float
    total_vouchers_pending: float
    total_encumbrance_balance: float
    total_pending_retainage: float
    record_count: int
    unique_suppliers: int
    negative_paid_records: int
    large_paid_1m_records: int
    missing_po_date_records: int


class TopSuppliersResponse(BaseModel):
    total_count: int
    count: int
    limit: int
    offset: int
    data: list[TopSupplierItem]

class PendingByDepartmentItem(BaseModel):
    fiscal_year: int
    department: str
    total_vouchers_paid: float
    total_vouchers_pending: float
    total_encumbrance_balance: float
    total_pending_retainage: float
    record_count: int
    unique_suppliers: int
    negative_paid_records: int
    large_paid_1m_records: int
    missing_po_date_records: int


class PendingByDepartmentResponse(BaseModel):
    total_count: int
    count: int
    limit: int
    offset: int
    data: list[PendingByDepartmentItem]

class FundCategorySummaryItem(BaseModel):
    fiscal_year: int
    fund_type: str
    fund_category: str
    total_vouchers_paid: float
    total_vouchers_pending: float
    total_encumbrance_balance: float
    total_pending_retainage: float
    record_count: int
    unique_suppliers: int
    negative_paid_records: int
    large_paid_1m_records: int
    missing_po_date_records: int


class FundCategorySummaryResponse(BaseModel):
    total_count: int
    count: int
    limit: int
    offset: int
    data: list[FundCategorySummaryItem]