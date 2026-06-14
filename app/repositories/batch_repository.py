import csv
from pathlib import Path

from app.config import (
    PENDING_BY_DEPARTMENT_FILE,
    SPENDING_BY_DEPARTMENT_FILE,
    SPENDING_BY_FISCAL_YEAR_FILE,
    TOP_SUPPLIERS_FILE,
)

def read_spending_by_fiscal_year(
    file_path: Path = SPENDING_BY_FISCAL_YEAR_FILE,
) -> list[dict[str, int | float]]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Spending by fiscal year file not found: {file_path}"
        )

    records: list[dict[str, int | float]] = []

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            records.append(
                {
                    "fiscal_year": int(row["fiscal_year"]),
                    "total_vouchers_paid": float(
                        row["total_vouchers_paid"]
                    ),
                    "total_vouchers_pending": float(
                        row["total_vouchers_pending"]
                    ),
                    "total_encumbrance_balance": float(
                        row["total_encumbrance_balance"]
                    ),
                    "total_pending_retainage": float(
                        row["total_pending_retainage"]
                    ),
                    "record_count": int(row["record_count"]),
                    "unique_suppliers": int(row["unique_suppliers"]),
                    "negative_paid_records": int(
                        row["negative_paid_records"]
                    ),
                    "large_paid_1m_records": int(
                        row["large_paid_1m_records"]
                    ),
                    "missing_po_date_records": int(
                        row["missing_po_date_records"]
                    ),
                }
            )

    return records

def read_spending_by_department(
    file_path: Path = SPENDING_BY_DEPARTMENT_FILE,
) -> list[dict[str, str | int | float]]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Spending by department file not found: {file_path}"
        )

    records: list[dict[str, str | int | float]] = []

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            records.append(
                {
                    "fiscal_year": int(row["fiscal_year"]),
                    "organization_group": row["organization_group"],
                    "department": row["department"],
                    "total_vouchers_paid": float(
                        row["total_vouchers_paid"]
                    ),
                    "total_vouchers_pending": float(
                        row["total_vouchers_pending"]
                    ),
                    "total_encumbrance_balance": float(
                        row["total_encumbrance_balance"]
                    ),
                    "total_pending_retainage": float(
                        row["total_pending_retainage"]
                    ),
                    "record_count": int(row["record_count"]),
                    "unique_suppliers": int(row["unique_suppliers"]),
                    "negative_paid_records": int(
                        row["negative_paid_records"]
                    ),
                    "large_paid_1m_records": int(
                        row["large_paid_1m_records"]
                    ),
                    "missing_po_date_records": int(
                        row["missing_po_date_records"]
                    ),
                }
            )

    return records

def read_top_suppliers(
    file_path: Path = TOP_SUPPLIERS_FILE,
) -> list[dict[str, str | int | float]]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Top suppliers file not found: {file_path}"
        )

    records: list[dict[str, str | int | float]] = []

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            records.append(
                {
                    "supplier_name": row["supplier_name"],
                    "total_vouchers_paid": float(
                        row["total_vouchers_paid"]
                    ),
                    "total_vouchers_pending": float(
                        row["total_vouchers_pending"]
                    ),
                    "total_encumbrance_balance": float(
                        row["total_encumbrance_balance"]
                    ),
                    "total_pending_retainage": float(
                        row["total_pending_retainage"]
                    ),
                    "record_count": int(row["record_count"]),
                    "unique_suppliers": int(row["unique_suppliers"]),
                    "negative_paid_records": int(
                        row["negative_paid_records"]
                    ),
                    "large_paid_1m_records": int(
                        row["large_paid_1m_records"]
                    ),
                    "missing_po_date_records": int(
                        row["missing_po_date_records"]
                    ),
                }
            )

    return records

def read_pending_by_department(
    file_path: Path = PENDING_BY_DEPARTMENT_FILE,
) -> list[dict[str, str | int | float]]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Pending by department file not found: {file_path}"
        )

    records: list[dict[str, str | int | float]] = []

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            records.append(
                {
                    "fiscal_year": int(row["fiscal_year"]),
                    "department": row["department"],
                    "total_vouchers_paid": float(
                        row["total_vouchers_paid"]
                    ),
                    "total_vouchers_pending": float(
                        row["total_vouchers_pending"]
                    ),
                    "total_encumbrance_balance": float(
                        row["total_encumbrance_balance"]
                    ),
                    "total_pending_retainage": float(
                        row["total_pending_retainage"]
                    ),
                    "record_count": int(row["record_count"]),
                    "unique_suppliers": int(row["unique_suppliers"]),
                    "negative_paid_records": int(
                        row["negative_paid_records"]
                    ),
                    "large_paid_1m_records": int(
                        row["large_paid_1m_records"]
                    ),
                    "missing_po_date_records": int(
                        row["missing_po_date_records"]
                    ),
                }
            )

    return records