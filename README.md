# CloudDesk Multi-Tenant SaaS Backend

CloudDesk is a production-style multi-tenant SaaS backend built on AWS.

The project demonstrates how users can authenticate, create organizations, manage tenant memberships, and enforce role-based access control using serverless AWS services and PostgreSQL.

CloudDesk was designed as part of the AWS 80 Projects portfolio to demonstrate practical Cloud Infrastructure Engineering skills rather than simply reproducing a tutorial.

---

## Business Scenario

CloudDesk provides the backend foundation for a collaborative business platform.

A registered user can:

- Create an organization.
- Become the owner of that organization.
- Belong to multiple organizations.
- Add existing CloudDesk users to an organization.
- Assign `admin` or `member` roles.
- Update member roles.
- Remove members without deleting their historical membership records.

Each organization is represented as a tenant. Access to tenant data is controlled through tenant membership and role-based authorization.

---

## Business Requirements

CloudDesk must:

- Securely authenticate users.
- Automatically create an application user after signup confirmation.
- Allow one user to belong to multiple tenants.
- Allow one tenant to contain multiple users.
- Enforce tenant-level authorization.
- Support `owner`, `admin`, and `member` roles.
- Prevent unauthorized access to tenant data.
- Store database credentials securely.
- Deploy through repeatable Infrastructure as Code.
- Remain understandable, maintainable, and cost-conscious.

---

## Functional Requirements

### User authentication

- Users register and authenticate through Amazon Cognito.
- API Gateway validates JSON Web Tokens before invoking protected Lambda functions.
- Confirmed Cognito users are automatically provisioned in PostgreSQL.
- Authenticated users can retrieve their CloudDesk user profile.

### Tenant management

- Create a tenant.
- Automatically assign the creator as the tenant owner.
- List tenants belonging to the authenticated user.
- Retrieve a tenant only when the authenticated user belongs to it.

### Membership management

- List active tenant members.
- Add an existing CloudDesk user to a tenant.
- Assign `admin` or `member` roles.
- Update a member's role.
- Remove a member through soft deletion.

### Authorization

CloudDesk supports three tenant roles:

| Role | Permissions |
|---|---|
| `owner` | Full tenant and membership administration |
| `admin` | Add users and access tenant resources |
| `member` | Access tenant resources available to regular members |

---

## Non-Functional Requirements

CloudDesk should provide:

- Secure authentication and authorization.
- Tenant data isolation.
- Maintainable application code.
- Repeatable infrastructure deployment.
- Private database connectivity.
- Secure secret retrieval.
- Consistent API responses.
- Cost-conscious infrastructure.
- Scalable stateless compute.
- Auditable membership changes.
- Clear operational documentation.

---

## Solution Architecture

```text
Client
  │
  │ HTTPS request with Cognito JWT
  ▼
Amazon API Gateway HTTP API
  │
  │ Cognito JWT Authorizer
  ▼
AWS Lambda
  │
  ├── Authentication
  ├── Authorization
  ├── Input validation
  └── Business logic
  │
  ▼
Shared Lambda Layer
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
  ├── users
  ├── tenants
  └── tenant_users
```

Detailed architecture documentation is available in:

```text
docs/architecture.md
```

---

## Network Architecture

Database-connected Lambda functions run inside the configured VPC.

```text
AWS Lambda
  │
  ├── Lambda security group
  │
  ├── Private subnet connectivity
  │
  ├── PostgreSQL traffic to RDS on port 5432
  │
  └── HTTPS traffic to Secrets Manager endpoint on port 443
  │
  ├──────────────► Secrets Manager interface VPC endpoint
  │
  └──────────────► Amazon RDS for PostgreSQL
```

The RDS security group allows PostgreSQL traffic from the Lambda security group.

The Secrets Manager interface endpoint allows Lambda to retrieve database credentials privately without requiring a NAT Gateway.

---

## Identity and User Provisioning

CloudDesk separates authentication identities from application users.

