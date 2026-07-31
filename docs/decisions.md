# Architecture Decision Records (ADR)

This document records the major architectural and engineering decisions made during the development of CloudDesk.

The purpose of these records is to explain **why** a particular technology or design was chosen, what alternatives were considered, and the trade-offs involved.

---

# ADR-001 — Serverless Architecture

## Status

Accepted

## Decision

CloudDesk uses a serverless architecture based on:

- Amazon API Gateway HTTP API
- AWS Lambda
- AWS SAM

## Context

CloudDesk is an API-driven SaaS application with unpredictable traffic patterns and relatively lightweight request processing.

The objective is to build a scalable backend without managing application servers.

## Alternatives Considered

- Amazon ECS
- Amazon EKS
- EC2 with Nginx/Gunicorn

## Rationale

A serverless architecture provides:

- automatic scaling;
- no server management;
- pay-per-use pricing;
- faster deployment;
- native AWS integration.

Container orchestration would introduce operational complexity without solving a current business requirement.

---

# ADR-002 — Infrastructure as Code

## Status

Accepted

## Decision

AWS SAM was selected as the Infrastructure as Code tool.

## Context

CloudDesk consists primarily of Lambda functions, API Gateway, Cognito resources, IAM roles, Lambda Layers, and CloudFormation-managed infrastructure.

## Alternatives Considered

- Terraform
- AWS CDK

## Rationale

AWS SAM provides first-class support for serverless resources while generating standard CloudFormation templates.

Using Terraform alongside SAM would require maintaining two Infrastructure as Code solutions for the same application, increasing complexity without providing additional value.

Terraform may be introduced in future projects where it better aligns with the infrastructure requirements.

---

# ADR-003 — API Gateway HTTP API

## Status

Accepted

## Decision

Use Amazon API Gateway HTTP API.

## Context

CloudDesk exposes REST-style endpoints but does not require advanced REST API features such as usage plans, API keys, request validation models, or request transformation.

## Alternatives Considered

- API Gateway REST API

## Rationale

HTTP API provides:

- lower cost;
- lower latency;
- simpler configuration;
- native JWT authorization.

REST API remains a good choice for applications that require advanced API management capabilities.

---

# ADR-004 — Authentication

## Status

Accepted

## Decision

Amazon Cognito manages user authentication.

## Context

CloudDesk requires:

- user registration;
- login;
- password management;
- secure token issuance.

## Alternatives Considered

- Custom JWT implementation
- Auth0
- Keycloak

## Rationale

Amazon Cognito is a managed AWS service that integrates directly with API Gateway and eliminates the need to implement authentication logic from scratch.

---

# ADR-005 — Authorization Model

## Status

Accepted

## Decision

Separate authentication from authorization.

## Context

Authentication determines the user's identity.

Authorization determines what the authenticated user may do.

## Decision

Authorization is implemented through reusable helper functions:

```python
require_membership()
require_admin()
require_owner()
```

## Rationale

Centralizing authorization:

- reduces duplicated code;
- improves maintainability;
- provides consistent tenant security;
- simplifies future permission changes.

---

# ADR-006 — User Provisioning

## Status

Accepted

## Decision

Provision CloudDesk users using a Cognito Post Confirmation trigger.

## Context

Cognito identities should not become the application's data store.

CloudDesk requires additional application information beyond authentication.

## Alternatives Considered

- Create users during every API request
- Query Cognito directly for user information

## Rationale

Creating the application user immediately after signup:

- avoids repeated synchronization;
- keeps authentication separate from application data;
- reduces request latency;
- simplifies API handlers.

---

# ADR-007 — Relational Database

## Status

Accepted

## Decision

Amazon RDS for PostgreSQL stores application data.

## Context

CloudDesk requires:

- transactions;
- foreign keys;
- many-to-many relationships;
- relational joins.

## Alternatives Considered

- DynamoDB
- Aurora Serverless

## Rationale

PostgreSQL provides strong relational consistency and naturally models tenant membership relationships.

Aurora was unnecessary for the current workload, while DynamoDB would significantly complicate relational queries.

---

# ADR-008 — Multi-Tenant Data Model

## Status

Accepted

## Decision

Use a many-to-many relationship between users and tenants.

```text
users
    │
tenant_users
    │
tenants
```

## Context

Users may belong to multiple tenants.

Tenants may contain multiple users.

Each membership requires its own role and status.

## Rationale

The junction table supports:

- tenant-specific roles;
- membership history;
- soft deletion;
- future auditing.

---

# ADR-009 — Soft Delete Memberships

## Status

Accepted

