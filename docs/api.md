# CloudDesk API Documentation

## 1. Overview

CloudDesk exposes a serverless HTTP API for user, tenant, and tenant-membership management.

The API is implemented with:

- Amazon API Gateway HTTP API;
- AWS Lambda;
- Amazon Cognito JWT authorization;
- Amazon RDS for PostgreSQL.

Protected routes require a valid Cognito token.

---

## 2. Base URL

The deployed API follows this format:

```text
https://<api-id>.execute-api.us-east-1.amazonaws.com/<environment>
```

For the development environment:

```text
https://<api-id>.execute-api.us-east-1.amazonaws.com/dev
```

Replace `<api-id>` with the API Gateway identifier returned by the SAM deployment.

---

## 3. Authentication

Protected routes require an authorization header:

```http
Authorization: Bearer <token>
```

Example:

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/me"
```

API Gateway validates the token before invoking the protected Lambda function.

---

## 4. Content Type

Requests containing JSON must include:

```http
Content-Type: application/json
```

Example:

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"NovaTech","slug":"novatech"}' \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants"
```

---

## 5. Response Structure

CloudDesk uses a consistent JSON response structure.

### Successful response

```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": {}
}
```

### Error response

```json
{
  "success": false,
  "message": "The request could not be completed."
}
```

Some successful responses may return a list or object inside `data`.

---

## 6. Common HTTP Status Codes

| Status code | Meaning |
|---|---|
| `200` | Request completed successfully |
| `201` | Resource created successfully |
| `400` | Invalid input or business-rule violation |
| `401` | Authentication failed |
| `403` | Authenticated user lacks permission |
| `404` | Requested resource was not found |
| `409` | Resource conflict, such as duplicate membership |
| `500` | Unexpected server error |

---

# Platform Endpoints

## 7. Health Check

Checks whether API Gateway and the Lambda runtime are available.

### Request

```http
GET /health
```

### Authentication

Not required.

### Example

```bash
curl \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/health"
```

### Example successful response

```json
{
  "success": true,
  "message": "CloudDesk API is healthy.",
  "data": {
    "application": "CloudDesk",
    "environment": "dev"
  }
}
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `200` | API is available |
| `500` | Lambda execution failed |

---

## 8. Database Connectivity Test

Verifies that the Lambda function can retrieve the database secret and connect to PostgreSQL.

### Request

```http
GET /database-test
```

### Authentication

Depends on the current SAM route configuration.

This endpoint is intended for deployment verification and should not remain publicly exposed in a production environment.

### Example

```bash
curl \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/database-test"
```

### Example successful response

```json
{
  "success": true,
  "message": "Database connection successful.",
  "data": {
    "database": "clouddesk",
    "user": "clouddesk_admin",
    "version": "PostgreSQL",
    "server_time": "2026-07-30T20:00:00+00:00"
  }
}
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `200` | Database connection succeeded |
| `500` | Secret retrieval or database connection failed |

---

# User Endpoint

## 9. Get Current User

Returns the authenticated CloudDesk application user.

### Request

```http
GET /me
```

### Authentication

Required.

### Authorization

Any authenticated CloudDesk user.

### Example

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/me"
```

### Example successful response

```json
{
  "success": true,
  "message": "User retrieved successfully.",
  "data": {
    "id": "2e347506-254a-4d31-b4d0-74a3a24d7396",
    "cognito_sub": "12345678-1234-1234-1234-123456789012",
    "email": "owner@example.com",
    "first_name": "Simeon",
    "last_name": "Siaka",
    "status": "active",
    "created_at": "2026-07-20T15:20:30+00:00",
    "updated_at": "2026-07-20T15:20:30+00:00"
  }
}
```

### Error responses

#### Missing or invalid token

```json
{
  "message": "Unauthorized"
}
```

Status:

```text
401 Unauthorized
```

#### Application user not found

```json
{
  "success": false,
  "message": "Authenticated CloudDesk user was not found."
}
```

Status:

```text
401 Unauthorized
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `200` | User returned successfully |
| `401` | Authentication failed or user record was not found |
| `500` | Unexpected server error |

