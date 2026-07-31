"""
Return a single tenant belonging to the authenticated user.
"""

from shared.auth import (
    AuthenticationError,
    get_current_user,
)
from shared.authorization import (
    AuthorizationError,
    require_membership,
)
from shared.db import get_tenant_by_id
from shared.response import error, success
from shared.serialization import serialize_dict


def lambda_handler(event, context):
    """Return a tenant by ID."""

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

        tenant = get_tenant_by_id(tenant_id)

        if tenant is None:
            return error(
                message="Tenant not found.",
                status_code=404,
            )

        return success(
            message="Tenant retrieved successfully.",
            data=serialize_dict(tenant),
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
            message="Unable to retrieve tenant.",
            status_code=500,
        )
