# CloudDesk Engineering Decisions

> Architecture Decision Records for the CloudDesk multi-tenant SaaS backend.

---

## Document Status

| Field | Value |
|---|---|
| Project | CloudDesk Multi-Tenant SaaS Backend |
| Environment | `dev` |
| AWS Region | `us-east-1` |
| Infrastructure as Code | AWS SAM |
| Runtime | Python 3.13 |
| Database | Amazon RDS for PostgreSQL |
| Status | Active |

This document records the major engineering decisions made during CloudDesk.

The goal is not only to document what was chosen, but also:

- why it was chosen;
- which alternatives were considered;
- what trade-offs were accepted;
- what conditions would justify revisiting the decision.

---

## Decision Format

Each decision follows this structure:

- **Status**
- **Context**
- **Decision**
- **Rationale**
- **Alternatives considered**
- **Consequences**
- **Revisit when**

---

# ADR-001: Use a Multi-Tenant Shared Application Architecture

## Status

Accepted.

## Context

CloudDesk must support multiple customer organizations while using one backend platform.

The system must allow:

- one user to belong to multiple tenants;
- one tenant to contain multiple users;
- different roles per tenant;
- strict prevention of cross-tenant access.

## Decision

Use a shared application and shared PostgreSQL database with logical tenant isolation enforced through the `tenant_users` membership model and application authorization.

## Rationale

This is the simplest architecture that satisfies the current business requirements.

It avoids creating separate infrastructure or databases for every tenant while still allowing CloudDesk to enforce tenant-specific access.

## Alternatives Considered

### Database per tenant

Rejected because it would:

- increase provisioning complexity;
- increase cost;
- complicate migrations;
- complicate monitoring;
- be unnecessary for the current scale.

### Schema per tenant

Rejected because it would:

- complicate query management;
- increase migration complexity;
- add operational overhead without solving a demonstrated requirement.

## Consequences

Positive:

- lower infrastructure cost;
- simpler deployment;
- easier centralized reporting;
- simpler schema management.

Negative:

- tenant isolation depends on consistent authorization and query discipline;
- a coding error could create a cross-tenant exposure risk.

## Revisit When

- regulatory requirements demand stronger physical separation;
- enterprise tenants require dedicated infrastructure;
- tenant size or performance isolation becomes a problem;
- contractual requirements demand separate databases.

---

# ADR-002: Use PostgreSQL for Application Data

## Status

Accepted.

## Context

CloudDesk must store:

- users;
- tenants;
- many-to-many memberships;
- tenant roles;
- membership status;
- timestamps;
- transactional tenant creation.

## Decision

Use Amazon RDS for PostgreSQL.

## Rationale

PostgreSQL is a strong fit because CloudDesk depends on:

- relational joins;
- transactions;
- foreign keys;
- uniqueness constraints;
- many-to-many relationships;
- role and membership queries;
- strong consistency.

Tenant creation and owner membership must be committed together.

## Alternatives Considered

### DynamoDB

Rejected because the current data model is relational and transaction-heavy.

DynamoDB could support the workload, but it would require more complex access-pattern design and denormalization without a demonstrated scaling need.

### Aurora PostgreSQL

Rejected for the current stage because:

- the workload does not justify its additional cost and operational scope;
- standard RDS PostgreSQL satisfies the requirements.

## Consequences

Positive:

- strong relational integrity;
- simple membership queries;
- transactional operations;
- mature SQL ecosystem.

Negative:

- database connections become the primary scaling constraint;
- RDS introduces continuous baseline cost;
- Lambda concurrency must be monitored against connection capacity.

## Revisit When

- workload growth justifies Aurora;
- read scale requires replicas;
- availability requirements justify Multi-AZ changes;
- connection pressure requires RDS Proxy.

---

# ADR-003: Separate Cognito Identity from CloudDesk Application Users

## Status

Accepted.

## Context

Amazon Cognito manages authentication, but CloudDesk also needs application-specific user data.

## Decision

Store Cognito identities in Cognito and maintain a separate `users` record in PostgreSQL.

The Cognito subject maps the identity to the CloudDesk user.