---

# Tenant Endpoints

## 10. Create Tenant

Creates a new tenant and assigns the authenticated user as its owner.

### Request

```http
POST /tenants
```

### Authentication

Required.

### Authorization

Any authenticated CloudDesk user.

### Request body

```json
{
  "name": "NovaTech",
  "slug": "novatech"
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `name` | string | Yes | Human-readable tenant name |
| `slug` | string | Yes | Unique tenant identifier used in application logic |

### Example

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "NovaTech",
        "slug": "novatech"
      }' \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants"
```

### Example successful response

```json
{
  "success": true,
  "message": "Tenant created successfully.",
  "data": {
    "id": "b763fbb4-8fe3-4198-a69b-990a1e35b92c",
    "name": "NovaTech",
    "slug": "novatech",
    "status": "active",
    "created_at": "2026-07-25T11:30:00+00:00",
    "updated_at": "2026-07-25T11:30:00+00:00"
  }
}
```

### Business behavior

The operation creates both:

1. the tenant record;
2. the owner's membership record.

Both database operations occur in one transaction.

### Error responses

#### Missing fields

```json
{
  "success": false,
  "message": "Tenant name and slug are required."
}
```

Status:

```text
400 Bad Request
```

#### Slug already exists

```json
{
  "success": false,
  "message": "A tenant with this slug already exists."
}
```

Status:

```text
409 Conflict
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `201` | Tenant created successfully |
| `400` | Invalid request body |
| `401` | Authentication failed |
| `409` | Tenant slug already exists |
| `500` | Unexpected server error |

---

## 11. List Current User's Tenants

Returns tenants where the authenticated user has an active membership.

### Request

```http
GET /tenants
```

### Authentication

Required.

### Authorization

Any authenticated CloudDesk user.

### Example

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants"
```

### Example successful response

```json
{
  "success": true,
  "message": "Tenants retrieved successfully.",
  "data": [
    {
      "id": "b763fbb4-8fe3-4198-a69b-990a1e35b92c",
      "name": "NovaTech",
      "slug": "novatech",
      "status": "active",
      "role": "owner",
      "membership_status": "active",
      "created_at": "2026-07-25T11:30:00+00:00",
      "updated_at": "2026-07-25T11:30:00+00:00"
    }
  ]
}
```

### Empty result

```json
{
  "success": true,
  "message": "Tenants retrieved successfully.",
  "data": []
}
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `200` | Tenants returned successfully |
| `401` | Authentication failed |
| `500` | Unexpected server error |

---

## 12. Get Tenant

Returns one tenant after verifying that the authenticated user has an active membership.

### Request

```http
GET /tenants/{tenantId}
```

### Authentication

Required.

### Authorization

Active tenant membership required.

Permitted roles:

- `owner`
- `admin`
- `member`

### Path parameters

| Parameter | Description |
|---|---|
| `tenantId` | Tenant UUID |

### Example

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/b763fbb4-8fe3-4198-a69b-990a1e35b92c"
```

### Example successful response

```json
{
  "success": true,
  "message": "Tenant retrieved successfully.",
  "data": {
    "id": "b763fbb4-8fe3-4198-a69b-990a1e35b92c",
    "name": "NovaTech",
    "slug": "novatech",
    "status": "active",
    "created_at": "2026-07-25T11:30:00+00:00",
    "updated_at": "2026-07-25T11:30:00+00:00"
  }
}
```

### Error responses

#### Tenant ID missing

```json
{
  "success": false,
  "message": "Tenant ID is required."
}
```

Status:

```text
400 Bad Request
```

#### User is not an active tenant member

```json
{
  "success": false,
  "message": "You do not have access to this tenant."
}
```

Status:

```text
403 Forbidden
```

#### Tenant not found

```json
{
  "success": false,
  "message": "Tenant not found."
}
```

