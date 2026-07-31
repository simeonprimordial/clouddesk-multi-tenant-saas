"""
Central application configuration.

Every Lambda imports configuration from this module instead
of reading environment variables directly.
"""

import os


class Config:
    """Application configuration."""

    APP_NAME = "CloudDesk"

    ENVIRONMENT = os.getenv("APP_ENV", "dev")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    DATABASE_SECRET_ARN = os.getenv("DATABASE_SECRET_ARN")

    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

    # Cognito Configuration
    COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")

    COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")

    COGNITO_ISSUER = (
        f"https://cognito-idp.{AWS_REGION}.amazonaws.com/" f"{COGNITO_USER_POOL_ID}"
        if COGNITO_USER_POOL_ID
        else None
    )


config = Config()
