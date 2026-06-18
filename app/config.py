from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
BATCH_DATA_DIR = DATA_DIR / "batch"

SPENDING_BY_FISCAL_YEAR_FILE = (
    BATCH_DATA_DIR / "mart_spending_by_fiscal_year.csv"
)

SPENDING_BY_DEPARTMENT_FILE = (
    BATCH_DATA_DIR / "mart_spending_by_department.csv"
)

TOP_SUPPLIERS_FILE = (
    BATCH_DATA_DIR / "mart_spending_by_supplier_top_n.csv"
)

PENDING_BY_DEPARTMENT_FILE = (
    BATCH_DATA_DIR / "mart_pending_by_department.csv"
)

FUND_CATEGORY_SUMMARY_FILE = (
    BATCH_DATA_DIR / "mart_fund_category_summary.csv"
)

STREAMING_SAMPLE_FILE = (
    DATA_DIR
    / "streaming"
    / "vendor_payments_streaming_sample.jsonl"
)

API_CACHE_TTL_SECONDS = 60.0