Status:

```text
404 Not Found
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `200` | Tenant returned successfully |
| `400` | Tenant ID missing |
| `401` | Authentication failed |
| `403` | Active tenant membership required |
| `404` | Tenant not found |
| `500` | Unexpected server error |

---

# Tenant Membership Endpoints

## 13. List Tenant Members

Returns active members of a tenant.

### Request

```http
GET /tenants/{tenantId}/members
```

### Authentication

Required.

### Authorization

Active tenant membership required.

Permitted roles:

- `owner`
- `admin`
- `member`

### Path parameters

| Parameter | Description |
|---|---|
| `tenantId` | Tenant UUID |

### Example

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/b763fbb4-8fe3-4198-a69b-990a1e35b92c/members"
```

### Example successful response

```json
{
  "success": true,
  "message": "Tenant members retrieved successfully.",
  "data": [
    {
      "tenant_id": "b763fbb4-8fe3-4198-a69b-990a1e35b92c",
      "user_id": "2e347506-254a-4d31-b4d0-74a3a24d7396",
      "email": "owner@example.com",
      "first_name": "Simeon",
      "last_name": "Siaka",
      "role": "owner",
      "status": "active",
      "created_at": "2026-07-25T11:30:00+00:00",
      "updated_at": "2026-07-25T11:30:00+00:00"
    },
    {
      "tenant_id": "b763fbb4-8fe3-4198-a69b-990a1e35b92c",
      "user_id": "716f39f8-6ec8-46c1-a8a9-e430a1f67310",
      "email": "member@example.com",
      "first_name": "Cloud",
      "last_name": "Member",
      "role": "admin",
      "status": "active",
      "created_at": "2026-07-26T09:15:00+00:00",
      "updated_at": "2026-07-27T10:20:00+00:00"
    }
  ]
}
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `200` | Members returned successfully |
| `400` | Tenant ID missing |
| `401` | Authentication failed |
| `403` | Active tenant membership required |
| `500` | Unexpected server error |

---

## 14. Add Tenant Member

Adds an existing CloudDesk user to a tenant.

### Request

```http
POST /tenants/{tenantId}/members
```

### Authentication

Required.

### Authorization

Tenant `owner` or `admin`.

### Path parameters

| Parameter | Description |
|---|---|
| `tenantId` | Tenant UUID |

### Request body

```json
{
  "email": "member@example.com",
  "role": "member"
}
```

### Fields

| Field | Type | Required | Allowed values |
|---|---|---:|---|
| `email` | string | Yes | Existing CloudDesk user's email |
| `role` | string | Yes | `member`, `admin` |

The standard member endpoint does not permit assigning the `owner` role.

### Example

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "email": "member@example.com",
        "role": "member"
      }' \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/b763fbb4-8fe3-4198-a69b-990a1e35b92c/members"
```

### Example successful response

```json
{
  "success": true,
  "message": "Tenant member added successfully.",
  "data": {
    "tenant_id": "b763fbb4-8fe3-4198-a69b-990a1e35b92c",
    "user_id": "716f39f8-6ec8-46c1-a8a9-e430a1f67310",
    "role": "member",
    "status": "active",
    "created_at": "2026-07-26T09:15:00+00:00",
    "updated_at": "2026-07-26T09:15:00+00:00"
  }
}
```

### Error responses

#### Missing email

```json
{
  "success": false,
  "message": "Email is required."
}
```

Status:

```text
400 Bad Request
```

#### Invalid role

```json
{
  "success": false,
  "message": "Role must be either member or admin."
}
```

Status:

```text
400 Bad Request
```

#### Insufficient role

```json
{
  "success": false,
  "message": "Tenant administrator access is required."
}
```

Status:

```text
403 Forbidden
```

#### User not found

```json
{
  "success": false,
  "message": "CloudDesk user not found."
}
```

Status:

```text
404 Not Found
```

#### Membership already exists

