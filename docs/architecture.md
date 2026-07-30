# CloudDesk Architecture

## 1. Overview

CloudDesk is a multi-tenant SaaS backend built on AWS.

The platform allows users to:

- register and authenticate;
- create organizations called tenants;
- belong to multiple tenants;
- manage tenant membership;
- assign tenant-level roles;
- control access using role-based authorization.

The architecture uses managed AWS services and serverless compute to reduce operational overhead while maintaining clear security, networking, and data boundaries.

---

## 2. Business Context

CloudDesk provides the backend foundation for a collaborative business application.

Each customer organization is represented as a tenant.

A user may:

- own one or more tenants;
- belong to multiple tenants;
- hold a different role in each tenant;
- access only tenants where they have an active membership.

The system must prevent users from accessing another tenant's data simply by knowing or guessing a tenant identifier.

---

## 3. Architecture Goals

The architecture was designed to provide:

- secure user authentication;
- tenant-level authorization;
- private database access;
- secure credential management;
- reusable application components;
- repeatable infrastructure deployment;
- cost-conscious service selection;
- scalability at the API and compute layers;
- clear separation of application responsibilities.

---

## 4. High-Level Architecture

```text
Client Application
        │
        │ HTTPS request with Cognito JWT
        ▼
Amazon API Gateway HTTP API
        │
        │ JWT validation
        ▼
AWS Lambda Functions
        │
        ├── Authentication
        ├── Authorization
        ├── Input validation
        ├── Business logic
        └── Response handling
        │
        ▼
Shared Lambda Layer
        │
        ├── auth.py
        ├── authorization.py
        ├── config.py
        ├── db.py
        ├── response.py
        ├── secrets.py
        └── serialization.py
        │
        ├──────────────► AWS Secrets Manager
        │
        ▼
Amazon RDS for PostgreSQL
        │
        ├── users
        ├── tenants
        └── tenant_users
```

---

## 5. AWS Services

| AWS service | Responsibility |
|---|---|
| Amazon API Gateway HTTP API | Routes API requests and validates JWTs |
| AWS Lambda | Executes application logic |
| Amazon Cognito | Manages signup, login, confirmation, and token issuance |
| Amazon RDS for PostgreSQL | Stores users, tenants, memberships, roles, and statuses |
| AWS Secrets Manager | Stores database credentials |
| Amazon VPC | Provides private network connectivity |
| AWS PrivateLink interface endpoint | Provides private access to Secrets Manager |
| AWS IAM | Controls Lambda permissions |
| AWS CloudFormation | Provisions infrastructure through AWS SAM |
| Amazon CloudWatch | Stores Lambda execution logs |

---

## 6. Component Responsibilities

### 6.1 Client

The client may be:

- a web application;
- a mobile application;
- an API testing tool;
- another trusted service.

The client sends HTTPS requests to API Gateway.

Protected requests include a Cognito token in the authorization header:

```http
Authorization: Bearer <token>
```

---

### 6.2 Amazon API Gateway HTTP API

API Gateway is the public entry point for the backend.

Its responsibilities include:

- exposing API routes;
- mapping HTTP methods to Lambda functions;
- validating Cognito JWTs;
- rejecting unauthorized requests;
- forwarding validated JWT claims to Lambda;
- managing the deployment stage.

CloudDesk uses HTTP API rather than REST API because the current requirements do not need advanced REST API features.

This reduces complexity and cost.

---

### 6.3 Amazon Cognito

Amazon Cognito provides identity management.

Its responsibilities include:

- user registration;
- password management;
- account confirmation;
- authentication;
- token issuance;
- identity claims.

Cognito does not store tenant membership or application authorization data.

Those responsibilities belong to PostgreSQL.

---

### 6.4 AWS Lambda

Each API operation is implemented as a separate Lambda function.

Examples include:

- retrieving the current user;
- creating a tenant;
- listing tenants;
- retrieving a tenant;
- listing members;
- adding a member;
- updating a role;
- removing a member.

Lambda functions handle:

- validated user identity;
- input validation;
- authorization;
- business rules;
- database operations;
- API responses.

The functions remain stateless between requests.

---

### 6.5 Shared Lambda Layer

Common application code is stored in a shared Lambda layer.

```text
backend/layers/shared/
├── requirements.txt
└── python/
    ├── shared/
    │   ├── auth.py
    │   ├── authorization.py
    │   ├── config.py
    │   ├── db.py
    │   ├── response.py
    │   ├── secrets.py
    │   └── serialization.py
    ├── psycopg/
    ├── psycopg_binary/
    ├── psycopg_binary.libs/
    └── tzdata/
```

The application modules remain under:

