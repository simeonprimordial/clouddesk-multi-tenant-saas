"""
Add an existing CloudDesk user to a tenant.
"""

import json

from shared.auth import AuthenticationError, get_current_user
from shared.authorization import AuthorizationError, require_admin
from shared.db import create_tenant_membership, get_membership, get_user_by_email
from shared.observability import log_operation
from shared.response import error, success
from shared.serialization import serialize_dict

ALLOWED_ROLES = {
    "admin",
    "member",
}


def lambda_handler(event, context):
    """Add an existing CloudDesk user to a tenant."""

    try:
        current_user = get_current_user(event)

        log_operation(
            "Add tenant member request received.",
            event=event,
            context=context,
            outcome="started",
            current_user=current_user,
        )

        tenant_id = event.get("pathParameters", {}).get("tenantId")

        if not tenant_id:
            return error(
                message="Tenant ID is required.",
                status_code=400,
            )

        # Only tenant owners and admins may add members.
        require_admin(
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

        email = str(body.get("email", "")).strip().lower()
        role = str(body.get("role", "member")).strip().lower()

        if not email:
            return error(
                message="Email is required.",
                status_code=400,
            )

        if role not in ALLOWED_ROLES:
            return error(
                message="Role must be either admin or member.",
                status_code=400,
            )

        target_user = get_user_by_email(email)

        if target_user is None:
            return error(
                message="No active CloudDesk user was found with that email.",
                status_code=404,
            )

        existing_membership = get_membership(
            tenant_id=tenant_id,
            user_id=target_user["id"],
        )

        if existing_membership is not None:
            return error(
                message="The user already belongs to this tenant.",
                status_code=409,
            )

        membership = create_tenant_membership(
            tenant_id=tenant_id,
            user_id=target_user["id"],
            role=role,
        )

        response_data = {
            "user": serialize_dict(target_user),
            "membership": serialize_dict(membership),
        }

        log_operation(
            "Tenant member added.",
            event=event,
            context=context,
            outcome="success",
            current_user=current_user,
            status_code=201,
            extra={
                "tenant_id": tenant_id,
                "target_user_id": target_user["id"],
                "assigned_role": role,
            },
        )

        return success(
            message="Tenant member added successfully.",
            data=response_data,
            status_code=201,
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
            "Failed to add tenant member.",
            event=event,
            context=context,
            outcome="failure",
            current_user=None,
            status_code=500,
        )

        return error(
            message="Unable to add tenant member.",
            status_code=500,
        )