## Rationale

Authentication and application data serve different purposes.

Cognito should manage:

- credentials;
- account confirmation;
- token issuance;
- identity claims.

PostgreSQL should manage:

- application user ID;
- tenant membership;
- tenant roles;
- user status;
- application profile fields.

## Alternatives Considered

### Store all application data in Cognito attributes

Rejected because Cognito is not a relational application database and does not model tenant memberships well.

### Create user records lazily during the first API call

Rejected because it would mix provisioning with request handling and create more runtime complexity.

## Consequences

Positive:

- clear separation of responsibilities;
- relational application data remains in PostgreSQL;
- Cognito can be replaced more easily in the future.

Negative:

- identity synchronization must be handled;
- provisioning failures can leave a confirmed Cognito user without an application record.

## Revisit When

- a different identity provider is introduced;
- federation becomes a requirement;
- provisioning needs compensation or retry workflows.

---

# ADR-004: Use Cognito Post Confirmation for User Provisioning

## Status

Accepted.

## Context

CloudDesk requires every confirmed Cognito user to have a PostgreSQL application-user record.

## Decision

Use the Cognito Post Confirmation trigger to invoke a user-provisioning Lambda.

## Rationale

The event occurs at the correct lifecycle point: after the user confirms the account.

It avoids performing synchronization during every protected API request.

## Alternatives Considered

### Provision on first `/me` request

Rejected because:

- it mixes reads with provisioning;
- it introduces additional runtime branching;
- it makes user-state behavior less predictable.

### Scheduled synchronization

Rejected because:

- it delays user availability;
- it adds unnecessary operational complexity.

## Consequences

Positive:

- user records are created early;
- API request flow remains simpler;
- provisioning is event-driven.

Negative:

- Post Confirmation failures must be investigated;
- retry and compensation behavior is limited.

## Revisit When

- asynchronous retry is required;
- external user sources are introduced;
- invitation flows need more complex provisioning.

---

# ADR-005: Use API Gateway HTTP API

## Status

Accepted.

## Context

CloudDesk needs a public HTTPS API with JWT authorization and Lambda integration.

## Decision

Use Amazon API Gateway HTTP API instead of REST API.

## Rationale

HTTP API provides:

- Lambda integrations;
- JWT authorizers;
- lower operational complexity;
- lower cost than REST API;
- sufficient routing for the current project.

## Alternatives Considered

### API Gateway REST API

Rejected because the project does not currently require:

- usage plans;
- advanced request transformations;
- API keys;
- REST API-specific integrations.

### Application Load Balancer

Rejected because the application is Lambda-first and HTTP API provides a better fit.

## Consequences

Positive:

- simpler API layer;
- lower cost;
- native JWT authorizer.

Negative:

- fewer advanced API-management capabilities.

## Revisit When

- usage plans are required;
- complex request transformation is needed;
- API key management becomes a requirement.

---

# ADR-006: Use AWS Lambda for Compute

## Status

Accepted.

## Context

CloudDesk consists of event-driven API operations with variable demand.

## Decision

Implement each API operation as a focused AWS Lambda function.

## Rationale

Lambda provides:

- automatic scaling;
- no server management;
- usage-based compute;
- direct integration with API Gateway;
- strong fit for stateless request handlers.

## Alternatives Considered

### EC2

Rejected because it would require server management, patching, scaling, and continuous compute cost.

### ECS or Fargate

Rejected because the application does not require long-running containers.

### EKS or Kubernetes

Rejected because it would add major operational complexity without solving a current problem.

## Consequences

Positive:

- low operational overhead;
- independent handlers;
- automatic scaling;
- straightforward SAM deployment.

Negative:

- cold starts;
- database connection pressure;
- distributed logs;
- runtime package constraints.

## Revisit When

- long-running workloads appear;
- persistent connections are required;
- workload economics favor containers;
- Lambda limits become restrictive.

---

# ADR-007: Use One Lambda Function per Business Operation

## Status

Accepted.

## Context

CloudDesk exposes multiple operations across users, tenants, and memberships.

## Decision

