"""Tests for the update-member Lambda handler."""

import json
from unittest.mock import patch

from update_member.handler import lambda_handler


CURRENT_USER = {
    "id": "owner-123",
    "status": "active",
}


def make_event(
    role="admin",
    tenant_id="tenant-123",
    user_id="member-123",
):
    return {
        "pathParameters": {
            "tenantId": tenant_id,
            "userId": user_id,
        },
        "body": json.dumps({"role": role}),
    }


def response_body(response):
    return json.loads(response["body"])


@patch("update_member.handler.update_tenant_member_role")
@patch("update_member.handler.get_tenant_member")
@patch("update_member.handler.require_owner")
@patch("update_member.handler.get_current_user")
def test_update_member_role_success(
    mock_get_current_user,
    mock_require_owner,
    mock_get_tenant_member,
    mock_update_tenant_member_role,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_tenant_member.return_value = {
        "tenant_id": "tenant-123",
        "user_id": "member-123",
        "role": "member",
        "status": "active",
    }
    mock_update_tenant_member_role.return_value = {
        "tenant_id": "tenant-123",
        "user_id": "member-123",
        "role": "admin",
        "status": "active",
    }

    response = lambda_handler(
        make_event(role="admin"),
        None,
    )

    assert response["statusCode"] == 200

    body = response_body(response)

    assert body["success"] is True
    assert body["data"]["role"] == "admin"

    mock_require_owner.assert_called_once_with(
        tenant_id="tenant-123",
        current_user=CURRENT_USER,
    )


@patch("update_member.handler.require_owner")
@patch("update_member.handler.get_current_user")
def test_update_member_rejects_invalid_role(
    mock_get_current_user,
    mock_require_owner,
):
    mock_get_current_user.return_value = CURRENT_USER

    response = lambda_handler(
        make_event(role="owner"),
        None,
    )

    assert response["statusCode"] == 400
    assert response_body(response)["message"] == (
        "Role must be either admin or member."
    )


@patch("update_member.handler.get_tenant_member")
@patch("update_member.handler.require_owner")
@patch("update_member.handler.get_current_user")
def test_update_member_rejects_missing_member(
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


@patch("update_member.handler.get_tenant_member")
@patch("update_member.handler.require_owner")
@patch("update_member.handler.get_current_user")
def test_update_member_protects_owner_role(
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
        make_event(
            role="member",
            user_id="owner-123",
        ),
        None,
    )

    assert response["statusCode"] == 400
    assert response_body(response)["message"] == (
        "The tenant owner's role cannot be changed."
    )