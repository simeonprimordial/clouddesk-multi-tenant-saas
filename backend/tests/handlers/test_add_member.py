"""Tests for the add-member Lambda handler."""

import json
from unittest.mock import patch

from add_member.handler import lambda_handler

CURRENT_USER = {
    "id": "owner-123",
    "status": "active",
}

TARGET_USER = {
    "id": "member-123",
    "email": "member@example.com",
    "first_name": "Cloud",
    "last_name": "Member",
    "status": "active",
}


def make_event(body=None, tenant_id="tenant-123"):
    return {
        "pathParameters": {
            "tenantId": tenant_id,
        },
        "body": json.dumps(body or {}),
    }


def response_body(response):
    return json.loads(response["body"])


@patch("add_member.handler.create_tenant_membership")
@patch("add_member.handler.get_membership")
@patch("add_member.handler.get_user_by_email")
@patch("add_member.handler.require_admin")
@patch("add_member.handler.get_current_user")
def test_add_member_success(
    mock_get_current_user,
    mock_require_admin,
    mock_get_user_by_email,
    mock_get_membership,
    mock_create_tenant_membership,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_user_by_email.return_value = TARGET_USER
    mock_get_membership.return_value = None
    mock_create_tenant_membership.return_value = {
        "tenant_id": "tenant-123",
        "user_id": "member-123",
        "role": "member",
        "status": "active",
    }

    response = lambda_handler(
        make_event(
            {
                "email": "MEMBER@example.com",
                "role": "member",
            }
        ),
        None,
    )

    assert response["statusCode"] == 201

    body = response_body(response)

    assert body["success"] is True
    assert body["data"]["user"]["email"] == "member@example.com"
    assert body["data"]["membership"]["role"] == "member"

    mock_require_admin.assert_called_once_with(
        tenant_id="tenant-123",
        current_user=CURRENT_USER,
    )

    mock_get_user_by_email.assert_called_once_with("member@example.com")


@patch("add_member.handler.get_current_user")
def test_add_member_requires_tenant_id(mock_get_current_user):
    mock_get_current_user.return_value = CURRENT_USER

    response = lambda_handler(
        {
            "pathParameters": {},
            "body": json.dumps({"email": "member@example.com"}),
        },
        None,
    )

    assert response["statusCode"] == 400
    assert response_body(response)["message"] == ("Tenant ID is required.")


@patch("add_member.handler.require_admin")
@patch("add_member.handler.get_current_user")
def test_add_member_rejects_invalid_role(
    mock_get_current_user,
    mock_require_admin,
):
    mock_get_current_user.return_value = CURRENT_USER

    response = lambda_handler(
        make_event(
            {
                "email": "member@example.com",
                "role": "owner",
            }
        ),
        None,
    )

    assert response["statusCode"] == 400
    assert response_body(response)["message"] == (
        "Role must be either admin or member."
    )


@patch("add_member.handler.get_user_by_email")
@patch("add_member.handler.require_admin")
@patch("add_member.handler.get_current_user")
def test_add_member_rejects_unknown_user(
    mock_get_current_user,
    mock_require_admin,
    mock_get_user_by_email,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_user_by_email.return_value = None

    response = lambda_handler(
        make_event(
            {
                "email": "missing@example.com",
                "role": "member",
            }
        ),
        None,
    )

    assert response["statusCode"] == 404
    assert response_body(response)["message"] == (
        "No active CloudDesk user was found with that email."
    )


@patch("add_member.handler.get_membership")
@patch("add_member.handler.get_user_by_email")
@patch("add_member.handler.require_admin")
@patch("add_member.handler.get_current_user")
def test_add_member_rejects_duplicate_membership(
    mock_get_current_user,
    mock_require_admin,
    mock_get_user_by_email,
    mock_get_membership,
):
    mock_get_current_user.return_value = CURRENT_USER
    mock_get_user_by_email.return_value = TARGET_USER
    mock_get_membership.return_value = {
        "tenant_id": "tenant-123",
        "user_id": "member-123",
        "status": "active",
    }

    response = lambda_handler(
        make_event(
            {
                "email": "member@example.com",
                "role": "member",
            }
        ),
        None,
    )

    assert response["statusCode"] == 409
    assert response_body(response)["message"] == (
        "The user already belongs to this tenant."
    )