```text
backend/layers/shared/python/shared/
```

Third-party dependencies remain directly under:

```text
backend/layers/shared/python/
```

This structure allows Lambda to import application modules as:

```python
from shared.auth import get_current_user
```

---

### 6.6 AWS Secrets Manager

Secrets Manager stores PostgreSQL connection information.

The secret contains values such as:

- host;
- port;
- database name;
- username;
- password.

Lambda functions retrieve the secret at runtime.

Credentials are not stored in:

- Lambda source code;
- `template.yaml`;
- `samconfig.toml`;
- Git;
- API requests.

---

### 6.7 Amazon RDS for PostgreSQL

PostgreSQL stores the CloudDesk application data.

The primary tables are:

```text
users
tenants
tenant_users
```

PostgreSQL was selected because the application requires:

- relational joins;
- many-to-many relationships;
- transactional consistency;
- foreign keys;
- role and membership queries;
- consistent tenant creation and owner assignment.

---

## 7. Identity Architecture

CloudDesk separates identity management from application user management.

```text
Cognito identity
        │
        │ cognito sub
        ▼
CloudDesk user record
        │
        ▼
Tenant memberships
```

Cognito answers:

> Who authenticated?

PostgreSQL answers:

> Who is this user inside CloudDesk?

This separation allows CloudDesk to store application-specific information without overloading the identity provider.

---

## 8. User Provisioning Flow

When a user confirms registration, Cognito invokes the Post Confirmation Lambda.

```text
User
  │
  │ Signs up
  ▼
Amazon Cognito
  │
  │ Confirmation completed
  ▼
Post Confirmation Lambda
  │
  │ Creates CloudDesk user record
  ▼
PostgreSQL users table
```

### Provisioning sequence

1. The user signs up through Cognito.
2. Cognito creates the identity.
3. The user confirms the account.
4. Cognito invokes the Post Confirmation Lambda.
5. The Lambda reads the Cognito attributes.
6. The Lambda inserts the CloudDesk user into PostgreSQL.
7. Future API calls map the Cognito `sub` to that application user.

This avoids performing user synchronization during every API request.

---

## 9. Authentication Flow

```text
Client
  │
  │ Sends Cognito token
  ▼
API Gateway JWT Authorizer
  │
  ├── Validates token signature
  ├── Validates issuer
  ├── Validates audience
  └── Validates expiration
  │
  ▼
Lambda
  │
  │ Reads validated claims
  ▼
get_current_user()
  │
  ▼
PostgreSQL users table
```

### Authentication responsibilities

API Gateway:

- validates the token;
- rejects invalid tokens;
- provides validated claims.

Lambda:

- reads the claims;
- extracts the Cognito subject;
- retrieves the corresponding CloudDesk user.

Lambda does not duplicate JWT signature verification.

---

## 10. Authorization Architecture

Authentication identifies the user.

Authorization determines what the user may do.

CloudDesk centralizes authorization in:

```text
authorization.py
```

The main authorization helpers are:

```python
require_membership()
require_admin()
require_owner()
```

### Authorization hierarchy

```text
require_membership()
        │
        ├── Membership must exist
        └── Membership must be active

require_admin()
        │
        ├── Calls require_membership()
        └── Allows owner or admin

require_owner()
        │
        ├── Calls require_membership()
        └── Allows owner only
```

This design ensures that:

- tenant checks are consistent;
- business handlers remain readable;
- authorization logic is not duplicated;
- role changes can be managed centrally.

---

## 11. Role Model

CloudDesk supports three tenant roles.

| Role | Description |
|---|---|
| `owner` | Highest tenant authority |
| `admin` | Manages members and accesses tenant resources |
| `member` | Standard tenant access |

### Current permissions

| Action | Member | Admin | Owner |
|---|---:|---:|---:|
| View tenant | Yes | Yes | Yes |
| List members | Yes | Yes | Yes |
| Add member | No | Yes | Yes |
| Update member role | No | No | Yes |
| Remove member | No | No | Yes |

The owner role cannot be assigned through the normal member-management endpoint.

The current owner cannot be:

- demoted;
- removed;
- replaced through the standard membership flow.

---

## 12. Multi-Tenant Data Model

```text
users
  │
  │ One-to-many
  ▼
tenant_users
  ▲
  │ Many-to-one
  │
tenants
```

### 12.1 `users`

Stores CloudDesk application users.

Typical fields include:

- `id`;
- `cognito_sub`;
- `email`;
- `first_name`;
- `last_name`;
- `status`;
- `created_at`;
- `updated_at`.

---

### 12.2 `tenants`

Stores customer organizations.

Typical fields include:

