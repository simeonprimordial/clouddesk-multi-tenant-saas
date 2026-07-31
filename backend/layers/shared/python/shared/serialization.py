"""
Utilities for converting Python objects into JSON-compatible values.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def serialize_value(value: Any) -> Any:
    """Convert a value into a JSON-compatible representation."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        return float(value)

    return value


def serialize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Serialize every value in a dictionary."""

    return {key: serialize_value(value) for key, value in data.items()}


def serialize_list(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Serialize every dictionary in a list."""

    return [serialize_dict(row) for row in rows]
