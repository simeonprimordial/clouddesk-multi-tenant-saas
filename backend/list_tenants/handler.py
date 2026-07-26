"""
Return the active tenants available to the authenticated user.
"""

from shared.auth import (
    AuthenticationError,
    AuthorizationError,
    get_current_user,
)
from shared.db import get_tenants_for_user
from shared.response import error, success
from shared.serialization import serialize_list


def lambda_handler(event, context):
    """Return tenants belonging to the authenticated CloudDesk user."""

    try:
        current_user = get_current_user(event)

        tenants = get_tenants_for_user(current_user["id"])

        return success(
            message="Tenants retrieved successfully.",
            data=serialize_list(tenants),
        )

    except AuthenticationError as auth_error:
        return error(
            message=str(auth_error),
            status_code=401,
        )

    except AuthorizationError as authorization_error:
        return error(
            message=str(authorization_error),
            status_code=403,
        )

    except Exception:
        return error(
            message="Unable to retrieve tenants.",
            status_code=500,
        )