"""
PostgreSQL connection management for CloudDesk Lambda functions.
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from .secrets import get_database_secret

logger = logging.getLogger(__name__)

_connection: Connection[dict[str, Any]] | None = None


class DatabaseConnectionError(RuntimeError):
    """Raised when CloudDesk cannot establish a PostgreSQL connection."""


def get_connection() -> Connection[dict[str, Any]]:
    """
    Return a reusable PostgreSQL connection.

    Lambda may reuse the same execution environment for multiple
    invocations, so an existing healthy connection is reused.
    """

    global _connection

    if _connection is not None and not _connection.closed:
        return _connection

    secret = get_database_secret()

    try:
        _connection = psycopg.connect(
            host=secret["host"],
            port=secret["port"],
            dbname=secret["dbname"],
            user=secret["username"],
            password=secret["password"],
            connect_timeout=5,
            row_factory=dict_row,
            application_name="clouddesk-lambda",
        )
    except psycopg.Error as error:
        logger.exception("Failed to connect to the CloudDesk database")
        raise DatabaseConnectionError(
            "Unable to establish a database connection"
        ) from error

    logger.info(
        "PostgreSQL connection established",
        extra={
            "database": secret["dbname"],
            "host": secret["host"],
        },
    )

    return _connection


@contextmanager
def database_transaction() -> Generator[
    Connection[dict[str, Any]],
    None,
    None,
]:
    """
    Provide a PostgreSQL connection within a managed transaction.

    Commits successful operations and rolls back failed operations.
    """

    connection = get_connection()

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        logger.exception("Database transaction failed and was rolled back")
        raise


def close_connection() -> None:
    """Close the cached PostgreSQL connection when explicitly required."""

    global _connection

    if _connection is not None and not _connection.closed:
        _connection.close()
        logger.info("PostgreSQL connection closed")

    _connection = None

def get_user_by_cognito_sub(
    cognito_sub: str,
) -> dict[str, Any] | None:
    """
    Find a CloudDesk user using their Cognito sub identifier.

    Returns None when the Cognito user has not yet been synchronized
    with the CloudDesk database.
    """

    query = """
        SELECT
            id,
            cognito_user_id,
            email,
            first_name,
            last_name,
            status,
            created_at,
            updated_at
        FROM users
        WHERE cognito_user_id = %s;
    """

    with database_transaction() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (cognito_sub,))
            return cursor.fetchone()


def create_user(
    cognito_sub: str,
    email: str,
    first_name: str,
    last_name: str,
) -> dict[str, Any]:
    """
    Create a CloudDesk user linked to an authenticated Cognito user.

    Returns the newly created database record.
    """

    query = """
        INSERT INTO users (
            cognito_user_id,
            email,
            first_name,
            last_name
        )
        VALUES (%s, %s, %s, %s)
        RETURNING
            id,
            cognito_user_id,
            email,
            first_name,
            last_name,
            status,
            created_at,
            updated_at;
    """

    with database_transaction() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    cognito_sub,
                    email.strip().lower(),
                    first_name.strip(),
                    last_name.strip(),
                ),
            )

            user = cursor.fetchone()

            if user is None:
                raise RuntimeError(
                    "The user was created but no database record was returned."
                )

            return user

def get_tenant_by_slug(slug: str):
    """Return a tenant matching the supplied slug."""

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                name,
                slug,
                status,
                created_at,
                updated_at
            FROM tenants
            WHERE slug = %s;
            """,
            (slug,),
        )

        return cursor.fetchone()


def create_tenant_with_owner(
    name: str,
    slug: str,
    owner_user_id,
):
    """
    Create a tenant and assign the supplied user as its owner.

    Both inserts run inside one transaction. If either insert fails,
    the complete operation is rolled back.
    """

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tenants (
                    name,
                    slug,
                    status
                )
                VALUES (%s, %s, 'active')
                RETURNING
                    id,
                    name,
                    slug,
                    status,
                    created_at,
                    updated_at;
                """,
                (name, slug),
            )

            tenant = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO tenant_users (
                    tenant_id,
                    user_id,
                    role,
                    status
                )
                VALUES (%s, %s, 'owner', 'active');
                """,
                (
                    tenant["id"],
                    owner_user_id,
                ),
            )

        connection.commit()
        return tenant

    except Exception:
        connection.rollback()
        raise

