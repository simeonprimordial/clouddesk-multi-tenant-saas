"""
Authentication helpers for CloudDesk Lambda functions.

API Gateway validates Cognito JWTs before invoking protected
Lambda functions. This module reads trusted JWT claims from the
API Gateway event and resolves the corresponding CloudDesk user.
"""

from typing import Any

from .authorization import AuthorizationError
from .db import get_user_by_cognito_sub


class AuthenticationError(Exception):
    """Raised when authenticated user information is unavailable."""


def get_jwt_claims(event: dict[str, Any]) -> dict[str, Any]:
    """
    Extract verified JWT claims from an API Gateway HTTP API event.

    Expected event path:
    requestContext.authorizer.jwt.claims
    """

    try:
        claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    except (KeyError, TypeError) as error:
        raise AuthenticationError(
            "Authenticated JWT claims were not found in the request."
        ) from error

    if not isinstance(claims, dict):
        raise AuthenticationError("JWT claims have an invalid format.")

    return claims


def get_authenticated_identity(event: dict[str, Any]) -> dict[str, str]:
    """
    Return the authenticated Cognito user's essential identity.

    The access token should provide:
    - sub: Cognito user's permanent unique identifier
    - username: Cognito username
    - client_id: Cognito app client that received the token
    """

    claims = get_jwt_claims(event)

    cognito_sub = claims.get("sub")
    username = claims.get("username")
    client_id = claims.get("client_id")

    if not cognito_sub:
        raise AuthenticationError(
            "The authenticated token does not contain a user identifier."
        )

    return {
        "cognito_sub": str(cognito_sub),
        "username": str(username or ""),
        "client_id": str(client_id or ""),
    }


def get_current_user(event: dict[str, Any]) -> dict[str, Any]:
    """
    Resolve the authenticated Cognito identity to a CloudDesk user.

    API Gateway has already validated the JWT. This function uses the
    verified Cognito sub to locate the corresponding application user.
    """

    identity = get_authenticated_identity(event)
    cognito_sub = identity["cognito_sub"]

    user = get_user_by_cognito_sub(cognito_sub)

    if user is None:
        raise AuthorizationError(
            "The authenticated user is not provisioned in CloudDesk."
        )

    if user["status"] != "active":
        raise AuthorizationError("The authenticated CloudDesk user is inactive.")

    return user
