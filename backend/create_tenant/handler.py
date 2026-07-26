"""
Create a new CloudDesk tenant for the authenticated user.
"""

import json
import re
from shared.serialization import serialize_dict
from typing import Any


from shared.auth import (
    AuthenticationError,
    AuthorizationError,
    get_current_user,
)
from shared.db import (
    create_tenant_with_owner,
    get_tenant_by_slug,
)
from shared.response import error, success




def create_slug(name: str) -> str:
    """Convert a tenant name into a URL-safe slug."""

    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def lambda_handler(event, context):
    """Create a tenant and assign the current user as owner."""

    try:
        current_user = get_current_user(event)

        body = json.loads(event.get("body") or "{}")
        name = str(body.get("name") or "").strip()

        if not name:
            return error(
                message="Tenant name is required.",
                status_code=400,
            )

        if len(name) > 150:
            return error(
                message="Tenant name must not exceed 150 characters.",
                status_code=400,
            )

        slug = create_slug(name)

        if not slug:
            return error(
                message="Tenant name must contain letters or numbers.",
                status_code=400,
            )

        if len(slug) > 100:
            return error(
                message="Generated tenant slug exceeds 100 characters.",
                status_code=400,
            )

        existing_tenant = get_tenant_by_slug(slug)

        if existing_tenant is not None:
            return error(
                message="A tenant with this name already exists.",
                status_code=409,
            )

        tenant = create_tenant_with_owner(
            name=name,
            slug=slug,
            owner_user_id=current_user["id"],
        )

        serialized_tenant = serialize_dict(tenant)

        return success(
            message="Tenant created successfully.",
            data=serialized_tenant,
            status_code=201,
        )

    except json.JSONDecodeError:
        return error(
            message="Request body must contain valid JSON.",
            status_code=400,
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
            message="Unable to create tenant.",
            status_code=500,
        )