def get_tenants_for_user(user_id):
    """Return active tenant memberships for a CloudDesk user."""

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                t.id,
                t.name,
                t.slug,
                t.status,
                tu.role,
                tu.status AS membership_status,
                t.created_at,
                t.updated_at
            FROM tenant_users tu
            JOIN tenants t
                ON t.id = tu.tenant_id
            WHERE tu.user_id = %s
              AND tu.status = 'active'
              AND t.status = 'active'
            ORDER BY t.name ASC;
            """,
            (user_id,),
        )

        return cursor.fetchall()

def get_membership(
    tenant_id,
    user_id,
):
    """
    Return the authenticated user's membership
    within a tenant.
    """

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tenant_id,
                user_id,
                role,
                status,
                created_at,
                updated_at
            FROM tenant_users
            WHERE tenant_id = %s
              AND user_id = %s;
            """,
            (
                tenant_id,
                user_id,
            ),
        )

        return cursor.fetchone()    

def get_tenant_by_id(tenant_id):
    """
    Return a tenant by its identifier.
    """

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                name,
                slug,
                status,
                created_at,
                updated_at
            FROM tenants
            WHERE id = %s
              AND status = 'active';
            """,
            (tenant_id,),
        )

        return cursor.fetchone()

def get_tenant_members(tenant_id):
    """
    Return all active members belonging to a tenant.
    """

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                tu.role,
                tu.status,
                tu.created_at
            FROM tenant_users tu
            JOIN users u
                ON tu.user_id = u.id
            WHERE tu.tenant_id = %s
              AND tu.status = 'active'
            ORDER BY
                CASE tu.role
                    WHEN 'owner' THEN 1
                    WHEN 'admin' THEN 2
                    WHEN 'member' THEN 3
                END,
                u.first_name,
                u.last_name;
            """,
            (tenant_id,),
        )

        return cursor.fetchall()

def get_user_by_email(email):
    """
    Return an active CloudDesk user by email address.
    """

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                email,
                first_name,
                last_name,
                status
            FROM users
            WHERE email = %s
              AND status = 'active';
            """,
            (email,),
        )

        return cursor.fetchone()

def create_tenant_membership(
    tenant_id,
    user_id,
    role="member",
):
    """
    Add an existing user to a tenant.
    """

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO tenant_users (
                tenant_id,
                user_id,
                role
            )
            VALUES (%s, %s, %s)
            RETURNING
                tenant_id,
                user_id,
                role,
                status,
                created_at;
            """,
            (
                tenant_id,
                user_id,
                role,
            ),
        )

        membership = cursor.fetchone()

    connection.commit()

    return membership

def update_tenant_member_role(
    tenant_id,
    user_id,
    role,
):
    """
    Update a tenant member's role.
    """

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE tenant_users
            SET
                role = %s,
                updated_at = NOW()
            WHERE tenant_id = %s
              AND user_id = %s
              AND status = 'active'
            RETURNING
                tenant_id,
                user_id,
                role,
                status,
                created_at,
                updated_at;
            """,
            (
                role,
                tenant_id,
                user_id,
            ),
        )

        membership = cursor.fetchone()

    connection.commit()

    return membership

def get_tenant_member(
    tenant_id,
    user_id,
):
    """
    Return a tenant membership by tenant and user.
    """

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tenant_id,
                user_id,
                role,
                status,
                created_at,
                updated_at
            FROM tenant_users
            WHERE tenant_id = %s
              AND user_id = %s;
            """,
            (
                tenant_id,
                user_id,
            ),
        )

        return cursor.fetchone()

def deactivate_tenant_member(
    tenant_id,
    user_id,
):
    """
    Soft delete a tenant membership by marking it inactive.
    """

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE tenant_users
            SET
                status = 'inactive',
                updated_at = NOW()
            WHERE tenant_id = %s
              AND user_id = %s
              AND status = 'active'
            RETURNING
                tenant_id,
                user_id,
                role,
                status,
                created_at,
                updated_at;
            """,
            (
                tenant_id,
                user_id,
            ),
        )

        membership = cursor.fetchone()

    connection.commit()

    return membership