- `id`;
- `name`;
- `slug`;
- `status`;
- `created_at`;
- `updated_at`.

---

### 12.3 `tenant_users`

Stores the many-to-many relationship between users and tenants.

Typical fields include:

- `tenant_id`;
- `user_id`;
- `role`;
- `status`;
- `created_at`;
- `updated_at`.

This table is the central authorization source for tenant-scoped operations.

---

## 13. Tenant Creation Flow

```text
Authenticated User
        │
        │ POST /tenants
        ▼
API Gateway
        │
        ▼
Create Tenant Lambda
        │
        ├── Validate input
        ├── Verify current user
        ├── Create tenant
        └── Create owner membership
        │
        ▼
PostgreSQL Transaction
```

Tenant creation and owner membership creation occur in one database transaction.

This prevents a tenant from being created without an owner.

If either operation fails, the transaction is rolled back.

---

## 14. Tenant Access Flow

```text
Authenticated User
        │
        │ GET /tenants/{tenantId}
        ▼
Get Tenant Lambda
        │
        ├── Resolve current user
        ├── Require active membership
        └── Retrieve tenant
        │
        ▼
PostgreSQL
```

Knowing a tenant UUID is not enough to access the tenant.

The user must have an active membership.

---

## 15. Membership Management Flow

### Add member

```text
Owner or Admin
      │
      │ POST /tenants/{tenantId}/members
      ▼
Add Member Lambda
      │
      ├── Require admin access
      ├── Validate role
      ├── Find user by email
      ├── Check existing membership
      └── Create membership
      │
      ▼
PostgreSQL
```

Only an existing CloudDesk user can currently be added.

A future invitation workflow may support users who have not yet registered.

---

### Update role

```text
Tenant Owner
      │
      │ PUT /tenants/{tenantId}/members/{userId}
      ▼
Update Member Lambda
      │
      ├── Require owner
      ├── Validate requested role
      ├── Protect owner membership
      └── Update member role
      │
      ▼
PostgreSQL
```

The endpoint permits role changes between:

```text
member
admin
```

It does not permit assigning:

```text
owner
```

---

### Remove member

```text
Tenant Owner
      │
      │ DELETE /tenants/{tenantId}/members/{userId}
      ▼
Remove Member Lambda
      │
      ├── Require owner
      ├── Find target membership
      ├── Protect tenant owner
      ├── Prevent invalid removal
      └── Mark membership inactive
      │
      ▼
PostgreSQL
```

The membership is not physically deleted.

Instead:

```text
status = inactive
```

This is a soft-delete strategy.

---

## 16. Membership Lifecycle

```text
Membership created
status = active
        │
        ▼
Role updated
member ↔ admin
        │
        ▼
Membership deactivated
status = inactive
```

Soft deletion provides:

- membership history;
- easier auditing;
- future restoration capability;
- protection against accidental permanent deletion.

---

## 17. Network Architecture

Database-connected Lambda functions run inside the VPC.

```text
                         AWS VPC

┌─────────────────────────────────────────────────────┐
│                                                     │
│  Private Subnets                                    │
│                                                     │
│  ┌──────────────────┐                               │
│  │ AWS Lambda       │                               │
│  │                  │                               │
│  │ Lambda SG        │                               │
│  └────────┬─────────┘                               │
│           │                                         │
│           │ TCP 5432                                │
│           ▼                                         │
│  ┌──────────────────┐                               │
│  │ Amazon RDS       │                               │
│  │ PostgreSQL       │                               │
│  │                  │                               │
│  │ RDS SG           │                               │
│  └──────────────────┘                               │
│                                                     │
│           │ HTTPS 443                               │
│           ▼                                         │
│  ┌──────────────────────────────────────┐           │
│  │ Secrets Manager Interface Endpoint  │           │
│  │ Endpoint Security Group              │           │
│  └──────────────────────────────────────┘           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 18. Security Group Design

### Lambda security group

The Lambda security group allows required outbound communication.

It is referenced as the source for inbound rules on dependent resources.

---

### RDS security group

The RDS security group permits:

```text
Protocol: TCP
Port: 5432
Source: Lambda security group
```

This is safer than permitting database access from:

```text
0.0.0.0/0
```

---

### Secrets Manager endpoint security group

The endpoint security group permits:

```text
Protocol: TCP
Port: 443
Source: Lambda security group
```

This allows Lambda to access Secrets Manager privately.

---

## 19. Private Secret Retrieval

Lambda requires database credentials before connecting to PostgreSQL.

Without internet access or a NAT Gateway, Lambda reaches Secrets Manager through an interface VPC endpoint.

```text
Lambda
  │
  │ HTTPS 443
  ▼
