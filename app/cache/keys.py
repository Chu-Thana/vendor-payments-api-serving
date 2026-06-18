from __future__ import annotations

from typing import Any


def build_cache_key(
    namespace: str,
    **parameters: Any,
) -> str:
    normalized_parameters = [
        f"{name}={_normalize_value(value)}"
        for name, value in sorted(parameters.items())
    ]

    if not normalized_parameters:
        return namespace

    return f"{namespace}:{':'.join(normalized_parameters)}"


def _normalize_value(value: Any) -> str:
    if value is None:
        return "all"

    if isinstance(value, str):
        return value.strip().casefold()

    return str(value)