```text
User signup
    │
    ▼
Amazon Cognito
    │
    ▼
User confirms account
    │
    ▼
Post Confirmation Lambda
    │
    ▼
CloudDesk users table
```

Amazon Cognito manages authentication-related information such as:

- User credentials.
- Account confirmation.
- Identity claims.
- Token issuance.

PostgreSQL stores CloudDesk application information such as:

- CloudDesk user ID.
- Email address.
- First and last name.
- Tenant ownership.
- Tenant membership.
- Tenant role.
- Membership status.

This prevents the identity provider from becoming the application database.

---

## Authentication Flow

Protected API requests follow this flow:

```text
Client
  │
  │ Access token
  ▼
API Gateway JWT Authorizer
  │
  │ Token validated
  ▼
Lambda
  │
  ▼
get_current_user()
  │
  ▼
CloudDesk users table
```

API Gateway validates the token before the protected Lambda function runs.

Lambda does not repeat JWT signature verification. It reads the validated claims supplied by API Gateway and maps the Cognito identity to the corresponding CloudDesk user.

---

## Multi-Tenant Data Model

```text
users
  │
  │ One user can have many memberships
  ▼
tenant_users
  ▲
  │ One tenant can have many memberships
  │
tenants
```

The `tenant_users` table connects users and tenants.

It stores:

- `tenant_id`
- `user_id`
- `role`
- `status`
- `created_at`
- `updated_at`

This allows one user to belong to multiple tenants while holding a different role in each tenant.

### Database tables

#### `users`

Stores CloudDesk application users provisioned after Cognito confirmation.

#### `tenants`

Stores organizations created inside CloudDesk.

#### `tenant_users`

Stores the many-to-many relationship between users and tenants, including the user's role and membership status.

---

## Authentication and Authorization

Authentication answers:

> Who is making the request?

Authorization answers:

> Is this user permitted to perform this action?

CloudDesk centralizes authorization through reusable helpers:

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
        └── Permits owner or admin

require_owner()
        │
        ├── Calls require_membership()
        └── Permits owner only
```

This prevents permission logic from being duplicated across Lambda handlers.

---

## Membership Lifecycle

```text
Existing CloudDesk user
        │
        ▼
Added to tenant
status = active
role = member or admin
        │
        ▼
Role may be updated
member ↔ admin
        │
        ▼
Membership removed
status = inactive
```

Membership removal uses soft deletion.

The row remains in PostgreSQL, but its status changes from `active` to `inactive`.

This preserves historical membership information and supports future audit or restoration requirements.

---

## Implemented API Endpoints

### Platform endpoints

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/health` | Confirm API and Lambda availability | Public |
| `GET` | `/database-test` | Verify database connectivity | Deployment verification |

### User endpoint

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/me` | Return the authenticated CloudDesk user | Authenticated user |

### Tenant endpoints

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `POST` | `/tenants` | Create a tenant and assign the creator as owner | Authenticated user |
| `GET` | `/tenants` | List tenants belonging to the current user | Authenticated user |
| `GET` | `/tenants/{tenantId}` | Retrieve a tenant | Active tenant member |

### Tenant membership endpoints

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/tenants/{tenantId}/members` | List active tenant members | Active tenant member |
| `POST` | `/tenants/{tenantId}/members` | Add an existing CloudDesk user | Owner or admin |
| `PUT` | `/tenants/{tenantId}/members/{userId}` | Update a member's role | Owner |
| `DELETE` | `/tenants/{tenantId}/members/{userId}` | Deactivate a membership | Owner |

Complete request and response documentation is available in:

```text
docs/api.md
```

---

## Repository Structure