```json
{
  "success": false,
  "message": "The user is already a member of this tenant."
}
```

Status:

```text
409 Conflict
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `201` | Member added successfully |
| `400` | Invalid input |
| `401` | Authentication failed |
| `403` | Owner or admin access required |
| `404` | CloudDesk user not found |
| `409` | Membership already exists |
| `500` | Unexpected server error |

---

## 15. Update Tenant Member Role

Changes an existing tenant member's role.

### Request

```http
PUT /tenants/{tenantId}/members/{userId}
```

### Authentication

Required.

### Authorization

Tenant `owner` only.

### Path parameters

| Parameter | Description |
|---|---|
| `tenantId` | Tenant UUID |
| `userId` | Target CloudDesk user UUID |

### Request body

```json
{
  "role": "admin"
}
```

### Allowed roles

```text
member
admin
```

The endpoint does not permit assigning the `owner` role.

### Example

```bash
curl -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "role": "admin"
      }' \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/b763fbb4-8fe3-4198-a69b-990a1e35b92c/members/716f39f8-6ec8-46c1-a8a9-e430a1f67310"
```

### Example successful response

```json
{
  "success": true,
  "message": "Tenant member role updated successfully.",
  "data": {
    "tenant_id": "b763fbb4-8fe3-4198-a69b-990a1e35b92c",
    "user_id": "716f39f8-6ec8-46c1-a8a9-e430a1f67310",
    "role": "admin",
    "status": "active",
    "created_at": "2026-07-26T09:15:00+00:00",
    "updated_at": "2026-07-27T10:20:00+00:00"
  }
}
```

### Business rules

- Only the tenant owner can update roles.
- The `owner` role cannot be assigned.
- The tenant owner's role cannot be changed.
- The target membership must exist.

### Error responses

#### Missing path parameters

```json
{
  "success": false,
  "message": "Tenant ID and User ID are required."
}
```

Status:

```text
400 Bad Request
```

#### Invalid role

```json
{
  "success": false,
  "message": "Role must be either member or admin."
}
```

Status:

```text
400 Bad Request
```

#### Non-owner attempts update

```json
{
  "success": false,
  "message": "Tenant owner access is required."
}
```

Status:

```text
403 Forbidden
```

#### Target membership not found

```json
{
  "success": false,
  "message": "Tenant member not found."
}
```

Status:

```text
404 Not Found
```

#### Attempt to change owner role

```json
{
  "success": false,
  "message": "The tenant owner's role cannot be changed."
}
```

Status:

```text
400 Bad Request
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `200` | Role updated successfully |
| `400` | Invalid role or protected-owner operation |
| `401` | Authentication failed |
| `403` | Tenant owner access required |
| `404` | Tenant member not found |
| `500` | Unexpected server error |

---

## 16. Remove Tenant Member

Removes a member by marking the membership inactive.

### Request

```http
DELETE /tenants/{tenantId}/members/{userId}
```

### Authentication

Required.

### Authorization

Tenant `owner` only.

### Path parameters

| Parameter | Description |
|---|---|
| `tenantId` | Tenant UUID |
| `userId` | Target CloudDesk user UUID |

### Example

```bash
curl -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/b763fbb4-8fe3-4198-a69b-990a1e35b92c/members/716f39f8-6ec8-46c1-a8a9-e430a1f67310"
```

### Example successful response

```json
{
  "success": true,
  "message": "Tenant member removed successfully.",
  "data": {
    "tenant_id": "b763fbb4-8fe3-4198-a69b-990a1e35b92c",
    "user_id": "716f39f8-6ec8-46c1-a8a9-e430a1f67310",
    "role": "admin",
    "status": "inactive",
    "created_at": "2026-07-26T09:15:00+00:00",
    "updated_at": "2026-07-30T18:40:00+00:00"
  }
}
```

### Soft-delete behavior

The membership row is retained.

The database changes:

```text
status = active
```

to:

```text
status = inactive
```

This preserves membership history.

### Business rules