Use focused Lambda functions such as:

- `create_tenant`;
- `list_tenants`;
- `get_tenant`;
- `add_member`;
- `update_member`;
- `remove_member`.

## Rationale

This keeps handlers:

- small;
- independently deployable;
- easier to test;
- aligned with least-privilege IAM;
- easy to troubleshoot.

## Alternatives Considered

### One monolithic Lambda

Rejected because it would:

- centralize too much logic;
- make testing and permissions broader;
- increase deployment blast radius.

## Consequences

Positive:

- clearer responsibility;
- smaller handler scope;
- simpler logs and alarms per function.

Negative:

- more functions to deploy and monitor;
- repeated configuration in the SAM template.

## Revisit When

- function count becomes difficult to manage;
- route groups share significant runtime behavior;
- a framework-based Lambda monolith provides measurable value.

---

# ADR-008: Use a Shared Lambda Layer

## Status

Accepted.

## Context

Multiple Lambda functions need the same authentication, authorization, database, secret, response, serialization, and observability logic.

## Decision

Store reusable application modules in:

```text
backend/layers/shared/python/shared/
```

and third-party dependencies directly under:

```text
backend/layers/shared/python/
```

## Rationale

The layer reduces duplication and centralizes security-sensitive behavior.

## Alternatives Considered

### Copy helper modules into each function

Rejected because it would create duplication and inconsistent behavior.

### Package everything independently

Rejected because the project would have repeated dependencies and larger artifacts.

## Consequences

Positive:

- centralized logic;
- easier security fixes;
- consistent responses and authorization;
- smaller function folders.

Negative:

- all functions depend on layer compatibility;
- local Windows testing must avoid importing Linux binaries before local packages;
- layer versioning must be managed.

## Revisit When

- deployment coupling becomes a problem;
- functions require conflicting dependency versions;
- packaging tools provide a better approach.

---

# ADR-009: Centralize Authorization

## Status

Accepted.

## Context

Every tenant-scoped handler must enforce consistent membership and role rules.

## Decision

Use reusable helpers:

```python
require_membership()
require_admin()
require_owner()
```

## Rationale

Authorization logic is security-critical and should not be duplicated across handlers.

## Alternatives Considered

### Inline checks in every handler

Rejected because duplicated checks can drift and create vulnerabilities.

### IAM-only authorization

Rejected because tenant roles are application data, not AWS identities.

## Consequences

Positive:

- consistent access rules;
- easier tests;
- easier reviews;
- simpler handlers.

Negative:

- authorization helpers become a critical shared dependency.

## Revisit When

- policy complexity justifies a policy engine;
- fine-grained resource permissions expand significantly.

---

# ADR-010: Use Application-Level Tenant Isolation

## Status

Accepted.

## Context

CloudDesk uses a shared PostgreSQL schema.

## Decision

Enforce tenant isolation by verifying the current user's active membership before tenant operations.

## Rationale

The current project scale and complexity do not justify a separate policy engine or PostgreSQL row-level security.

## Alternatives Considered

### PostgreSQL Row-Level Security

Deferred because:

- it adds database-policy complexity;
- the project already enforces roles in the application;
- it is not required for the current milestone.

## Consequences

Positive:

- clear application behavior;
- easier handler-level testing.

Negative:

- every query must remain tenant-aware;
- application mistakes remain a risk.

## Revisit When

- defense-in-depth requirements increase;
- the query layer expands;
- a production security review recommends database-enforced isolation.

---

# ADR-011: Use Soft Deletion for Membership Removal

## Status

Accepted.

## Context

CloudDesk should preserve membership history.

## Decision

Set membership status to `inactive` rather than deleting the row.

## Rationale

Soft deletion supports:

- audit history;
- recovery;
- accidental-deletion protection;
- future reactivation.

## Alternatives Considered

### Hard deletion

Rejected because it permanently removes useful membership history.

## Consequences

Positive:

- historical data preserved;
- easier future auditing.

Negative:

- queries must filter by active status;
- reactivation behavior must eventually be defined.

## Revisit When

- legal retention rules require physical deletion;
- data lifecycle policies are introduced.

