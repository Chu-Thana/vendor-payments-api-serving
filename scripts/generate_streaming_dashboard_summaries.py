from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = Path(
    r"E:\dev\vendor-payments-streaming-pipeline"
    r"\output\staging"
    r"\vendor_payments_streaming_staging.jsonl"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "streaming"

SUMMARY_FILE = (
    OUTPUT_DIR / "vendor_payments_streaming_summary.json"
)

DEPARTMENT_SUMMARY_FILE = (
    OUTPUT_DIR
    / "vendor_payments_streaming_department_summary.json"
)


def parse_number(value: Any) -> float:
    if value in (None, ""):
        return 0.0

    return float(value)


def main() -> None:
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Streaming source file not found: {SOURCE_FILE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_events = 0
    total_payment_amount = 0.0

    fiscal_year_counts: Counter[int] = Counter()
    dedup_status_counts: Counter[str] = Counter()

    unique_departments: set[str] = set()
    unique_suppliers: set[str] = set()

    department_metrics: dict[str, dict[str, Any]] = {}

    with SOURCE_FILE.open(
        mode="r",
        encoding="utf-8-sig",
    ) as source_file:
        for line_number, line in enumerate(
            source_file,
            start=1,
        ):
            stripped_line = line.strip()

            if not stripped_line:
                continue

            try:
                event = json.loads(stripped_line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at line {line_number}"
                ) from exc

            payload = event.get("payload") or {}

            fiscal_year_value = payload.get("fiscal_year")
            department_value = payload.get("department")
            supplier_value = payload.get("supplier_name")

            payment_amount = parse_number(
                event.get("payment_amount")
            )

            dedup_status = str(
                event.get("dedup_status") or "unknown"
            )

            if fiscal_year_value is None:
                continue

            fiscal_year = int(fiscal_year_value)
            department = str(
                department_value or "Unknown"
            )
            supplier = str(
                supplier_value or "Unknown"
            )

            total_events += 1
            total_payment_amount += payment_amount

            fiscal_year_counts[fiscal_year] += 1
            dedup_status_counts[dedup_status] += 1

            unique_departments.add(department)
            unique_suppliers.add(supplier)

            if department not in department_metrics:
                department_metrics[department] = {
                    "department": department,
                    "event_count": 0,
                    "total_payment_amount": 0.0,
                    "suppliers": set(),
                    "minimum_fiscal_year": fiscal_year,
                    "maximum_fiscal_year": fiscal_year,
                }

            metrics = department_metrics[department]

            metrics["event_count"] += 1
            metrics["total_payment_amount"] += payment_amount
            metrics["suppliers"].add(supplier)

            metrics["minimum_fiscal_year"] = min(
                metrics["minimum_fiscal_year"],
                fiscal_year,
            )

            metrics["maximum_fiscal_year"] = max(
                metrics["maximum_fiscal_year"],
                fiscal_year,
            )

    if total_events == 0:
        raise ValueError(
            "Streaming source contains no valid events"
        )

    fiscal_years = sorted(fiscal_year_counts)

    summary = {
        "total_events": total_events,
        "total_payment_amount": round(
            total_payment_amount,
            2,
        ),
        "unique_departments": len(unique_departments),
        "unique_suppliers": len(unique_suppliers),
        "minimum_fiscal_year": min(fiscal_years),
        "maximum_fiscal_year": max(fiscal_years),
        "events_by_fiscal_year": [
            {
                "fiscal_year": fiscal_year,
                "event_count": fiscal_year_counts[
                    fiscal_year
                ],
            }
            for fiscal_year in fiscal_years
        ],
        "events_by_dedup_status": [
            {
                "dedup_status": dedup_status,
                "event_count": event_count,
            }
            for dedup_status, event_count
            in sorted(dedup_status_counts.items())
        ],
    }

    department_items = []

    for department, metrics in department_metrics.items():
        department_items.append(
            {
                "department": department,
                "event_count": metrics["event_count"],
                "total_payment_amount": round(
                    metrics["total_payment_amount"],
                    2,
                ),
                "unique_suppliers": len(
                    metrics["suppliers"]
                ),
                "minimum_fiscal_year": (
                    metrics["minimum_fiscal_year"]
                ),
                "maximum_fiscal_year": (
                    metrics["maximum_fiscal_year"]
                ),
            }
        )

    department_items.sort(
        key=lambda item: item["event_count"],
        reverse=True,
    )

    department_summary = {
        "total_count": len(department_items),
        "data": department_items,
    }

    SUMMARY_FILE.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    DEPARTMENT_SUMMARY_FILE.write_text(
        json.dumps(
            department_summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("Streaming dashboard summaries generated")
    print(f"Total events: {total_events:,}")
    print(
        "Unique departments: "
        f"{len(unique_departments):,}"
    )
    print(
        "Unique suppliers: "
        f"{len(unique_suppliers):,}"
    )
    print(f"Summary: {SUMMARY_FILE}")
    print(
        "Department summary: "
        f"{DEPARTMENT_SUMMARY_FILE}"
    )


if __name__ == "__main__":
    main()