- Only the tenant owner may remove a member.
- The tenant owner cannot be removed.
- Self-removal is rejected by the current endpoint.
- The target membership must exist.

### Error responses

#### Missing path parameters

```json
{
  "success": false,
  "message": "Tenant ID and User ID are required."
}
```

Status:

```text
400 Bad Request
```

#### Non-owner attempts removal

```json
{
  "success": false,
  "message": "Tenant owner access is required."
}
```

Status:

```text
403 Forbidden
```

#### Target membership not found

```json
{
  "success": false,
  "message": "Tenant member not found."
}
```

Status:

```text
404 Not Found
```

#### Attempt to remove tenant owner

```json
{
  "success": false,
  "message": "The tenant owner cannot be removed."
}
```

Status:

```text
400 Bad Request
```

#### Attempt to remove yourself

```json
{
  "success": false,
  "message": "You cannot remove yourself from the tenant."
}
```

Status:

```text
400 Bad Request
```

### Possible status codes

| Status code | Meaning |
|---|---|
| `200` | Membership deactivated successfully |
| `400` | Invalid or protected removal operation |
| `401` | Authentication failed |
| `403` | Tenant owner access required |
| `404` | Tenant member not found |
| `500` | Unexpected server error |

---

# Authorization Matrix

## 17. Tenant Role Permissions

| Endpoint | Member | Admin | Owner |
|---|---:|---:|---:|
| `GET /tenants/{tenantId}` | Yes | Yes | Yes |
| `GET /tenants/{tenantId}/members` | Yes | Yes | Yes |
| `POST /tenants/{tenantId}/members` | No | Yes | Yes |
| `PUT /tenants/{tenantId}/members/{userId}` | No | No | Yes |
| `DELETE /tenants/{tenantId}/members/{userId}` | No | No | Yes |

The authenticated user must also have an active membership.

---

# Error Handling

## 18. Authentication Errors

Authentication errors occur when:

- the authorization header is missing;
- the token is invalid;
- the token is expired;
- the token issuer or audience is invalid;
- the CloudDesk application user cannot be resolved.

API Gateway may return its own unauthorized response before Lambda is invoked.

---

## 19. Authorization Errors

Authorization errors occur when:

- the user is not a tenant member;
- the membership is inactive;
- the user lacks admin access;
- the user lacks owner access.

Example:

```json
{
  "success": false,
  "message": "Tenant owner access is required."
}
```

Status:

```text
403 Forbidden
```

---

## 20. Validation Errors

Validation errors occur when:

- required path parameters are missing;
- required JSON fields are missing;
- JSON cannot be parsed;
- a role is not supported;
- a protected owner operation is attempted.

Example:

```json
{
  "success": false,
  "message": "Role must be either member or admin."
}
```

Status:

```text
400 Bad Request
```

---

## 21. Conflict Errors

A conflict occurs when a requested operation would duplicate an existing resource.

Examples:

- creating a duplicate tenant slug;
- adding a user who already has a tenant membership.

Example:

```json
{
  "success": false,
  "message": "The user is already a member of this tenant."
}
```

Status:

```text
409 Conflict
```

---

## 22. Server Errors

Unexpected failures return a generic error response.

Example:

```json
{
  "success": false,
  "message": "Unable to complete the request."
}
```

Status:

```text
500 Internal Server Error
```

Internal implementation details and secrets should not be returned to API clients.

Detailed failures should be investigated through CloudWatch Logs.

---

# Testing Workflow

## 23. Environment Variables

Set the base URL and token:

```bash
export BASE_URL="https://<api-id>.execute-api.us-east-1.amazonaws.com/dev"
export TOKEN="<cognito-token>"
```

Set tenant and user identifiers:

```bash
export TENANT_ID="<tenant-id>"
export USER_ID="<user-id>"
```

---

## 24. Suggested Endpoint Test Order

Test the API in this order:

