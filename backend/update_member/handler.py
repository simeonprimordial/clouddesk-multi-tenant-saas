"""
Update a tenant member's role.
"""

import json

from shared.auth import (
    AuthenticationError,
    get_current_user,
)
from shared.authorization import (
    AuthorizationError,
    require_owner,
)
from shared.db import (
    get_tenant_member,
    update_tenant_member_role,
)
from shared.response import error, success
from shared.serialization import serialize_dict


ALLOWED_ROLES = {
    "admin",
    "member",
}


def lambda_handler(event, context):
    """Update a tenant member's role."""

    try:
        current_user = get_current_user(event)

        path_parameters = event.get("pathParameters", {})

        tenant_id = path_parameters.get("tenantId")
        user_id = path_parameters.get("userId")

        if not tenant_id or not user_id:
            return error(
                message="Tenant ID and User ID are required.",
                status_code=400,
            )

        # Only the tenant owner can update roles.
        require_owner(
            tenant_id=tenant_id,
            current_user=current_user,
        )

        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return error(
                message="Request body must contain valid JSON.",
                status_code=400,
            )

        role = str(body.get("role", "")).strip().lower()

        if role not in ALLOWED_ROLES:
            return error(
                message="Role must be either admin or member.",
                status_code=400,
            )

        target_member = get_tenant_member(
            tenant_id=tenant_id,
            user_id=user_id,
        )

        if target_member is None:
            return error(
                message="Tenant member not found.",
                status_code=404,
            )

        if target_member["role"] == "owner":
            return error(
                message="The tenant owner's role cannot be changed.",
                status_code=400,
            )

        membership = update_tenant_member_role(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )

        return success(
            message="Tenant member updated successfully.",
            data=serialize_dict(membership),
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
            message="Unable to update tenant member.",
            status_code=500,
        )