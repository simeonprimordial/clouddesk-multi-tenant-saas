"""
Remove a member from a tenant by marking the membership inactive.
"""

from shared.auth import AuthenticationError, get_current_user
from shared.authorization import AuthorizationError, require_owner
from shared.db import deactivate_tenant_member, get_tenant_member
from shared.observability import log_operation
from shared.response import error, success
from shared.serialization import serialize_dict


def lambda_handler(event, context):
    """Soft delete a tenant member."""

    try:
        current_user = get_current_user(event)

        log_operation(
            "Remove tenant member request received.",
            event=event,
            context=context,
            outcome="started",
            current_user=current_user,
        )

        path_parameters = event.get("pathParameters", {})

        tenant_id = path_parameters.get("tenantId")
        user_id = path_parameters.get("userId")

        if not tenant_id or not user_id:
            return error(
                message="Tenant ID and User ID are required.",
                status_code=400,
            )

        require_owner(
            tenant_id=tenant_id,
            current_user=current_user,
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
                message="The tenant owner cannot be removed.",
                status_code=400,
            )

        if user_id == current_user["id"]:
            return error(
                message="You cannot remove yourself from the tenant.",
                status_code=400,
            )

        membership = deactivate_tenant_member(
            tenant_id=tenant_id,
            user_id=user_id,
        )

        log_operation(
            "Tenant member removed.",
            event=event,
            context=context,
            outcome="success",
            current_user=current_user,
            status_code=200,
            extra={
                "tenant_id": tenant_id,
                "target_user_id": user_id,
            },
        )

        return success(
            message="Tenant member removed successfully.",
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

        log_operation(
            "Failed to remove tenant member.",
            event=event,
            context=context,
            outcome="failure",
            current_user=None,
            status_code=500,
        )

        return error(
            message="Unable to remove tenant member.",
            status_code=500,
        )
