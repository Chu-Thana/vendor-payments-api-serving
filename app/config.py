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