---

# ADR-012: Protect Tenant Ownership

## Status

Accepted.

## Context

Removing or demoting the only tenant owner would leave the tenant without administrative control.

## Decision

The standard membership API cannot:

- assign `owner`;
- demote the current owner;
- remove the current owner;
- allow owner self-removal.

## Rationale

Ownership changes require a dedicated, transactional workflow.

## Alternatives Considered

### Allow owner changes through the role endpoint

Rejected because it could create ownerless tenants or ambiguous authority.

## Consequences

Positive:

- protects tenant continuity;
- prevents accidental lockout.

Negative:

- ownership transfer is not currently supported.

## Revisit When

- a dedicated ownership-transfer workflow is implemented.

---

# ADR-013: Store Database Credentials in Secrets Manager

## Status

Accepted.

## Context

Lambda requires PostgreSQL credentials.

## Decision

Store credentials in AWS Secrets Manager and pass only the secret ARN to the application.

## Rationale

This avoids hardcoded credentials and supports future rotation.

## Alternatives Considered

### Environment variables containing passwords

Rejected because credentials would be directly visible in configuration and deployment history.

### Parameter Store

Not selected because Secrets Manager is purpose-built for secrets and future rotation.

## Consequences

Positive:

- no database password in source control;
- centralized secret management;
- future rotation support.

Negative:

- recurring cost;
- runtime dependency;
- caching and rotation behavior must be considered.

## Revisit When

- rotation is enabled;
- secret architecture changes;
- organization-wide secret-management standards are introduced.

---

# ADR-014: Use a Secrets Manager Interface VPC Endpoint

## Status

Accepted.

## Context

VPC-connected Lambda functions need to retrieve database credentials without public internet access.

## Decision

Use a Secrets Manager interface endpoint.

## Rationale

This provides private service access without adding a NAT Gateway solely for secret retrieval.

## Alternatives Considered

### NAT Gateway

Rejected because it would add a larger recurring cost and broader outbound connectivity.

### Public internet path

Rejected because the Lambda functions are designed for private dependency access.

## Consequences

Positive:

- private secret retrieval;
- avoids NAT Gateway;
- explicit endpoint security group.

Negative:

- interface endpoint has recurring cost;
- additional network resources.

## Revisit When

- multiple private workloads require broad outbound internet access;
- a centralized egress design is introduced.

---

# ADR-015: Use AWS SAM

## Status

Accepted.

## Context

CloudDesk is primarily a serverless AWS application.

## Decision

Use AWS SAM and CloudFormation for Infrastructure as Code.

## Rationale

SAM provides direct support for:

- Lambda;
- API Gateway;
- events;
- layers;
- IAM policies;
- CloudFormation outputs.

## Alternatives Considered

### Terraform

Not added because maintaining the same application in two IaC tools would create unnecessary complexity.

### Manual console deployment

Rejected because it is not repeatable and does not support reliable CI/CD.

## Consequences

Positive:

- serverless-native templates;
- CloudFormation rollback;
- repeatable deployment;
- GitHub Actions integration.

Negative:

- CloudFormation errors can be verbose;
- some existing resource relationships require careful parameterization.

## Revisit When

- the portfolio needs a Terraform-specific project;
- CloudDesk expands beyond SAM's comfortable scope;
- organization standards require Terraform.

---

# ADR-016: Use GitHub Actions for CI/CD

## Status

Accepted.

## Context

CloudDesk requires automated quality checks and deployment.

## Decision

Use:

```text
.github/workflows/ci.yml
.github/workflows/deploy.yml
```

## Rationale

GitHub Actions integrates directly with the repository and supports OIDC authentication to AWS.

## Consequences

Positive:

- automated validation;
- deployment only after successful CI;
- visible workflow history;
- no separate CI platform.

Negative:

- workflow permissions and triggers must be maintained;
- deployment depends on GitHub availability.

## Revisit When

- organization-wide CI moves to another platform;
- deployment requirements require a specialized release system.

---

# ADR-017: Use GitHub OIDC Instead of AWS Access Keys

## Status

Accepted.

