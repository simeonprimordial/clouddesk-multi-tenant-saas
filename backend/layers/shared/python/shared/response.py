"""
Consistent HTTP responses for CloudDesk API handlers.
"""

import json
from typing import Any

DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


def success(
    message: str,
    data: Any = None,
    status_code: int = 200,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return a successful API response."""

    headers = DEFAULT_HEADERS.copy()

    if request_id:
        headers["X-Request-Id"] = request_id

    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(
            {
                "success": True,
                "message": message,
                "data": data,
            }
        ),
    }


def error(
    message: str,
    status_code: int = 500,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return an error API response."""

    headers = DEFAULT_HEADERS.copy()

    if request_id:
        headers["X-Request-Id"] = request_id

    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(
            {
                "success": False,
                "message": message,
            }
        ),
    }
