"""Tests for the create-tenant Lambda handler."""

import json
from unittest.mock import patch

from create_tenant.handler import create_slug, lambda_handler


CURRENT_USER = {
    "id": "user-123",
    "status": "active",
}


def make_event(body):
    return {
        "body": json.dumps(body),
    }


def response_body(response):
    return json.loads(response["body"])


def test_create_slug_normalizes_tenant_name():
    assert create_slug("  NovaTech Solutions  ") == "novatech-solutions"


@patch("create_tenant.handler.create_tenant_with_owner")
@patch("create_tenant.handler.get_tenant_by_slug")
@patch("create_tenant.handler.get_current_user")
def test_create_tenant_success(
    mock_get_current_user,
    mock_get_tenant_by_slug,
    mock_create_tenant_with_owner,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_tenant_by_slug.return_value = None
    mock_create_tenant_with_owner.return_value = {
        "id": "tenant-123",
        "name": "NovaTech",
        "slug": "novatech",
        "status": "active",
    }

    response = lambda_handler(
        make_event({"name": "NovaTech"}),
        None,
    )

    assert response["statusCode"] == 201

    body = response_body(response)

    assert body["success"] is True
    assert body["message"] == "Tenant created successfully."
    assert body["data"]["slug"] == "novatech"

    mock_create_tenant_with_owner.assert_called_once_with(
        name="NovaTech",
        slug="novatech",
        owner_user_id="user-123",
    )


@patch("create_tenant.handler.get_current_user")
def test_create_tenant_requires_name(mock_get_current_user):
    mock_get_current_user.return_value = CURRENT_USER

    response = lambda_handler(
        make_event({}),
        None,
    )

    assert response["statusCode"] == 400
    assert response_body(response)["message"] == (
        "Tenant name is required."
    )


@patch("create_tenant.handler.get_current_user")
def test_create_tenant_rejects_invalid_json(mock_get_current_user):
    mock_get_current_user.return_value = CURRENT_USER

    response = lambda_handler(
        {"body": "{invalid-json"},
        None,
    )

    assert response["statusCode"] == 400
    assert response_body(response)["message"] == (
        "Request body must contain valid JSON."
    )


@patch("create_tenant.handler.get_tenant_by_slug")
@patch("create_tenant.handler.get_current_user")
def test_create_tenant_rejects_duplicate_slug(
    mock_get_current_user,
    mock_get_tenant_by_slug,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_tenant_by_slug.return_value = {
        "id": "existing-tenant",
        "slug": "novatech",
    }

    response = lambda_handler(
        make_event({"name": "NovaTech"}),
        None,
    )

    assert response["statusCode"] == 409
    assert response_body(response)["message"] == (
        "A tenant with this name already exists."
    )