Secrets Manager Interface Endpoint
  │
  ▼
AWS Secrets Manager
```

This design avoids adding a NAT Gateway solely for secret retrieval.

---

## 20. IAM Architecture

Each database-connected Lambda requires permission to:

- write CloudWatch logs;
- create and manage VPC network interfaces;
- retrieve the configured database secret.

The functions use:

```text
AWSLambdaVPCAccessExecutionRole
```

for VPC networking requirements.

They also receive access to the specific database secret through:

```text
AWSSecretsManagerGetSecretValuePolicy
```

The secret ARN is supplied during deployment rather than hardcoded in the repository.

---

## 21. Application Layer Design

CloudDesk separates responsibilities into reusable modules.

```text
API Handler
    │
    ├── auth.py
    ├── authorization.py
    ├── db.py
    ├── response.py
    └── serialization.py
```

### `config.py`

Provides centralized environment configuration.

### `secrets.py`

Retrieves and validates database credentials.

### `db.py`

Manages:

- PostgreSQL connections;
- transactions;
- user queries;
- tenant queries;
- membership queries.

### `auth.py`

Handles:

- JWT claim extraction;
- authenticated identity resolution;
- CloudDesk current-user lookup.

### `authorization.py`

Handles:

- membership checks;
- admin checks;
- owner checks.

### `response.py`

Generates consistent HTTP responses.

### `serialization.py`

Converts database values such as:

- UUIDs;
- timestamps;
- dates;

into JSON-compatible values.

---

## 22. API Route Architecture

### Public routes

```http
GET /health
```

The health endpoint verifies that API Gateway and Lambda are available.

---

### Protected user route

```http
GET /me
```

Requires a valid Cognito JWT.

---

### Protected tenant routes

```http
POST /tenants
GET  /tenants
GET  /tenants/{tenantId}
```

---

### Protected membership routes

```http
GET    /tenants/{tenantId}/members
POST   /tenants/{tenantId}/members
PUT    /tenants/{tenantId}/members/{userId}
DELETE /tenants/{tenantId}/members/{userId}
```

Detailed API documentation is available in:

```text
docs/api.md
```

---

## 23. Deployment Architecture

```text
Developer Workstation
        │
        │ sam validate
        │ sam build
        │ sam deploy
        ▼
AWS SAM
        │
        ▼
AWS CloudFormation
        │
        ├── API Gateway HTTP API
        ├── Cognito User Pool
        ├── Cognito User Pool Client
        ├── Lambda Functions
        ├── Shared Lambda Layer
        ├── IAM Permissions
        ├── Security Groups
        ├── RDS Ingress Rule
        └── Secrets Manager VPC Endpoint
```

Infrastructure is defined in:

```text
backend/template.yaml
```

Deployment configuration is stored in:

```text
backend/samconfig.toml
```

The deployed CloudFormation stack is:

```text
clouddesk-backend
```

---

## 24. Infrastructure as Code Decision

AWS SAM was selected because the application is primarily serverless.

SAM provides native support for:

- Lambda;
- API Gateway;
- Lambda layers;
- Cognito integrations;
- IAM policies;
- CloudFormation outputs.

Terraform was not added because maintaining the same application across two Infrastructure as Code tools would add complexity without solving a current problem.

---

## 25. Security Architecture Review

CloudDesk currently implements:

- managed authentication through Cognito;
- JWT validation at API Gateway;
- application-user mapping;
- tenant-level RBAC;
- active-membership validation;
- owner protection;
- Secrets Manager credential storage;
- VPC-based database access;
- security-group-based traffic control;
- private secret retrieval;
- IAM-scoped secret access;
- soft deletion of memberships.

---

## 26. Tenant Isolation Controls

Tenant isolation is enforced at the application layer.

For tenant-scoped routes, the request flow includes:

```text
Authenticated user
        │
        ▼
Tenant ID from request
        │
        ▼
Membership lookup
        │
        ├── Membership exists?
        ├── Membership active?
        └── Required role present?
        │
        ▼
Tenant operation allowed
```

A request is rejected when:

- the user is not authenticated;
- the CloudDesk user does not exist;
- the tenant membership does not exist;
- the membership is inactive;
- the user's role is insufficient.

---

## 27. Reliability Considerations

The architecture uses managed services for:

- authentication;
- API routing;
- compute;
- secret storage;
- database hosting;
- logging.

Reliability controls include:

- stateless Lambda functions;
- database transactions;
- relational constraints;
- foreign keys;
- reusable error handling;
- soft deletion;
- CloudWatch logs;
- managed API Gateway routing.

---

## 28. Scalability Considerations

API Gateway and Lambda can scale automatically.

```text
Incoming Requests
        │
        ▼
