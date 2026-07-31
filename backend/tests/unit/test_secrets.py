"""Tests for CloudDesk Secrets Manager helpers."""

import json
from unittest.mock import patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError
from shared.secrets import (
    SecretConfigurationError,
    get_database_secret,
)

VALID_SECRET = {
    "host": "clouddesk-db.example.us-east-1.rds.amazonaws.com",
    "port": "5432",
    "dbname": "clouddesk",
    "username": "postgres",
    "password": "example-password",
}


@pytest.fixture(autouse=True)
def clear_secret_cache():
    """Prevent cached secrets from leaking between tests."""

    get_database_secret.cache_clear()
    yield
    get_database_secret.cache_clear()


@patch("shared.secrets.config")
def test_get_database_secret_requires_secret_arn(mock_config):
    mock_config.DATABASE_SECRET_ARN = None

    with pytest.raises(
        SecretConfigurationError,
        match="DATABASE_SECRET_ARN environment variable is not configured",
    ):
        get_database_secret()


@patch("shared.secrets.secrets_client")
@patch("shared.secrets.config")
def test_get_database_secret_returns_validated_secret(
    mock_config,
    mock_secrets_client,
):
    mock_config.DATABASE_SECRET_ARN = "secret-arn"

    mock_secrets_client.get_secret_value.return_value = {
        "SecretString": json.dumps(VALID_SECRET)
    }

    secret = get_database_secret()

    assert secret["host"] == VALID_SECRET["host"]
    assert secret["dbname"] == "clouddesk"
    assert secret["port"] == 5432

    mock_secrets_client.get_secret_value.assert_called_once_with(SecretId="secret-arn")


@patch("shared.secrets.secrets_client")
@patch("shared.secrets.config")
def test_get_database_secret_is_cached(
    mock_config,
    mock_secrets_client,
):
    mock_config.DATABASE_SECRET_ARN = "secret-arn"

    mock_secrets_client.get_secret_value.return_value = {
        "SecretString": json.dumps(VALID_SECRET)
    }

    first_result = get_database_secret()
    second_result = get_database_secret()

    assert first_result == second_result
    assert mock_secrets_client.get_secret_value.call_count == 1


@patch("shared.secrets.secrets_client")
@patch("shared.secrets.config")
def test_get_database_secret_rejects_missing_secret_string(
    mock_config,
    mock_secrets_client,
):
    mock_config.DATABASE_SECRET_ARN = "secret-arn"
    mock_secrets_client.get_secret_value.return_value = {}

    with pytest.raises(
        SecretConfigurationError,
        match="does not contain a SecretString value",
    ):
        get_database_secret()


@patch("shared.secrets.secrets_client")
@patch("shared.secrets.config")
def test_get_database_secret_rejects_invalid_json(
    mock_config,
    mock_secrets_client,
):
    mock_config.DATABASE_SECRET_ARN = "secret-arn"

    mock_secrets_client.get_secret_value.return_value = {
        "SecretString": "{invalid-json"
    }

    with pytest.raises(
        SecretConfigurationError,
        match="contains invalid JSON",
    ):
        get_database_secret()


@patch("shared.secrets.secrets_client")
@patch("shared.secrets.config")
def test_get_database_secret_rejects_missing_fields(
    mock_config,
    mock_secrets_client,
):
    mock_config.DATABASE_SECRET_ARN = "secret-arn"

    incomplete_secret = {
        "host": "database.example.com",
        "port": 5432,
    }

    mock_secrets_client.get_secret_value.return_value = {
        "SecretString": json.dumps(incomplete_secret)
    }

    with pytest.raises(
        SecretConfigurationError,
        match="missing required fields",
    ):
        get_database_secret()


@patch("shared.secrets.secrets_client")
@patch("shared.secrets.config")
def test_get_database_secret_rejects_invalid_port(
    mock_config,
    mock_secrets_client,
):
    mock_config.DATABASE_SECRET_ARN = "secret-arn"

    invalid_secret = {
        **VALID_SECRET,
        "port": "not-a-number",
    }

    mock_secrets_client.get_secret_value.return_value = {
        "SecretString": json.dumps(invalid_secret)
    }

    with pytest.raises(
        SecretConfigurationError,
        match="port must be a valid integer",
    ):
        get_database_secret()


@patch("shared.secrets.secrets_client")
@patch("shared.secrets.config")
def test_get_database_secret_handles_client_error(
    mock_config,
    mock_secrets_client,
):
    mock_config.DATABASE_SECRET_ARN = "secret-arn"

    mock_secrets_client.get_secret_value.side_effect = ClientError(
        {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "Access denied",
            }
        },
        "GetSecretValue",
    )

    with pytest.raises(
        SecretConfigurationError,
        match="Unable to retrieve database credentials",
    ):
        get_database_secret()


@patch("shared.secrets.secrets_client")
@patch("shared.secrets.config")
def test_get_database_secret_handles_boto_core_error(
    mock_config,
    mock_secrets_client,
):
    mock_config.DATABASE_SECRET_ARN = "secret-arn"

    mock_secrets_client.get_secret_value.side_effect = BotoCoreError()

    with pytest.raises(
        SecretConfigurationError,
        match="Unable to retrieve database credentials",
    ):
        get_database_secret()
