"""Tests for CloudDesk serialization helpers."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from shared.serialization import (
    serialize_dict,
    serialize_list,
    serialize_value,
)


def test_serialize_uuid():
    value = UUID("b763fbb4-8fe3-4198-a69b-990a1e35b92c")

    assert serialize_value(value) == str(value)


def test_serialize_datetime():
    value = datetime(
        2026,
        7,
        31,
        12,
        30,
        tzinfo=timezone.utc,
    )

    assert serialize_value(value) == value.isoformat()


def test_serialize_date():
    value = date(2026, 7, 31)

    assert serialize_value(value) == "2026-07-31"


def test_serialize_decimal():
    value = Decimal("19.95")

    assert serialize_value(value) == 19.95


def test_serialize_regular_value_unchanged():
    assert serialize_value("active") == "active"
    assert serialize_value(5) == 5
    assert serialize_value(None) is None


def test_serialize_dict():
    tenant_id = UUID("b763fbb4-8fe3-4198-a69b-990a1e35b92c")

    result = serialize_dict(
        {
            "id": tenant_id,
            "name": "NovaTech",
            "status": "active",
        }
    )

    assert result == {
        "id": str(tenant_id),
        "name": "NovaTech",
        "status": "active",
    }


def test_serialize_list():
    rows = [
        {
            "id": UUID("b763fbb4-8fe3-4198-a69b-990a1e35b92c"),
            "name": "NovaTech",
        },
        {
            "id": UUID("716f39f8-6ec8-46c1-a8a9-e430a1f67310"),
            "name": "FinTrust",
        },
    ]

    result = serialize_list(rows)

    assert result == [
        {
            "id": "b763fbb4-8fe3-4198-a69b-990a1e35b92c",
            "name": "NovaTech",
        },
        {
            "id": "716f39f8-6ec8-46c1-a8a9-e430a1f67310",
            "name": "FinTrust",
        },
    ]
