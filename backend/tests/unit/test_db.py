"""Tests for CloudDesk PostgreSQL helpers."""

from unittest.mock import MagicMock, patch

import psycopg
import pytest

import shared.db as db
from shared.db import (
    DatabaseConnectionError,
    close_connection,
    create_tenant_membership,
    create_tenant_with_owner,
    create_user,
    database_transaction,
    deactivate_tenant_member,
    get_connection,
    get_membership,
    get_tenant_by_id,
    get_tenant_by_slug,
    get_tenant_member,
    get_tenant_members,
    get_tenants_for_user,
    get_user_by_cognito_sub,
    get_user_by_email,
    update_tenant_member_role,
)


DATABASE_SECRET = {
    "host": "database.example.com",
    "port": 5432,
    "dbname": "clouddesk",
    "username": "postgres",
    "password": "example-password",
}


@pytest.fixture(autouse=True)
def reset_cached_connection():
    """Reset the module-level cached connection between tests."""

    db._connection = None
    yield
    db._connection = None


def create_mock_connection(
    *,
    fetchone=None,
    fetchall=None,
):
    """Create a connection and cursor mock supporting context managers."""

    connection = MagicMock()
    connection.closed = False

    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall or []

    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cursor
    cursor_context.__exit__.return_value = False

    connection.cursor.return_value = cursor_context

    return connection, cursor


@patch("shared.db.psycopg.connect")
@patch("shared.db.get_database_secret")
def test_get_connection_creates_new_connection(
    mock_get_database_secret,
    mock_connect,
):
    mock_get_database_secret.return_value = DATABASE_SECRET

    connection = MagicMock()
    connection.closed = False
    mock_connect.return_value = connection

    result = get_connection()

    assert result is connection

    mock_connect.assert_called_once_with(
        host="database.example.com",
        port=5432,
        dbname="clouddesk",
        user="postgres",
        password="example-password",
        connect_timeout=5,
        row_factory=db.dict_row,
        application_name="clouddesk-lambda",
    )


@patch("shared.db.psycopg.connect")
def test_get_connection_reuses_cached_connection(mock_connect):
    cached_connection = MagicMock()
    cached_connection.closed = False

    db._connection = cached_connection

    result = get_connection()

    assert result is cached_connection
    mock_connect.assert_not_called()


@patch("shared.db.psycopg.connect")
@patch("shared.db.get_database_secret")
def test_get_connection_replaces_closed_connection(
    mock_get_database_secret,
    mock_connect,
):
    old_connection = MagicMock()
    old_connection.closed = True
    db._connection = old_connection

    new_connection = MagicMock()
    new_connection.closed = False

    mock_get_database_secret.return_value = DATABASE_SECRET
    mock_connect.return_value = new_connection

    result = get_connection()

    assert result is new_connection
    mock_connect.assert_called_once()


@patch("shared.db.psycopg.connect")
@patch("shared.db.get_database_secret")
def test_get_connection_wraps_psycopg_error(
    mock_get_database_secret,
    mock_connect,
):
    mock_get_database_secret.return_value = DATABASE_SECRET
    mock_connect.side_effect = psycopg.Error("connection failed")

    with pytest.raises(
        DatabaseConnectionError,
        match="Unable to establish a database connection",
    ):
        get_connection()


@patch("shared.db.get_connection")
def test_database_transaction_commits_on_success(
    mock_get_connection,
):
    connection = MagicMock()
    mock_get_connection.return_value = connection

    with database_transaction() as result:
        assert result is connection

    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()


@patch("shared.db.get_connection")
def test_database_transaction_rolls_back_on_failure(
    mock_get_connection,
):
    connection = MagicMock()
    mock_get_connection.return_value = connection

    with pytest.raises(RuntimeError, match="test failure"):
        with database_transaction():
            raise RuntimeError("test failure")

    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()


def test_close_connection_closes_cached_connection():
    connection = MagicMock()
    connection.closed = False
    db._connection = connection

    close_connection()

    connection.close.assert_called_once()
    assert db._connection is None


def test_close_connection_ignores_already_closed_connection():
    connection = MagicMock()
    connection.closed = True
    db._connection = connection

    close_connection()

    connection.close.assert_not_called()
    assert db._connection is None


@patch("shared.db.database_transaction")
def test_get_user_by_cognito_sub_returns_user(
    mock_database_transaction,
):
    user = {
        "id": "user-123",
        "cognito_user_id": "cognito-123",
    }

    connection, cursor = create_mock_connection(fetchone=user)

    transaction_context = MagicMock()
    transaction_context.__enter__.return_value = connection
    transaction_context.__exit__.return_value = False

    mock_database_transaction.return_value = transaction_context

    result = get_user_by_cognito_sub("cognito-123")

    assert result == user
    cursor.execute.assert_called_once()

    query_arguments = cursor.execute.call_args.args[1]
    assert query_arguments == ("cognito-123",)


@patch("shared.db.database_transaction")
def test_create_user_normalizes_input(
    mock_database_transaction,
):
    created_user = {
        "id": "user-123",
        "email": "member@example.com",
    }

    connection, cursor = create_mock_connection(
        fetchone=created_user
    )

    transaction_context = MagicMock()
    transaction_context.__enter__.return_value = connection
    transaction_context.__exit__.return_value = False

    mock_database_transaction.return_value = transaction_context

    result = create_user(
        cognito_sub="cognito-123",
        email=" MEMBER@EXAMPLE.COM ",
        first_name=" Cloud ",
        last_name=" Member ",
    )

    assert result == created_user

    query_arguments = cursor.execute.call_args.args[1]

    assert query_arguments == (
        "cognito-123",
        "member@example.com",
        "Cloud",
        "Member",
    )


