"""
Return the authenticated CloudDesk user's profile.
"""

from shared.auth import (
    AuthenticationError,
    AuthorizationError,
    get_current_user,
)
from shared.response import error, success
from shared.serialization import serialize_dict


def lambda_handler(event, context):
    """Return the authenticated CloudDesk user's profile."""

    try:
        user = get_current_user(event)

        user_profile = serialize_dict(user)

        return success(
            message="Authenticated user retrieved successfully.",
            data=user_profile,
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
            message="Unable to retrieve the authenticated user.",
            status_code=500,
        )
