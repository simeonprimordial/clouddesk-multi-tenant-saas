"""Tests for CloudDesk authorization helpers."""

from unittest.mock import patch

import pytest

from shared.authorization import (
    AuthorizationError,
    require_admin,
    require_membership,
    require_owner,
)


CURRENT_USER = {
    "id": "user-123",
    "status": "active",
}


@patch("shared.authorization.get_membership")
def test_require_membership_returns_active_membership(
    mock_get_membership,
):
    membership = {
        "tenant_id": "tenant-123",
        "user_id": "user-123",
        "role": "member",
        "status": "active",
    }

    mock_get_membership.return_value = membership

    result = require_membership(
        tenant_id="tenant-123",
        current_user=CURRENT_USER,
    )

    assert result == membership

    mock_get_membership.assert_called_once_with(
        tenant_id="tenant-123",
        user_id="user-123",
    )


@patch("shared.authorization.get_membership")
def test_require_membership_rejects_non_member(
    mock_get_membership,
):
    mock_get_membership.return_value = None

    with pytest.raises(
        AuthorizationError,
        match="not a member of this tenant",
    ):
        require_membership(
            tenant_id="tenant-123",
            current_user=CURRENT_USER,
        )


@patch("shared.authorization.get_membership")
def test_require_membership_rejects_inactive_membership(
    mock_get_membership,
):
    mock_get_membership.return_value = {
        "role": "member",
        "status": "inactive",
    }

    with pytest.raises(
        AuthorizationError,
        match="membership is inactive",
    ):
        require_membership(
            tenant_id="tenant-123",
            current_user=CURRENT_USER,
        )


@patch("shared.authorization.get_membership")
@pytest.mark.parametrize("role", ["owner", "admin"])
def test_require_admin_allows_owner_and_admin(
    mock_get_membership,
    role,
):
    mock_get_membership.return_value = {
        "role": role,
        "status": "active",
    }

    membership = require_admin(
        tenant_id="tenant-123",
        current_user=CURRENT_USER,
    )

    assert membership["role"] == role


@patch("shared.authorization.get_membership")
def test_require_admin_rejects_member(
    mock_get_membership,
):
    mock_get_membership.return_value = {
        "role": "member",
        "status": "active",
    }

    with pytest.raises(
        AuthorizationError,
        match="Administrator privileges are required",
    ):
        require_admin(
            tenant_id="tenant-123",
            current_user=CURRENT_USER,
        )


@patch("shared.authorization.get_membership")
def test_require_owner_allows_owner(
    mock_get_membership,
):
    mock_get_membership.return_value = {
        "role": "owner",
        "status": "active",
    }

    membership = require_owner(
        tenant_id="tenant-123",
        current_user=CURRENT_USER,
    )

    assert membership["role"] == "owner"


@patch("shared.authorization.get_membership")
@pytest.mark.parametrize("role", ["admin", "member"])
def test_require_owner_rejects_non_owner(
    mock_get_membership,
    role,
):
    mock_get_membership.return_value = {
        "role": role,
        "status": "active",
    }

    with pytest.raises(
        AuthorizationError,
        match="Only the tenant owner",
    ):
        require_owner(
            tenant_id="tenant-123",
            current_user=CURRENT_USER,
        )