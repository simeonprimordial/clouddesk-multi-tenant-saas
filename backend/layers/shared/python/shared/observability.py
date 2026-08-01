"""
Structured observability helpers for CloudDesk Lambda functions.
"""

import logging
from typing import Any

logger = logging.getLogger("clouddesk")


def get_request_context(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """
    Extract non-sensitive operational context from a Lambda invocation.
    """

    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}
    path_parameters = event.get("pathParameters") or {}

    return {
        "aws_request_id": getattr(context, "aws_request_id", None),
        "function_name": getattr(context, "function_name", None),
        "api_request_id": request_context.get("requestId"),
        "route_key": request_context.get("routeKey"),
        "http_method": http_context.get("method"),
        "path": http_context.get("path"),
        "tenant_id": path_parameters.get("tenantId"),
        "target_user_id": path_parameters.get("userId"),
    }


def log_operation(
    message: str,
    *,
    event: dict[str, Any],
    context: Any,
    outcome: str,
    current_user: dict[str, Any] | None = None,
    status_code: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Write a structured application log without exposing sensitive values.
    """

    log_context = get_request_context(event, context)

    log_context.update(
        {
            "outcome": outcome,
            "status_code": status_code,
            "current_user_id": (current_user.get("id") if current_user else None),
        }
    )

    if extra:
        log_context.update(extra)

    logger.info(
        message,
        extra=log_context,
    )