## Context

CI/CD requires AWS credentials.

## Decision

Use GitHub OIDC and AWS STS `AssumeRoleWithWebIdentity`.

## Rationale

OIDC provides short-lived credentials and eliminates long-lived AWS keys in GitHub.

## Alternatives Considered

### GitHub repository secrets containing AWS keys

Rejected because static credentials create a larger security risk and require rotation.

## Consequences

Positive:

- no long-lived AWS keys;
- trust restricted by repository and branch;
- temporary credentials.

Negative:

- trust policies are sensitive to exact OIDC subject claims;
- immutable GitHub subject configuration required troubleshooting.

## Revisit When

- GitHub identity configuration changes;
- separate deployment roles are created for staging and production.

---

# ADR-018: Separate CI and Deployment Workflows

## Status

Accepted.

## Context

CloudDesk must not deploy code that has not passed validation.

## Decision

Use one workflow for CI and another triggered after successful CI on `main`.

## Rationale

This creates a clear gate between validation and deployment.

The deployment workflow checks out the exact commit SHA validated by CI.

## Consequences

Positive:

- deployment is blocked by test or build failures;
- exact validated commit is deployed;
- responsibilities remain clear.

Negative:

- workflow chaining adds configuration complexity.

## Revisit When

- release environments require approvals;
- reusable workflows simplify the design.

---

# ADR-019: Use Black, isort, Ruff, pytest, and pytest-cov

## Status

Accepted.

## Context

The project needs automated code quality and testing.

## Decision

Use:

- Black for formatting;
- isort for import ordering;
- Ruff for linting;
- pytest for tests;
- pytest-cov for coverage.

## Rationale

These tools provide fast, widely understood Python quality gates.

## Consequences

Positive:

- consistent code;
- fewer review debates;
- fast feedback;
- measurable coverage.

Negative:

- tooling configuration must exclude vendored layer dependencies.

---

# ADR-020: Use Native CloudWatch Observability

## Status

Accepted.

## Context

CloudDesk needs logs, metrics, alarms, notifications, and dashboards.

## Decision

Use CloudWatch and SNS.

## Rationale

CloudDesk is AWS-native, and CloudWatch already provides the required service metrics.

## Alternatives Considered

### Prometheus and Grafana

Rejected because they would add infrastructure and maintenance without solving a current monitoring gap.

### Third-party observability platform

Rejected because the project does not require its additional features or cost.

## Consequences

Positive:

- native integration;
- no additional platform;
- simple deployment.

Negative:

- dashboard flexibility is more limited than specialized platforms;
- custom application metrics are not yet implemented.

## Revisit When

- multi-cloud monitoring is required;
- advanced visualization becomes necessary;
- observability requirements exceed CloudWatch.

---

# ADR-021: Apply 30-Day Log Retention After Deployment

## Status

Accepted.

## Context

Lambda automatically created some log groups before CloudFormation attempted to manage them.

This caused `AlreadyExists` failures.

## Decision

Deploy the stack first, then apply 30-day retention to existing CloudDesk Lambda log groups in the deployment workflow.

## Rationale

This avoids conflicts with automatically created log groups.

## Alternatives Considered

### Explicit CloudFormation log-group resources

Rejected for the current stack because existing groups caused deployment failure.

## Consequences

Positive:

- deployment succeeds;
- logs do not remain indefinitely.

Negative:

- never-invoked functions may not yet have log groups;
- retention may require later reconciliation.

## Revisit When

- all function log groups can be managed predictably;
- a dedicated retention-reconciliation job is introduced.

---

# ADR-022: Use Structured Logging for Critical Mutations

## Status

Accepted.

## Context

Tenant and membership mutations are high-value operational events.

## Decision

Instrument:

- tenant creation;
- member addition;
- role update;
- member removal.

## Rationale

These operations are important for troubleshooting and future auditing.

## Consequences

Positive:

- better incident investigation;
- request and tenant context;
- consistent operation outcomes.

Negative:

- not every handler is instrumented yet;
- logs are not a complete audit store.

## Revisit When

- all handlers require instrumentation;
- a dedicated audit-event system is introduced.

