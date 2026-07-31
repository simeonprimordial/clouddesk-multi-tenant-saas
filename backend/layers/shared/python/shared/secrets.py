"""
Secure retrieval and validation of CloudDesk database credentials.
"""

import json
import logging
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .config import config

logger = logging.getLogger(__name__)

secrets_client = boto3.client(
    "secretsmanager",
    region_name=config.AWS_REGION,
)

REQUIRED_DATABASE_FIELDS = {
    "host",
    "port",
    "dbname",
    "username",
    "password",
}


class SecretConfigurationError(RuntimeError):
    """Raised when the database secret is missing or incorrectly configured."""


@lru_cache(maxsize=1)
def get_database_secret() -> dict[str, Any]:
    """
    Retrieve and cache the CloudDesk PostgreSQL secret.

    The secret is retrieved once per warm Lambda execution environment.
    """

    if not config.DATABASE_SECRET_ARN:
        raise SecretConfigurationError(
            "DATABASE_SECRET_ARN environment variable is not configured"
        )

    try:
        response = secrets_client.get_secret_value(SecretId=config.DATABASE_SECRET_ARN)
    except (ClientError, BotoCoreError) as error:
        logger.exception("Failed to retrieve the database secret")
        raise SecretConfigurationError(
            "Unable to retrieve database credentials"
        ) from error

    secret_string = response.get("SecretString")

    if not secret_string:
        raise SecretConfigurationError(
            "Database secret does not contain a SecretString value"
        )

    try:
        secret = json.loads(secret_string)
    except json.JSONDecodeError as error:
        raise SecretConfigurationError(
            "Database secret contains invalid JSON"
        ) from error

    missing_fields = REQUIRED_DATABASE_FIELDS.difference(secret.keys())

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise SecretConfigurationError(
            f"Database secret is missing required fields: {missing}"
        )

    try:
        secret["port"] = int(secret["port"])
    except (TypeError, ValueError) as error:
        raise SecretConfigurationError(
            "Database secret port must be a valid integer"
        ) from error

    logger.info(
        "Database secret retrieved and validated",
        extra={
            "database": secret["dbname"],
            "engine": secret.get("engine", "postgres"),
        },
    )

    return secret
