import json
from typing import Any


def success(
    message: str,
    data: Any = None,
    status_code: int = 200,
) -> dict[str, Any]:
    """Return a successful API response."""

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
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
) -> dict[str, Any]:
    """Return an error API response."""

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(
            {
                "success": False,
                "message": message,
            }
        ),
    }