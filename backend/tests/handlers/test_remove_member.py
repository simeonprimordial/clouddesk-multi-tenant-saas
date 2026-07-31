"""Tests for the remove-member Lambda handler."""

import json
from unittest.mock import patch

from remove_member.handler import lambda_handler


CURRENT_USER = {
    "id": "owner-123",
    "status": "active",
}


def make_event(
    tenant_id="tenant-123",
    user_id="member-123",
):
    return {
        "pathParameters": {
            "tenantId": tenant_id,
            "userId": user_id,
        }
    }


def response_body(response):
    return json.loads(response["body"])


@patch("remove_member.handler.deactivate_tenant_member")
@patch("remove_member.handler.get_tenant_member")
@patch("remove_member.handler.require_owner")
@patch("remove_member.handler.get_current_user")
def test_remove_member_success(
    mock_get_current_user,
    mock_require_owner,
    mock_get_tenant_member,
    mock_deactivate_tenant_member,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_tenant_member.return_value = {
        "tenant_id": "tenant-123",
        "user_id": "member-123",
        "role": "admin",
        "status": "active",
    }
    mock_deactivate_tenant_member.return_value = {
        "tenant_id": "tenant-123",
        "user_id": "member-123",
        "role": "admin",
        "status": "inactive",
    }

    response = lambda_handler(
        make_event(),
        None,
    )

    assert response["statusCode"] == 200

    body = response_body(response)

    assert body["success"] is True
    assert body["data"]["status"] == "inactive"

    mock_deactivate_tenant_member.assert_called_once_with(
        tenant_id="tenant-123",
        user_id="member-123",
    )


@patch("remove_member.handler.get_tenant_member")
@patch("remove_member.handler.require_owner")
@patch("remove_member.handler.get_current_user")
def test_remove_member_rejects_missing_member(
    mock_get_current_user,
    mock_require_owner,
    mock_get_tenant_member,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_tenant_member.return_value = None

    response = lambda_handler(
        make_event(),
        None,
    )

    assert response["statusCode"] == 404
    assert response_body(response)["message"] == (
        "Tenant member not found."
    )


@patch("remove_member.handler.get_tenant_member")
@patch("remove_member.handler.require_owner")
@patch("remove_member.handler.get_current_user")
def test_remove_member_protects_tenant_owner(
    mock_get_current_user,
    mock_require_owner,
    mock_get_tenant_member,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_tenant_member.return_value = {
        "tenant_id": "tenant-123",
        "user_id": "owner-123",
        "role": "owner",
        "status": "active",
    }

    response = lambda_handler(
        make_event(user_id="owner-123"),
        None,
    )

    assert response["statusCode"] == 400
    assert response_body(response)["message"] == (
        "The tenant owner cannot be removed."
    )


@patch("remove_member.handler.get_tenant_member")
@patch("remove_member.handler.require_owner")
@patch("remove_member.handler.get_current_user")
def test_remove_member_rejects_self_removal(
    mock_get_current_user,
    mock_require_owner,
    mock_get_tenant_member,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_tenant_member.return_value = {
        "tenant_id": "tenant-123",
        "user_id": "owner-123",
        "role": "admin",
        "status": "active",
    }

    response = lambda_handler(
        make_event(user_id="owner-123"),
        None,
    )

    assert response["statusCode"] == 400
    assert response_body(response)["message"] == (
        "You cannot remove yourself from the tenant."
    )