API Gateway
        │
        ▼
Concurrent Lambda Invocations
        │
        ▼
PostgreSQL Connections
```

The primary future scaling concern is PostgreSQL connection capacity.

Direct Lambda-to-RDS connections are acceptable for the current project scale.

Amazon RDS Proxy may be introduced later if:

- Lambda concurrency increases significantly;
- database connection exhaustion occurs;
- connection reuse becomes insufficient;
- failover behavior needs additional connection management.

RDS Proxy is not included now because the current workload does not justify it.

---

## 29. Cost Considerations

Cost-conscious decisions include:

- API Gateway HTTP API instead of REST API;
- Lambda instead of continuously running servers;
- no ECS;
- no EKS;
- no Kubernetes;
- no NAT Gateway;
- no RDS Proxy at the current scale;
- one shared Lambda layer;
- managed Cognito authentication.

The primary continuous cost is Amazon RDS and its supporting network resources.

The Secrets Manager interface endpoint also creates a recurring cost, but it replaces the need for a more expensive NAT Gateway for the current private-access requirement.

---

## 30. Operational Considerations

CloudWatch currently provides Lambda logs.

Future operational improvements may include:

- structured JSON logging;
- CloudWatch log retention configuration;
- Lambda error alarms;
- API Gateway latency alarms;
- API Gateway 4XX and 5XX alarms;
- RDS connection alarms;
- RDS CPU and storage alarms;
- dashboards;
- AWS X-Ray tracing;
- audit-event storage.

These capabilities should be introduced when their implementation milestone begins.

---

## 31. Current Limitations

The current architecture does not yet include:

- automated unit tests;
- integration tests;
- CI/CD deployment;
- tenant invitations;
- ownership transfer;
- tenant-scoped business resources;
- structured application logging;
- automated database migrations;
- application audit events;
- API throttling policies;
- RDS Proxy;
- production monitoring dashboards.

These are planned improvements rather than accidental omissions.

---

## 32. Future Architecture Improvements

Potential improvements include:

### Automated testing

Add unit and integration tests for:

- authentication helpers;
- authorization helpers;
- database functions;
- API handlers;
- tenant isolation rules.

### CI/CD

Use GitHub Actions with AWS OIDC to:

- validate SAM;
- run tests;
- build;
- deploy without long-lived AWS credentials.

### Observability

Add:

- structured JSON logs;
- correlation IDs;
- CloudWatch dashboards;
- Lambda error alarms;
- API latency alarms;
- RDS health alarms.

### Database connection management

Introduce RDS Proxy only when concurrency demonstrates a real connection-management requirement.

### Invitation workflow

Allow administrators to invite users who have not yet registered.

### Audit events

Store actions such as:

- tenant creation;
- member addition;
- role change;
- member removal.

### Ownership transfer

Create a controlled process for transferring tenant ownership.

---

## 33. AWS Well-Architected Alignment

### Operational Excellence

- Infrastructure defined with AWS SAM.
- Shared reusable modules.
- Repeatable build and deployment commands.
- Centralized authorization logic.
- CloudWatch logging.

### Security

- Cognito authentication.
- JWT validation.
- Secrets Manager credentials.
- VPC database access.
- Security-group restrictions.
- Tenant RBAC.
- Owner protection.

### Reliability

- Managed AWS services.
- Stateless compute.
- Database transactions.
- Relational integrity.
- Soft deletion.

### Performance Efficiency

- Serverless API layer.
- API Gateway HTTP API.
- Indexed PostgreSQL lookups.
- Warm Lambda connection reuse.

### Cost Optimization

- No NAT Gateway.
- No container orchestration.
- No permanently running application tier.
- No RDS Proxy without demonstrated need.
- No duplicate Infrastructure as Code tool.

### Sustainability

- Serverless compute runs only when requested.
- Unnecessary always-on compute resources are avoided.
- Managed services reduce infrastructure overhead.

---

## 34. Architecture Summary

CloudDesk currently uses a serverless API architecture with relational tenant data.

```text
Cognito
   │
   ▼
API Gateway
   │
   ▼
Lambda
   │
   ├── Shared authentication and authorization
   ├── Secrets Manager
   └── PostgreSQL
```

The architecture provides:

- authenticated access;
- tenant isolation;
- role-based authorization;
- private database connectivity;
- secure credential retrieval;
- transactional tenant creation;
- soft membership deletion;
- reusable Lambda components;
- repeatable infrastructure deployment.

The design is intentionally production-oriented without introducing infrastructure that the current workload does not require.