@patch("shared.db.database_transaction")
def test_create_user_rejects_missing_returned_row(
    mock_database_transaction,
):
    connection, _ = create_mock_connection(fetchone=None)

    transaction_context = MagicMock()
    transaction_context.__enter__.return_value = connection
    transaction_context.__exit__.return_value = False

    mock_database_transaction.return_value = transaction_context

    with pytest.raises(
        RuntimeError,
        match="no database record was returned",
    ):
        create_user(
            cognito_sub="cognito-123",
            email="member@example.com",
            first_name="Cloud",
            last_name="Member",
        )


@patch("shared.db.get_connection")
def test_get_tenant_by_slug_returns_tenant(
    mock_get_connection,
):
    tenant = {
        "id": "tenant-123",
        "slug": "novatech",
    }

    connection, cursor = create_mock_connection(fetchone=tenant)
    mock_get_connection.return_value = connection

    result = get_tenant_by_slug("novatech")

    assert result == tenant
    assert cursor.execute.call_args.args[1] == ("novatech",)


@patch("shared.db.get_connection")
def test_create_tenant_with_owner_commits_transaction(
    mock_get_connection,
):
    connection, cursor = create_mock_connection(
        fetchone={
            "id": "tenant-123",
            "name": "NovaTech",
            "slug": "novatech",
        }
    )

    mock_get_connection.return_value = connection

    tenant = create_tenant_with_owner(
        name="NovaTech",
        slug="novatech",
        owner_user_id="owner-123",
    )

    assert tenant["id"] == "tenant-123"
    assert cursor.execute.call_count == 2
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()


@patch("shared.db.get_connection")
def test_create_tenant_with_owner_rolls_back_on_failure(
    mock_get_connection,
):
    connection, cursor = create_mock_connection()

    cursor.execute.side_effect = RuntimeError(
        "membership insert failed"
    )

    mock_get_connection.return_value = connection

    with pytest.raises(
        RuntimeError,
        match="membership insert failed",
    ):
        create_tenant_with_owner(
            name="NovaTech",
            slug="novatech",
            owner_user_id="owner-123",
        )

    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()


@pytest.mark.parametrize(
    ("function", "arguments", "expected_parameters"),
    [
        (
            get_tenants_for_user,
            ("user-123",),
            ("user-123",),
        ),
        (
            get_tenant_by_id,
            ("tenant-123",),
            ("tenant-123",),
        ),
        (
            get_tenant_members,
            ("tenant-123",),
            ("tenant-123",),
        ),
        (
            get_user_by_email,
            ("member@example.com",),
            ("member@example.com",),
        ),
    ],
)
@patch("shared.db.get_connection")
def test_single_parameter_query_helpers(
    mock_get_connection,
    function,
    arguments,
    expected_parameters,
):
    connection, cursor = create_mock_connection(
        fetchone={"id": "result-123"},
        fetchall=[{"id": "result-123"}],
    )

    mock_get_connection.return_value = connection

    function(*arguments)

    assert cursor.execute.call_args.args[1] == expected_parameters


@pytest.mark.parametrize(
    "function",
    [
        get_membership,
        get_tenant_member,
    ],
)
@patch("shared.db.get_connection")
def test_membership_query_helpers(
    mock_get_connection,
    function,
):
    connection, cursor = create_mock_connection(
        fetchone={
            "tenant_id": "tenant-123",
            "user_id": "user-123",
        }
    )

    mock_get_connection.return_value = connection

    result = function(
        tenant_id="tenant-123",
        user_id="user-123",
    )

    assert result["tenant_id"] == "tenant-123"

    assert cursor.execute.call_args.args[1] == (
        "tenant-123",
        "user-123",
    )


@patch("shared.db.get_connection")
def test_create_tenant_membership_commits(
    mock_get_connection,
):
    membership = {
        "tenant_id": "tenant-123",
        "user_id": "member-123",
        "role": "member",
    }

    connection, cursor = create_mock_connection(
        fetchone=membership
    )

    mock_get_connection.return_value = connection

    result = create_tenant_membership(
        tenant_id="tenant-123",
        user_id="member-123",
        role="member",
    )

    assert result == membership

    assert cursor.execute.call_args.args[1] == (
        "tenant-123",
        "member-123",
        "member",
    )

    connection.commit.assert_called_once()


@patch("shared.db.get_connection")
def test_update_tenant_member_role_commits(
    mock_get_connection,
):
    updated_membership = {
        "tenant_id": "tenant-123",
        "user_id": "member-123",
        "role": "admin",
    }

    connection, cursor = create_mock_connection(
        fetchone=updated_membership
    )

    mock_get_connection.return_value = connection

    result = update_tenant_member_role(
        tenant_id="tenant-123",
        user_id="member-123",
        role="admin",
    )

    assert result["role"] == "admin"

    assert cursor.execute.call_args.args[1] == (
        "admin",
        "tenant-123",
        "member-123",
    )

    connection.commit.assert_called_once()


@patch("shared.db.get_connection")
def test_deactivate_tenant_member_commits(
    mock_get_connection,
):
    deactivated_membership = {
        "tenant_id": "tenant-123",
        "user_id": "member-123",
        "status": "inactive",
    }

    connection, cursor = create_mock_connection(
        fetchone=deactivated_membership
    )

    mock_get_connection.return_value = connection

    result = deactivate_tenant_member(
        tenant_id="tenant-123",
        user_id="member-123",
    )

    assert result["status"] == "inactive"

    assert cursor.execute.call_args.args[1] == (
        "tenant-123",
        "member-123",
    )

    connection.commit.assert_called_once()