---

# ADR-023: Do Not Add RDS Proxy Yet

## Status

Accepted.

## Context

Lambda concurrency can create database connection pressure.

## Decision

Use direct Lambda-to-RDS connections with connection reuse for the current workload.

## Rationale

There is no demonstrated connection-exhaustion problem yet.

## Alternatives Considered

### RDS Proxy

Deferred because it adds cost and infrastructure complexity.

## Consequences

Positive:

- simpler architecture;
- lower cost.

Negative:

- direct connections remain a scaling risk.

## Revisit When

- concurrency grows;
- connection exhaustion appears;
- failover connection handling needs improvement.

---

# ADR-024: Do Not Add Containers or Kubernetes

## Status

Accepted.

## Context

The project goal is to solve the current backend requirements without overengineering.

## Decision

Do not add Docker, ECS, EKS, or Kubernetes.

## Rationale

The workload is well suited to Lambda.

Adding containers would not improve the current architecture.

## Revisit When

- long-running processes appear;
- workload packaging requires containers;
- runtime limits become a problem.

---

# ADR-025: Keep the Database-Test Endpoint for Development Verification

## Status

Accepted with restriction.

## Context

The team needs a way to verify Lambda, Secrets Manager, VPC networking, and PostgreSQL together.

## Decision

Keep `/database-test` during development.

## Rationale

It provides a direct deployment-verification signal.

## Consequences

Positive:

- fast networking and database diagnostics.

Negative:

- it may expose unnecessary database metadata;
- it is not suitable as a public production endpoint.

## Revisit When

- production hardening begins;
- a safer internal health-check design is implemented.

---

# ADR-026: Use Security Response Headers

## Status

Accepted.

## Context

Authenticated API responses should reduce browser-related exposure and caching.

## Decision

Add:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Cache-Control: no-store
```

## Rationale

These headers are low-cost defensive controls.

## Consequences

Positive:

- prevents content sniffing;
- prevents framing;
- reduces referrer leakage;
- prevents response caching.

Negative:

- request-ID propagation is still incomplete.

---

# ADR-027: Do Not Add WAF or Rate Limiting Yet

## Status

Deferred.

## Context

CloudDesk is a development portfolio environment.

## Decision

Do not add WAF or route-specific throttling during the current milestone.

## Rationale

The project does not yet have public production traffic or a measured abuse problem.

## Consequences

Positive:

- avoids unnecessary cost and configuration.

Negative:

- public production hardening remains incomplete.

## Revisit When

- public traffic is introduced;
- threat modeling identifies abuse risks;
- production launch begins.

---

# ADR-028: Use Manual Initial Database Migration

## Status

Accepted temporarily.

## Context

The initial schema must be applied to PostgreSQL.

## Decision

Run the initial SQL migration manually from an environment with database access.

## Rationale

The project has one initial migration and does not yet require a migration orchestration system.

## Consequences

Positive:

- simple;
- transparent;
- no additional tool.

Negative:

- not ideal for multiple environments;
- no automated rollback;
- deployment and schema changes are separate.

## Revisit When

- additional migrations are added;
- staging and production environments exist;
- deployment approvals and rollback procedures are defined.

---

# ADR-029: Use a Development-First Environment

## Status

Accepted.

## Context

CloudDesk is a portfolio project under active development.

## Decision

Deploy the current implementation as `dev` in `us-east-1`.

## Rationale

This avoids the cost and complexity of duplicate environments before the application is stable.

## Consequences

Positive:

- lower cost;
- simpler learning environment.

Negative:

- does not demonstrate full environment separation;
- production release controls are not present.

## Revisit When

- staging tests are required;
- production launch is considered;
- environment-specific IAM and data separation are implemented.

---

## Decision Summary

CloudDesk deliberately prioritizes:

- secure defaults;
- managed AWS services;
- clear tenant isolation;
- automation;
- maintainability;
- operational visibility;
- cost-conscious simplicity.

The project intentionally avoids technologies that do not solve a current problem.

The architecture should evolve only when new requirements, measurements, or risks justify the change.