```text
clouddesk-multi-tenant-saas/
├── backend/
│   ├── add_member/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── create_tenant/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── database/
│   │   └── migrations/
│   │       └── 001_initial_schema.sql
│   ├── database_test/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── get_tenant/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── health/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── layers/
│   │   └── shared/
│   │       ├── requirements.txt
│   │       └── python/
│   │           ├── shared/
│   │           │   ├── __init__.py
│   │           │   ├── auth.py
│   │           │   ├── authorization.py
│   │           │   ├── config.py
│   │           │   ├── db.py
│   │           │   ├── response.py
│   │           │   ├── secrets.py
│   │           │   └── serialization.py
│   │           ├── psycopg/
│   │           ├── psycopg_binary/
│   │           ├── psycopg_binary.libs/
│   │           └── tzdata/
│   ├── list_members/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── list_tenants/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── me/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── remove_member/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── update_member/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── user_provisioning/
│   │   ├── __init__.py
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── samconfig.toml
│   └── template.yaml
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── decisions.md
│   └── troubleshooting.md
├── .gitignore
└── README.md
```

---

## Shared Application Modules

CloudDesk uses a shared Lambda layer to avoid duplicating common functionality.

| Module | Responsibility |
|---|---|
| `config.py` | Central application configuration |
| `secrets.py` | Retrieve and validate database credentials |
| `db.py` | PostgreSQL connection and database queries |
| `auth.py` | Extract authenticated identity and current user |
| `authorization.py` | Enforce tenant membership and roles |
| `response.py` | Generate consistent API responses |
| `serialization.py` | Convert UUID and timestamp values into JSON-compatible formats |

Application modules remain under:

```text
backend/layers/shared/python/shared/
```

Third-party dependencies remain under:

```text
backend/layers/shared/python/
```

---

## AWS Services

| Service | Purpose |
|---|---|
| Amazon API Gateway HTTP API | API routing and JWT authorization |
| AWS Lambda | Serverless application compute |
| Amazon Cognito | User registration and authentication |
| Amazon RDS for PostgreSQL | Relational application database |
| AWS Secrets Manager | Secure database credential storage |
| AWS Identity and Access Management | Lambda execution permissions |
| Amazon VPC | Private network connectivity |
| AWS PrivateLink interface endpoint | Private Secrets Manager access |
| AWS CloudFormation | Infrastructure provisioning through AWS SAM |
| Amazon CloudWatch | Lambda logs and operational visibility |

---

## Infrastructure as Code

CloudDesk infrastructure is defined using AWS SAM.

The SAM template provisions or configures:

- API Gateway HTTP API.
- Cognito User Pool.
- Cognito application client.
- API Gateway JWT authorizer.
- Lambda functions.
- Shared Lambda layer.
- IAM execution permissions.
- Lambda security group.
- RDS security-group ingress.
- Secrets Manager interface VPC endpoint.
- Lambda permission for the Cognito Post Confirmation trigger.

AWS SAM was selected because the project is primarily serverless and SAM provides direct support for Lambda, API Gateway, layers, Cognito integrations, and CloudFormation deployments.

Terraform was not added because using two Infrastructure as Code tools for the same application would introduce unnecessary complexity without solving an additional requirement.

---

## Prerequisites

Install and configure:

- AWS CLI.
- AWS SAM CLI.
- Python 3.13.
- PostgreSQL client.
- Git.

Confirm AWS authentication:

```bash
aws sts get-caller-identity
```

Confirm the SAM CLI installation:

```bash
sam --version
```

---

## Deployment

Move into the backend directory:

```bash
cd backend
```

### Validate the SAM template

```bash
sam validate
```

### Build the application

```bash
sam build
```

### Deploy the application

```bash
sam deploy
```

Deployment configuration is stored in:

```text
backend/samconfig.toml
```

The CloudFormation stack is:

```text
clouddesk-backend
```

The deployment region is:

```text
us-east-1
```

---

## Database Migration

The initial schema is located at:

```text
backend/database/migrations/001_initial_schema.sql
```

The migration creates:

- `tenant_status`
- `user_status`
- `tenant_role`
- `users`
- `tenants`
- `tenant_users`
- Indexes
- Foreign keys
- Timestamp update triggers

Apply the migration using a PostgreSQL client connected to the CloudDesk database:

```bash
psql \
  --host=<database-endpoint> \
  --port=5432 \
  --username=<database-user> \
  --dbname=<database-name> \
  --file=database/migrations/001_initial_schema.sql
```

