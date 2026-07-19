import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def build_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Create a valid API Gateway HTTP API response."""

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Return the operational status of the CloudDesk API."""

    environment = os.getenv("APP_ENV", "unknown")

    logger.info(
        "Health check completed",
        extra={
            "environment": environment,
            "request_id": getattr(context, "aws_request_id", None),
        },
    )

    return build_response(
        200,
        {
            "success": True,
            "message": "CloudDesk API is healthy",
            "data": {
                "service": "clouddesk-backend",
                "environment": environment,
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )