import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

secrets_client = boto3.client("secretsmanager")


def get_database_secret() -> dict[str, Any]:
    """Retrieve and validate the CloudDesk database secret."""

    secret_arn = os.getenv("DATABASE_SECRET_ARN")

    if not secret_arn:
        raise RuntimeError("DATABASE_SECRET_ARN is not configured")

    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
    except (ClientError, BotoCoreError) as error:
        logger.exception("Unable to retrieve database secret")
        raise RuntimeError("Database secret retrieval failed") from error

    secret_string = response.get("SecretString")

    if not secret_string:
        raise RuntimeError("Database secret does not contain SecretString")

    try:
        secret = json.loads(secret_string)
    except json.JSONDecodeError as error:
        raise RuntimeError("Database secret is not valid JSON") from error

    required_fields = {
        "host",
        "port",
        "dbname",
        "username",
        "password",
    }

    missing_fields = required_fields.difference(secret)

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise RuntimeError(f"Database secret is missing fields: {missing}")

    return secret


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Verify that Lambda can securely retrieve the database secret."""

    try:
        secret = get_database_secret()

        logger.info(
            "Database secret retrieved successfully",
            extra={
                "database": secret["dbname"],
                "host_configured": bool(secret["host"]),
                "request_id": getattr(context, "aws_request_id", None),
            },
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": True,
                    "message": "Database secret retrieved successfully",
                    "data": {
                        "database": secret["dbname"],
                        "engine": secret.get("engine", "postgres"),
                        "port": secret["port"],
                    },
                }
            ),
        }

    except RuntimeError as error:
        logger.exception("Database secret validation failed")

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
        }