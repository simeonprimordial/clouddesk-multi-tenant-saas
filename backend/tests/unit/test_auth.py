"""Tests for CloudDesk authentication helpers."""

from unittest.mock import patch

import pytest
from shared.auth import (
    AuthenticationError,
    get_authenticated_identity,
    get_current_user,
    get_jwt_claims,
)
from shared.authorization import AuthorizationError


def create_authenticated_event():
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "cognito-user-123",
                        "username": "user@example.com",
                        "client_id": "client-123",
                    }
                }
            }
        }
    }


def test_get_jwt_claims_returns_verified_claims():
    event = create_authenticated_event()

    claims = get_jwt_claims(event)

    assert claims["sub"] == "cognito-user-123"
    assert claims["username"] == "user@example.com"
    assert claims["client_id"] == "client-123"


def test_get_jwt_claims_rejects_missing_authorizer():
    with pytest.raises(
        AuthenticationError,
        match="Authenticated JWT claims were not found",
    ):
        get_jwt_claims({})


def test_get_jwt_claims_rejects_invalid_claim_format():
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": "not-a-dictionary",
                }
            }
        }
    }

    with pytest.raises(
        AuthenticationError,
        match="JWT claims have an invalid format",
    ):
        get_jwt_claims(event)


def test_get_authenticated_identity_returns_expected_values():
    identity = get_authenticated_identity(create_authenticated_event())

    assert identity == {
        "cognito_sub": "cognito-user-123",
        "username": "user@example.com",
        "client_id": "client-123",
    }


def test_get_authenticated_identity_requires_sub():
    event = create_authenticated_event()

    del event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]

    with pytest.raises(
        AuthenticationError,
        match="does not contain a user identifier",
    ):
        get_authenticated_identity(event)


@patch("shared.auth.get_user_by_cognito_sub")
def test_get_current_user_returns_active_user(
    mock_get_user_by_cognito_sub,
):
    mock_get_user_by_cognito_sub.return_value = {
        "id": "user-123",
        "cognito_user_id": "cognito-user-123",
        "email": "user@example.com",
        "status": "active",
    }

    user = get_current_user(create_authenticated_event())

    assert user["id"] == "user-123"
    assert user["status"] == "active"

    mock_get_user_by_cognito_sub.assert_called_once_with("cognito-user-123")


@patch("shared.auth.get_user_by_cognito_sub")
def test_get_current_user_rejects_unprovisioned_user(
    mock_get_user_by_cognito_sub,
):
    mock_get_user_by_cognito_sub.return_value = None

    with pytest.raises(
        AuthorizationError,
        match="not provisioned in CloudDesk",
    ):
        get_current_user(create_authenticated_event())


@patch("shared.auth.get_user_by_cognito_sub")
def test_get_current_user_rejects_inactive_user(
    mock_get_user_by_cognito_sub,
):
    mock_get_user_by_cognito_sub.return_value = {
        "id": "user-123",
        "status": "inactive",
    }

    with pytest.raises(
        AuthorizationError,
        match="CloudDesk user is inactive",
    ):
        get_current_user(create_authenticated_event())