Database credentials must be retrieved securely from AWS Secrets Manager and must never be committed to the repository.

---

## API Usage Examples

Set the authenticated user's access token:

```bash
export TOKEN="<cognito-access-token>"
```

### Retrieve the authenticated user

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/me"
```

### Create a tenant

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

### List the user's tenants

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants"
```

### Retrieve a tenant

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/<tenant-id>"
```

### List tenant members

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/<tenant-id>/members"
```

### Add an existing CloudDesk user

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "email": "employee@example.com",
        "role": "member"
      }' \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/<tenant-id>/members"
```

### Update a member's role

```bash
curl -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "role": "admin"
      }' \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/<tenant-id>/members/<user-id>"
```

### Remove a tenant member

```bash
curl -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/tenants/<tenant-id>/members/<user-id>"
```

---

## Security Considerations

CloudDesk implements the following security controls:

- API Gateway validates Cognito JWTs before protected Lambda functions run.
- Database credentials are stored in AWS Secrets Manager.
- Secrets are not stored in source code or committed to Git.
- Database-connected Lambda functions run inside the VPC.
- RDS accepts PostgreSQL traffic from the Lambda security group.
- Secrets Manager is accessed through a VPC interface endpoint.
- Lambda permissions are limited to required AWS operations.
- Tenant access requires an active membership.
- Administrative actions require appropriate tenant roles.
- The `owner` role cannot be assigned through the standard member endpoint.
- The tenant owner cannot be demoted.
- The tenant owner cannot be removed.
- Membership removal uses soft deletion.
- Tenant-scoped endpoints verify membership before returning tenant data.

---

## Reliability Considerations

The architecture provides:

- Managed authentication through Amazon Cognito.
- Managed API routing through API Gateway.
- Stateless Lambda compute.
- Transactional tenant creation and owner assignment.
- PostgreSQL relational integrity.
- Soft membership deletion.
- Reusable error handling.
- CloudWatch execution logs.
- Consistent application response structures.

For higher traffic, Amazon RDS Proxy may be considered to manage Lambda database connections.

RDS Proxy is intentionally not included at this stage because the current workload does not justify the additional infrastructure and cost.

---

## Scalability Considerations

API Gateway and Lambda can scale automatically with incoming requests.

```text
API Gateway
     │
     ▼
AWS Lambda
     │
     ▼
