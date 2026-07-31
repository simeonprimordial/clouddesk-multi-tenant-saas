"""
Return all members belonging to a tenant.
"""

from shared.auth import (
    AuthenticationError,
    get_current_user,
)
from shared.authorization import (
    AuthorizationError,
    require_membership,
)
from shared.db import get_tenant_members
from shared.response import error, success
from shared.serialization import serialize_list


def lambda_handler(event, context):
    """Return all active members of a tenant."""

    try:
        current_user = get_current_user(event)

        tenant_id = event.get("pathParameters", {}).get("tenantId")

        if not tenant_id:
            return error(
                message="Tenant ID is required.",
                status_code=400,
            )

        require_membership(
            tenant_id=tenant_id,
            current_user=current_user,
        )

        members = get_tenant_members(tenant_id)

        return success(
            message="Tenant members retrieved successfully.",
            data=serialize_list(members),
        )

    except AuthenticationError as authentication_error:
        return error(
            message=str(authentication_error),
            status_code=401,
        )

    except AuthorizationError as authorization_error:
        return error(
            message=str(authorization_error),
            status_code=403,
        )

    except Exception:
        return error(
            message="Unable to retrieve tenant members.",
            status_code=500,
        )
