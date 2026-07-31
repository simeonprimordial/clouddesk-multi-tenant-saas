"""
Provision confirmed Cognito users in the CloudDesk database.
"""

import logging
from typing import Any

from shared.db import create_user, get_user_by_cognito_sub

logger = logging.getLogger(__name__)


class UserProvisioningError(RuntimeError):
    """Raised when a confirmed Cognito user cannot be provisioned."""


def lambda_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """
    Create a CloudDesk user after Cognito confirms the account.

    Cognito requires the original event to be returned.
    """

    user_attributes = event.get("request", {}).get("userAttributes", {})

    cognito_sub = user_attributes.get("sub")
    email = user_attributes.get("email")
    first_name = user_attributes.get("given_name")
    last_name = user_attributes.get("family_name")

    missing_attributes = [
        attribute_name
        for attribute_name, attribute_value in {
            "sub": cognito_sub,
            "email": email,
            "given_name": first_name,
            "family_name": last_name,
        }.items()
        if not attribute_value
    ]

    if missing_attributes:
        raise UserProvisioningError(
            "Cannot provision user because required Cognito attributes "
            f"are missing: {', '.join(missing_attributes)}"
        )

    existing_user = get_user_by_cognito_sub(cognito_sub)

    if existing_user is not None:
        logger.info(
            "CloudDesk user already exists",
            extra={"cognito_sub": cognito_sub},
        )
        return event

    user = create_user(
        cognito_sub=cognito_sub,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )

    logger.info(
        "CloudDesk user provisioned successfully",
        extra={
            "user_id": str(user["id"]),
            "cognito_sub": cognito_sub,
        },
    )

    return event