```text
1. GET /health
2. GET /database-test
3. GET /me
4. POST /tenants
5. GET /tenants
6. GET /tenants/{tenantId}
7. GET /tenants/{tenantId}/members
8. POST /tenants/{tenantId}/members
9. PUT /tenants/{tenantId}/members/{userId}
10. DELETE /tenants/{tenantId}/members/{userId}
```

This order follows the natural resource lifecycle.

---

## 25. Verify the Membership Lifecycle

After adding a member:

```sql
SELECT
    tenant_id,
    user_id,
    role,
    status,
    created_at,
    updated_at
FROM tenant_users
WHERE tenant_id = '<tenant-id>'
  AND user_id = '<user-id>';
```

Expected:

```text
role = member
status = active
```

After updating the role:

```text
role = admin
status = active
```

After removing the member:

```text
role = admin
status = inactive
```

The row should remain present because removal uses soft deletion.

---

# API Security Notes

## 26. Token Handling

Tokens must not be:

- committed to Git;
- stored in screenshots intended for public repositories;
- written into documentation;
- shared in public channels.

Use temporary shell variables during testing.

---

## 27. Tenant Isolation

A tenant UUID is not an authorization mechanism.

Every tenant-scoped endpoint must verify:

1. the authenticated application user;
2. the user's tenant membership;
3. the membership status;
4. the required role.

A user should not gain access simply by changing the `tenantId` path parameter.

---

## 28. Database Test Endpoint

The `/database-test` endpoint is useful during development, but it exposes database metadata.

Before a production release, it should be:

- removed;
- disabled;
- or restricted to trusted administrative access.

It should never return:

- database passwords;
- complete secret values;
- connection strings containing credentials.

---

# Current API Limitations

## 29. Existing User Requirement

The add-member endpoint currently requires the target user to already exist in CloudDesk.

It does not yet send invitations to unregistered email addresses.

A future workflow may:

1. create an invitation;
2. email the recipient;
3. allow signup;
4. accept the invitation;
5. activate tenant membership.

---

## 30. Ownership Transfer

The current API does not support transferring tenant ownership.

The owner role cannot be assigned through the standard update-member endpoint.

A future ownership-transfer operation should be transactional and explicitly protected.

---

## 31. Reactivating Memberships

The current API soft-deletes memberships by setting them to `inactive`.

The current documentation does not define a separate reactivation endpoint.

Future implementation may support reactivation or may update the add-member workflow to safely reactivate inactive memberships.

---

## 32. Pagination

The current list endpoints do not yet document pagination.

Pagination should be introduced when tenant or membership collections can become large enough to justify it.

---

## 33. API Versioning

The current routes do not include an explicit version prefix.

Current format:

```text
/tenants
```

A future production API may use:

```text
/v1/tenants
```

Versioning should be introduced before incompatible public API changes.

---

# Endpoint Summary

## 34. Complete Endpoint Table

| Method | Endpoint | Authentication | Required tenant role |
|---|---|---:|---|
| `GET` | `/health` | No | Not applicable |
| `GET` | `/database-test` | Configuration-dependent | Not applicable |
| `GET` | `/me` | Yes | Not applicable |
| `POST` | `/tenants` | Yes | Not applicable |
| `GET` | `/tenants` | Yes | Not applicable |
| `GET` | `/tenants/{tenantId}` | Yes | Member, admin, or owner |
| `GET` | `/tenants/{tenantId}/members` | Yes | Member, admin, or owner |
| `POST` | `/tenants/{tenantId}/members` | Yes | Admin or owner |
| `PUT` | `/tenants/{tenantId}/members/{userId}` | Yes | Owner |
| `DELETE` | `/tenants/{tenantId}/members/{userId}` | Yes | Owner |

---

## 35. API Documentation Status

This document covers the API implemented through the tenant membership management milestone.

Future API documentation should be updated when CloudDesk adds:

- tenant-scoped business resources;
- invitation workflows;
- ownership transfer;
- audit events;
- pagination;
- monitoring endpoints;
- additional API versions.