## Decision

Removing a member marks the membership as inactive instead of deleting it.

## Context

Membership history may become valuable for auditing, troubleshooting, or future restoration.

## Alternatives Considered

- Permanent deletion

## Rationale

Soft deletion:

- preserves history;
- reduces accidental data loss;
- supports future reactivation;
- simplifies auditing.

---

# ADR-010 — Shared Lambda Layer

## Status

Accepted

## Decision

Application helper modules are stored in a shared Lambda Layer.

## Context

Authentication, authorization, database access, configuration, serialization, and response handling are used across many Lambda functions.

## Rationale

The shared layer:

- avoids duplicated code;
- keeps handlers small;
- centralizes reusable logic;
- simplifies maintenance.

Application modules remain under:

```text
backend/layers/shared/python/shared/
```

Third-party libraries remain under:

```text
backend/layers/shared/python/
```

---

# ADR-011 — Database Credentials

## Status

Accepted

## Decision

Database credentials are stored in AWS Secrets Manager.

## Context

Credentials must never be committed to source control.

## Alternatives Considered

- Environment variables
- Hardcoded credentials

## Rationale

Secrets Manager provides:

- secure storage;
- IAM-controlled access;
- credential rotation support;
- centralized secret management.

---

# ADR-012 — Private Database Connectivity

## Status

Accepted

## Decision

Database-connected Lambda functions execute inside a VPC.

## Context

Amazon RDS is not publicly accessible.

## Rationale

Private networking:

- reduces attack surface;
- keeps database traffic off the public internet;
- follows AWS security best practices.

---

# ADR-013 — Secrets Manager VPC Endpoint

## Status

Accepted

## Decision

Use an Interface VPC Endpoint instead of a NAT Gateway for secret retrieval.

## Context

Lambda functions running inside private subnets require access to Secrets Manager.

## Alternatives Considered

- NAT Gateway

## Rationale

The interface endpoint provides private connectivity without introducing a NAT Gateway solely for secret retrieval.

This aligns with the project's cost optimization goals.

---

# ADR-014 — Role-Based Access Control

## Status

Accepted

## Decision

CloudDesk implements tenant-level RBAC.

Supported roles:

- owner
- admin
- member

## Rationale

RBAC provides a simple and scalable authorization model while allowing future expansion of tenant permissions.

---

# ADR-015 — Owner Protection

## Status

Accepted

## Decision

The API protects the tenant owner.

The owner:

- cannot be removed;
- cannot be demoted;
- cannot be reassigned through standard membership endpoints.

## Rationale

Every tenant must always retain a valid owner.

This prevents orphaned tenants and protects administrative integrity.

---

# ADR-016 — Response Standardization

## Status

Accepted

## Decision

All API responses use shared response helpers.

## Rationale

Consistent responses:

- improve API usability;
- simplify frontend development;
- reduce duplicated formatting logic.

---

# ADR-017 — Serialization Layer

## Status

Accepted

## Decision

UUIDs, timestamps, and other database values are serialized through a shared helper module.

## Rationale

Centralized serialization prevents repeated conversion logic inside Lambda handlers and ensures consistent JSON responses.

---

# ADR-018 — Current Operational Scope

## Status

Accepted

## Decision

Do not introduce infrastructure until it solves a demonstrated engineering requirement.

Examples intentionally excluded at the current stage include:

- Amazon RDS Proxy
- Amazon ECS
- Amazon EKS
- Kubernetes
- Terraform alongside SAM

## Rationale

CloudDesk is intended to demonstrate sound engineering judgment rather than the number of AWS services used.

Additional services will be introduced only when they provide measurable value to the architecture.

---

# Decision Summary

| ADR | Decision |
|------|----------|
| ADR-001 | Serverless architecture |
| ADR-002 | AWS SAM |
| ADR-003 | API Gateway HTTP API |
| ADR-004 | Amazon Cognito |
| ADR-005 | Separate authentication and authorization |
| ADR-006 | Post Confirmation user provisioning |
| ADR-007 | PostgreSQL |
| ADR-008 | Many-to-many tenant model |
| ADR-009 | Soft delete memberships |
| ADR-010 | Shared Lambda Layer |
| ADR-011 | AWS Secrets Manager |
| ADR-012 | Private Lambda-to-RDS networking |
| ADR-013 | Secrets Manager Interface VPC Endpoint |
| ADR-014 | Tenant RBAC |
| ADR-015 | Owner protection |
| ADR-016 | Standardized API responses |
| ADR-017 | Shared serialization |
| ADR-018 | Introduce infrastructure only when justified |