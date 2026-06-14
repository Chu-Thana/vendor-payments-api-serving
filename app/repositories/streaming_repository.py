from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import STREAMING_SAMPLE_FILE


def read_streaming_events(
    file_path: Path = STREAMING_SAMPLE_FILE,
) -> list[dict[str, Any]]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Streaming sample file not found: {file_path}"
        )

    events: list[dict[str, Any]] = []

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
    ) as jsonl_file:
        for line_number, line in enumerate(
            jsonl_file,
            start=1,
        ):
            stripped_line = line.strip()

            if not stripped_line:
                continue

            try:
                event = json.loads(stripped_line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Invalid JSON in streaming sample "
                    f"at line {line_number}"
                ) from exc

            payload = event.get("payload") or {}

            events.append(
                {
                    "event_id": event.get("event_id"),
                    "event_type": event.get("event_type"),
                    "event_timestamp": event.get(
                        "event_timestamp"
                    ),
                    "source_system": event.get(
                        "source_system"
                    ),
                    "fiscal_year": payload.get(
                        "fiscal_year"
                    ),
                    "supplier_name": payload.get(
                        "supplier_name"
                    ),
                    "department": payload.get(
                        "department"
                    ),
                    "vouchers_paid": payload.get(
                        "vouchers_paid"
                    ),
                    "payment_amount": event.get(
                        "payment_amount"
                    ),
                    "dedup_status": event.get(
                        "dedup_status"
                    ),
                    "ingested_at": event.get(
                        "ingested_at"
                    ),
                }
            )

    return events