"""
CloudDesk database connectivity test Lambda.

This function verifies that Lambda can:

1. Retrieve PostgreSQL credentials from AWS Secrets Manager.
2. Connect to the private Amazon RDS PostgreSQL instance.
3. Execute a simple SQL query.
"""

import logging
from typing import Any

from shared.db import DatabaseConnectionError, get_connection
from shared.response import error, success
from shared.secrets import SecretConfigurationError

logger = logging.getLogger(__name__)


def lambda_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """Test the CloudDesk PostgreSQL database connection."""

    request_id = getattr(context, "aws_request_id", None)

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_database() AS database_name,
                    current_user AS database_user,
                    version() AS postgres_version,
                    NOW() AS database_time;
                """
            )

            result = cursor.fetchone()

        logger.info(
            "Database connectivity test succeeded",
            extra={
                "request_id": request_id,
                "database": result["database_name"],
            },
        )

        return success(
            message="Database connection established successfully",
            data={
                "database": result["database_name"],
                "database_time": result["database_time"].isoformat(),
            },
        )

    except SecretConfigurationError:
        logger.exception(
            "Database secret configuration error",
            extra={"request_id": request_id},
        )

        return error(
            message="Database credentials could not be retrieved",
            status_code=500,
        )

    except DatabaseConnectionError:
        logger.exception(
            "Database connection failed",
            extra={"request_id": request_id},
        )

        return error(
            message="Unable to connect to the database",
            status_code=500,
        )

    except Exception:
        logger.exception(
            "Unexpected database test error",
            extra={"request_id": request_id},
        )

        return error(
            message="An unexpected database error occurred",
            status_code=500,
        )