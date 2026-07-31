"""Tests for CloudDesk API response helpers."""

import json

from shared.response import error, success


def test_success_returns_expected_response():
    response = success(
        message="Operation completed.",
        data={"tenant_id": "tenant-123"},
    )

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"

    body = json.loads(response["body"])

    assert body == {
        "success": True,
        "message": "Operation completed.",
        "data": {
            "tenant_id": "tenant-123",
        },
    }


def test_success_accepts_custom_status_code():
    response = success(
        message="Tenant created.",
        data={"name": "NovaTech"},
        status_code=201,
    )

    assert response["statusCode"] == 201


def test_success_defaults_data_to_none():
    response = success(message="Request completed.")

    body = json.loads(response["body"])

    assert body["success"] is True
    assert body["data"] is None


def test_error_returns_expected_response():
    response = error(
        message="Tenant not found.",
        status_code=404,
    )

    assert response["statusCode"] == 404
    assert response["headers"]["Content-Type"] == "application/json"

    body = json.loads(response["body"])

    assert body == {
        "success": False,
        "message": "Tenant not found.",
    }


def test_error_defaults_to_500():
    response = error(message="Unexpected error.")

    assert response["statusCode"] == 500