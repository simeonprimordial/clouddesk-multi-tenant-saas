"""
Authorization helpers for CloudDesk.
"""

from .db import get_membership


class AuthorizationError(Exception):
    """Raised when a user is not authorized."""


def require_membership(
    *,
    tenant_id,
    current_user,
):
    """
    Ensure the authenticated user belongs to the supplied tenant.
    """

    membership = get_membership(
        tenant_id=tenant_id,
        user_id=current_user["id"],
    )

    if membership is None:
        raise AuthorizationError("You are not a member of this tenant.")

    if membership["status"] != "active":
        raise AuthorizationError("Your tenant membership is inactive.")

    return membership


def require_admin(
    *,
    tenant_id,
    current_user,
):
    """
    Ensure the authenticated user is an administrator
    of the supplied tenant.
    """

    membership = require_membership(
        tenant_id=tenant_id,
        current_user=current_user,
    )

    if membership["role"] not in ("owner", "admin"):
        raise AuthorizationError("Administrator privileges are required.")

    return membership


def require_owner(
    *,
    tenant_id,
    current_user,
):
    """
    Ensure the authenticated user owns the supplied tenant.
    """

    membership = require_membership(
        tenant_id=tenant_id,
        current_user=current_user,
    )

    if membership["role"] != "owner":
        raise AuthorizationError("Only the tenant owner can perform this action.")

    return membership