PostgreSQL
```

The relational database is the primary scaling boundary.

PostgreSQL remains appropriate because CloudDesk requires:

- Relational joins.
- Transactional consistency.
- Tenant membership relationships.
- Role-based access queries.
- Foreign-key integrity.

A distributed database or container orchestration platform would introduce unnecessary complexity for the current workload.

---

## Performance Considerations

- API Gateway HTTP API provides lightweight serverless routing.
- Lambda functions remain stateless.
- Database connections may be reused during warm Lambda invocations.
- PostgreSQL indexes support tenant and membership lookups.
- Queries use targeted identifiers instead of table scans.
- UUID and timestamp values are serialized consistently.
- Shared authorization helpers avoid repeated security logic.

Database connections and query performance should be monitored as Lambda concurrency increases.

---

## Cost Optimization

The architecture avoids unnecessary services and recurring expenses.

Cost-conscious decisions include:

- API Gateway HTTP API instead of REST API.
- Lambda instead of permanently running application servers.
- A Secrets Manager interface endpoint instead of a NAT Gateway.
- No ECS or EKS.
- No Kubernetes.
- No RDS Proxy until connection pressure requires it.
- Shared code through a Lambda layer.
- AWS-managed services for authentication and API routing.

The primary continuous cost is Amazon RDS and its supporting networking resources.

---

## AWS Well-Architected Framework Alignment

### Security

- Cognito authentication.
- API Gateway JWT authorization.
- Secrets Manager credential storage.
- Private database connectivity.
- Security-group boundaries.
- Role-based tenant authorization.
- No credentials stored in source control.

### Reliability

- Managed AWS services.
- Stateless compute.
- PostgreSQL foreign keys.
- Transaction-based tenant creation.
- Soft deletion for membership records.
- CloudWatch logging.

### Performance Efficiency

- Serverless compute.
- HTTP API.
- Indexed relational lookups.
- Warm Lambda connection reuse.
- Targeted PostgreSQL queries.

### Cost Optimization

- No NAT Gateway.
- No permanently running application servers.
- No container orchestration.
- No unnecessary second Infrastructure as Code tool.
- No RDS Proxy without a demonstrated requirement.

### Operational Excellence

- Infrastructure defined through AWS SAM.
- Shared application modules.
- Repeatable build and deployment commands.
- Consistent API responses.
- Reusable authentication and authorization helpers.
- Documented architectural decisions.

---

## Engineering Decisions

Important engineering decisions are documented in:

```text
docs/decisions.md
```

Current decisions include:

- Amazon Cognito for identity management.
- PostgreSQL for relational tenant data.
- API Gateway HTTP API instead of REST API.
- AWS Lambda and AWS SAM.
- Event-driven user provisioning.
- Separate identity and application user records.
- Shared authentication and authorization helpers.
- Role-based tenant access.
- Soft deletion for tenant memberships.
- Secrets Manager interface endpoint instead of a NAT Gateway.
- No RDS Proxy at the current scale.
- No Terraform in addition to SAM.

---

## Current Project Status

### Completed

- AWS serverless infrastructure.
- PostgreSQL schema.
- Cognito authentication.
- API Gateway JWT authorization.
- Automatic application user provisioning.
- Current-user endpoint.
- Tenant creation.
- Automatic owner assignment.
- Tenant listing.
- Protected tenant retrieval.
- Tenant membership listing.
- Member addition.
- Member role updates.
- Membership soft deletion.
- Reusable RBAC authorization layer.
- Private secret retrieval.
- Private Lambda-to-RDS connectivity.

### Planned

- Tenant-scoped business resources.
- Structured application logging.
- Automated unit tests.
- Integration tests.
- CI/CD deployment workflow.
- Monitoring and alerting.
- Production hardening.
- Architecture diagrams.
- Deployment diagrams.
- Request-flow diagrams.
- Expanded troubleshooting documentation.

---

## Lessons Learned

This project demonstrates that multi-tenancy is not achieved by adding a `tenant_id` field alone.

A credible multi-tenant SaaS backend requires:

- A clear identity model.
- Application-level user provisioning.
- Tenant membership relationships.
- Role-based authorization.
- Tenant data isolation.
- Transactional operations.
- Secure credential management.
- Private network access.
- Consistent response patterns.
- Protection of owner-level operations.

The most important architectural lesson was separating:

- Authentication.
- Authorization.
- Database access.
- Serialization.
- Response handling.
- Business logic.

This separation allowed new API endpoints to be added without duplicating security and database logic.

---

## Future Improvements

Potential future improvements include:

- Automated unit and integration testing.
- CI/CD deployment using GitHub Actions and AWS OIDC.
- Structured JSON logging.
- CloudWatch dashboards and alarms.
- AWS X-Ray tracing.
- API throttling and abuse protection.
- RDS Proxy if database connection pressure increases.
- Tenant-scoped business resources.
- Email-based member invitation workflow.
- Tenant ownership transfer.
- Audit-event storage.
- Automated database migrations.
- Backup and recovery validation.
- Separate development, staging, and production environments.

These improvements will only be introduced when they solve a clear engineering requirement.

---

## Documentation

Additional project documentation is available under:

```text
docs/
├── architecture.md
├── api.md
├── decisions.md
└── troubleshooting.md
```

---

## Author

**Simeon Siaka**

Cloud Infrastructure and DevOps portfolio project.

- Portfolio: [SimeonOnTheCloudSpace](https://simeonprimordial.github.io/SimeonOnTheCloudSpace/)
- GitHub: [simeonprimordial](https://github.com/simeonprimordial)
- LinkedIn: [Simeon Siaka](https://www.linkedin.com/in/simeon-siaka-8a8367312/)