# CloudDesk Troubleshooting Guide

> Symptoms, root causes, fixes, and prevention guidance from the CloudDesk implementation and deployment process.

---

## Document Status

| Field | Value |
|---|---|
| Project | CloudDesk Multi-Tenant SaaS Backend |
| Environment | `dev` |
| AWS Region | `us-east-1` |
| Stack | `clouddesk-backend` |
| Runtime | Python 3.13 |
| Primary tools | AWS SAM, GitHub Actions, AWS CLI, Git Bash |

---

## 1. Troubleshooting Method

Use this order:

1. identify the failing layer;
2. find the earliest error;
3. verify the active AWS account and region;
4. inspect recent changes;
5. reproduce locally where possible;
6. fix the root cause;
7. rerun the smallest relevant test;
8. rerun the full quality gate;
9. verify the deployed system.

### Architecture layers

```text
Client
API Gateway
Cognito
Lambda handler
Shared layer
Secrets Manager
VPC networking
PostgreSQL
CloudFormation
GitHub Actions
CloudWatch
SNS
```

Do not change multiple layers at once unless the evidence requires it.

---

## 2. Essential Diagnostic Commands

Verify identity:

```bash
aws sts get-caller-identity
```

Verify stack status:

```bash
aws cloudformation describe-stacks \
  --stack-name clouddesk-backend \
  --region us-east-1 \
  --query "Stacks[0].StackStatus" \
  --output text
```

Inspect recent stack events:

```bash
aws cloudformation describe-stack-events \
  --stack-name clouddesk-backend \
  --region us-east-1 \
  --max-items 50
```

Validate and build:

```bash
cd backend
sam validate
sam build
```

Run tests:

```bash
pytest
```

Tail Lambda logs:

```bash
sam logs \
  -n <LogicalFunctionName> \
  --stack-name clouddesk-backend \
  --region us-east-1 \
  --tail
```

---

# Local Development Issues

## 3. Psycopg Import Fails on Windows

### Symptom

Tests fail with an import error related to Psycopg or a Linux binary.

### Root Cause

The Lambda layer contains Linux-compatible dependencies:

```text
backend/layers/shared/python/psycopg/
backend/layers/shared/python/psycopg_binary/
backend/layers/shared/python/psycopg_binary.libs/
```

When the layer path is placed before the Windows virtual environment in `sys.path`, Python may try to load Linux binaries locally.

### Fix

Install the local development dependency:

```bash
python -m pip install "psycopg[binary]"
```

Ensure local site-packages remain ahead of the vendored Linux packages.

Append the shared application path rather than inserting the entire layer path at the beginning.

### Prevention

- keep local dependencies in `requirements-dev.txt`;
- exclude vendored packages from linting;
- do not modify the shared-layer structure;
- run tests in the configured virtual environment.

---

## 4. `boto3` Missing During Local Tests

### Symptom

```text
ModuleNotFoundError: No module named 'boto3'
```

### Root Cause

AWS Lambda provides `boto3` in the runtime, but the local Python environment does not.

### Fix

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

### Prevention

Keep `boto3` in development requirements even when it is not bundled into the Lambda artifact.

---

## 5. Virtual Environment Not Active

### Symptom

- pytest not found;
- wrong Python version;
- missing dependencies;
- commands use global Python.

### Fix in Git Bash

```bash
source .venv/Scripts/activate
```

### Fix in PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

Verify:

```bash
which python
python --version
python -m pip --version
```

---

## 6. Black, isort, or Ruff Scans Vendored Packages

### Symptom

Large numbers of formatting or lint errors appear inside Psycopg or timezone packages.

### Root Cause

The tool is scanning third-party packages under the shared layer.

### Fix

Verify exclusions in:

```text
backend/pyproject.toml
```

Exclude:

```text
.aws-sam
htmlcov
layers/shared/python/psycopg
layers/shared/python/psycopg_binary
layers/shared/python/psycopg_binary.libs
layers/shared/python/tzdata
```

### Prevention

Treat vendored packages as deployment artifacts, not application source.

---

# SAM and CloudFormation Issues

## 7. SAM Template Validation Fails

### Symptom

```text
template.yaml is not a valid SAM template
```

### Investigation

```bash
sam validate
```

Where available:

```bash
sam validate --lint
```

### Common Causes

- YAML indentation;
- invalid property;
- missing parameter;
- wrong resource reference;
- duplicate logical ID;
- incorrect policy template.

### Fix

Correct the earliest validation error.

Do not deploy until validation succeeds.

---

## 8. SAM Build Fails

### Symptom

```text
Build Failed
```

### Common Causes

- incorrect `CodeUri`;
- wrong handler path;
- missing requirements file;
- layer packaging problem;
- Python version mismatch.

### Fix

```bash
sam build --debug
```

Inspect:

```text
backend/.aws-sam/build/
```

Verify the expected handler and shared modules exist.

### Prevention

Run `sam build` in CI before deployment.

---

## 9. Required Parameter Has No Value

### Symptom

```text
Parameters: [AlarmEmail] must have values
```

or another parameter name.

### Root Cause

The SAM template added a parameter, but the deployment command did not pass it.

### Fix

1. add the GitHub repository variable;
2. add the parameter to `--parameter-overrides`;
3. rerun the workflow.

### Prevention

When adding a template parameter, update:

- `samconfig.toml`;
- `deploy.yml`;
- `deployment.md`;
- GitHub variables;
- local deployment instructions.

---

## 10. Stack Stuck in Rollback

### Symptom

```text
UPDATE_ROLLBACK_FAILED
```

### Investigation

```bash
aws cloudformation describe-stack-events \
  --stack-name clouddesk-backend \
  --region us-east-1 \
  --max-items 100
```

Find the first `CREATE_FAILED`, `UPDATE_FAILED`, or `DELETE_FAILED`.

### Fix

Correct the root cause, then continue rollback if necessary:

```bash
aws cloudformation continue-update-rollback \
  --stack-name clouddesk-backend \
  --region us-east-1
```

### Prevention

- review change sets;
- include rollback permissions in the deployment role;
- add one resource group at a time for major changes.

---

## 11. CloudFormation Cannot Delete a Resource During Rollback

### Symptom

Rollback fails with an access-denied error for a delete action.

### Root Cause

The deployment role can create a resource but cannot delete it during rollback.

### Example

```text
cloudwatch:DeleteDashboards
```

### Fix

Add the corresponding rollback permission.

### Prevention

Deployment roles need create, update, and rollback actions for stack-managed resources.

---

# GitHub Actions and OIDC Issues

## 12. `AssumeRoleWithWebIdentity` Denied

### Symptom

```text
Not authorized to perform sts:AssumeRoleWithWebIdentity
```

### Root Causes

- incorrect OIDC subject;
- immutable GitHub identifiers not included;
- wrong repository;
- wrong branch;
- wrong audience;
- missing `id-token: write`.

### Fix

Verify workflow permissions:

```yaml
permissions:
  id-token: write
  contents: read
```

Update the IAM trust policy to match the actual immutable subject:

```text
repo:<owner>@<owner-id>/<repository>@<repository-id>:ref:refs/heads/main
```

Verify audience:

```text
sts.amazonaws.com
```

### Prevention

Document the exact trust pattern without exposing real identifiers in public documentation.

---

## 13. Workflow Uses Wrong Commit

### Symptom

The deployment does not match the commit that passed CI.

### Root Cause

The deployment workflow checks out the branch tip instead of the successful workflow commit.

### Fix

Check out the exact SHA from the completed CI workflow.

### Prevention

Keep CI and deployment linked by the validated commit SHA.

---

## 14. Deployment Workflow Does Not Run

### Check

- CI workflow name matches `workflow_run`;
- CI completed successfully;
- branch is `main`;
- deployment workflow exists on the default branch;
- trigger syntax is valid.

### Prevention

Test workflow triggers with a documentation-only change before depending on them for a major deployment.

---

# IAM Permission Issues

## 15. SNS Permission Denied

### Symptom

CloudFormation fails on SNS resources.

Possible actions:

```text
sns:CreateTopic
sns:Subscribe
sns:SetTopicAttributes
sns:DeleteTopic
```

### Fix

Add the required SNS deployment actions to the GitHub deployment role.

### Prevention

Review the resource lifecycle, including rollback actions.

---

## 16. CloudWatch Alarm Permission Denied

### Symptom

Deployment fails while creating or deleting alarms.

Possible actions:

```text
cloudwatch:PutMetricAlarm
cloudwatch:DeleteAlarms
cloudwatch:DescribeAlarms
```

### Fix

Add the required CloudWatch alarm permissions.

---

## 17. Dashboard Permission Denied

### Symptom

```text
AccessDenied for cloudwatch:PutDashboard
```

or:

```text
cloudwatch:DeleteDashboards
```

### Fix

Add both creation/update and deletion permissions.

### Prevention

Remember that rollback requires deletion rights.

---

## 18. Lambda Cannot Retrieve Secret

### Symptom

- database test returns 500;
- logs show `AccessDeniedException`;
- `GetSecretValue` fails.

### Check

- secret ARN is correct;
- Lambda role has `secretsmanager:GetSecretValue`;
- policy is scoped to the correct ARN;
- secret exists in `us-east-1`.

### Fix

Update the runtime role or deployment parameter.

---

# Log Group and Git Bash Issues

## 19. Log Group Already Exists

### Symptom

```text
Resource already exists
```

for:

```text
/aws/lambda/<function-name>
```

### Root Cause

Lambda created the log group automatically before CloudFormation attempted to create it.

### Fix

Remove conflicting explicit log-group resources and apply retention after deployment.

### Prevention

Use one consistent ownership strategy for log groups.

---

## 20. Git Bash Rewrites `/aws/lambda/...`

### Symptom

AWS CLI receives a Windows path such as:

```text
C:/Program Files/Git/aws/lambda/...
```

### Root Cause

MSYS path conversion.

### Fix

Prefix the command:

```bash
MSYS_NO_PATHCONV=1 aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/clouddesk-dev-"
```

### Prevention

Use `MSYS_NO_PATHCONV=1` for AWS resource names beginning with `/`.

---

## 21. Log Retention Is Blank

### Symptom

The retention query shows no value.

### Meaning

The log group retains logs indefinitely.

### Fix

```bash
MSYS_NO_PATHCONV=1 aws logs put-retention-policy \
  --log-group-name "/aws/lambda/<function-name>" \
  --retention-in-days 30 \
  --region us-east-1
```

### Prevention

Keep the post-deployment retention step enabled.

---

## 22. New Function Has No Log Group

### Symptom

The retention loop does not find a newly deployed function.

### Root Cause

Lambda creates the log group on first invocation.

### Fix

1. invoke the function;
2. rerun the retention command;
3. verify 30-day retention.

---

# Cognito and Authentication Issues

## 23. API Returns `401 Unauthorized`

### Possible Causes

- missing token;
- expired token;
- ID token used when access token is expected;
- wrong issuer;
- wrong audience;
- malformed header.

### Check

```http
Authorization: Bearer <token>
```

Verify the token belongs to the deployed User Pool and client.

### Prevention

Document the correct token type and use temporary shell variables.

---

## 24. Cognito User Exists but `/me` Returns 401

### Root Cause

The Cognito identity exists, but the CloudDesk PostgreSQL user record does not.

### Check

- Post Confirmation trigger configuration;
- provisioning Lambda logs;
- `users` table;
- Cognito subject value.

### Fix

Correct the provisioning failure and create the missing application record through the approved process.

### Prevention

Monitor Post Confirmation failures and test signup after deployment.

---

## 25. Post Confirmation Fails

### Possible Causes

- Lambda cannot reach RDS;
- secret access denied;
- invalid user attributes;
- duplicate or malformed data;
- Lambda permission missing;
- trigger configuration wrong.

### Investigation

Tail provisioning logs:

```bash
sam logs \
  -n UserProvisioningFunction \
  --stack-name clouddesk-backend \
  --region us-east-1 \
  --tail
```

---

# Database and Networking Issues

## 26. Database Test Returns 500

### Check in Order

1. Secrets Manager access;
2. endpoint state;
3. Lambda subnet configuration;
4. Lambda security group;
5. RDS security-group ingress;
6. RDS availability;
7. secret values;
8. database name and user;
9. schema migration.

### Useful Commands

```bash
aws ec2 describe-vpc-endpoints \
  --region us-east-1 \
  --filters "Name=service-name,Values=com.amazonaws.us-east-1.secretsmanager"
```

```bash
aws rds describe-db-instances \
  --db-instance-identifier clouddesk-db \
  --region us-east-1
```

---

## 27. Lambda Times Out Connecting to PostgreSQL

### Likely Causes

- wrong subnet;
- wrong security group;
- missing RDS ingress;
- RDS unavailable;
- endpoint or DNS issue;
- incorrect host.

### Correct RDS Ingress

```text
TCP 5432
Source: Lambda security group
```

Do not open PostgreSQL to `0.0.0.0/0`.

---

## 28. Lambda Cannot Reach Secrets Manager

### Check

- interface endpoint state is `available`;
- private DNS is enabled;
- endpoint security group allows `443` from Lambda security group;
- Lambda role can retrieve the secret;
- endpoint and Lambda are in the correct VPC.

---

## 29. Database Schema Missing

### Symptom

Logs show:

```text
relation "users" does not exist
```

or another missing table.

### Fix

Apply:

```text
backend/database/migrations/001_initial_schema.sql
```

from an environment with database access.

### Prevention

Add migration verification to deployment readiness checks.

---

## 30. Transaction Does Not Roll Back

### Symptom

Partial data remains after an operation fails.

### Investigation

- verify transaction context;
- verify commit location;
- verify exception handling;
- verify rollback path;
- run handler transaction tests.

### Prevention

Keep multi-write business operations inside one transaction and retain rollback tests.

---

# API and Business Logic Issues

## 31. Tenant Creation Returns 400

### Check

The request body should be:

```json
{
  "name": "NovaTech"
}
```

The handler generates the slug.

Do not send an outdated required `slug` field.

---

## 32. Tenant Creation Returns 409

### Root Cause

The generated slug already exists.

### Fix

Use a different tenant name or implement a future slug-disambiguation strategy.

---

## 33. User Cannot Access a Tenant

### Check

```sql
SELECT tenant_id, user_id, role, status
FROM tenant_users
WHERE tenant_id = '<tenant-id>'
  AND user_id = '<user-id>';
```

The membership must exist and be:

```text
status = active
```

---

## 34. Admin Cannot Update a Role

### Explanation

This is expected.

Current rules:

- owner or admin may add a member;
- only owner may update roles;
- only owner may remove members.

---

## 35. Owner Cannot Be Removed

### Explanation

This is expected.

The owner is protected from:

- removal;
- demotion;
- self-removal.

Ownership transfer requires a future dedicated workflow.

---

## 36. Removed Member Still Exists in Database

### Explanation

This is expected.

Removal uses soft deletion:

```text
status = inactive
```

The row remains for history and future auditing.

---

# Monitoring Issues

## 37. Alarm Exists but No Email Arrives

### Check

```bash
aws sns list-subscriptions-by-topic \
  --topic-arn "<topic-arn>" \
  --region us-east-1
```

If the subscription shows:

```text
PendingConfirmation
```

confirm it from the email.

Also verify the alarm action references the topic.

---

## 38. Dashboard Has No Data

### Possible Causes

- no recent traffic;
- wrong metric dimensions;
- wrong function names;
- wrong API ID;
- wrong RDS identifier;
- dashboard time range too short.

Generate traffic, wait for metric publication, and refresh.

---

## 39. Structured Logs Missing

### Check

- handler imports `observability.py`;
- log calls exist for the operation;
- the deployed function uses the current layer;
- log level permits the event;
- the correct log group is open.

---

# Test and CI Issues

## 40. Tests Pass Locally but Fail in CI

### Common Causes

- uncommitted file;
- path case difference;
- local environment leakage;
- dependency version difference;
- environment variable present locally but not in CI;
- test order dependency.

### Fix

Run from a clean environment:

```bash
python -m venv .venv-clean
source .venv-clean/Scripts/activate
python -m pip install -r requirements-dev.txt
pytest
```

---

## 41. Coverage Gate Fails

### Fix

Run:

```bash
pytest tests/unit tests/handlers \
  --cov=layers/shared/python/shared \
  --cov-report=term-missing
```

Add meaningful tests for uncovered business logic.

Do not add empty assertions only to increase coverage.

---

## 42. CI Formatting Fails

### Fix

```bash
black .
isort .
```

Then:

```bash
black --check .
isort --check-only .
ruff check .
pytest
```

---

## 43. Deployment Runs After Failed Tests

### Expected Behavior

It should not.

### Check

- deployment uses `workflow_run`;
- condition checks successful conclusion;
- branch is `main`.

---

# Recovery Procedures

## 44. Revert a Bad Deployment

Find the commit:

```bash
git log --oneline
```

Revert:

```bash
git revert <bad-commit-sha>
git push origin main
```

CI validates the revert before deployment.

---

## 45. Delete and Recreate the Stack

Use only when appropriate.

```bash
sam delete \
  --stack-name clouddesk-backend \
  --region us-east-1
```

Remember:

- RDS is external;
- the secret may be external;
- log groups may remain;
- shared resources must not be deleted accidentally.

---

## 46. Final Escalation Checklist

Before escalating, collect:

- exact timestamp;
- AWS region;
- stack status;
- first failed CloudFormation event;
- function name;
- request ID;
- route;
- relevant log excerpt with secrets removed;
- recent commit SHA;
- whether local tests pass;
- whether CI passes;
- whether the failure is reproducible.

Do not include passwords, access tokens, or secret values.

---

## 47. Troubleshooting Summary

The most important CloudDesk troubleshooting lessons are:

- find the earliest failure;
- separate local packaging issues from Lambda runtime behavior;
- treat OIDC trust claims as exact values;
- include rollback permissions in deployment IAM;
- avoid mixed ownership of Lambda log groups;
- account for Git Bash path conversion;
- verify every new SAM parameter in CI/CD;
- test tenant authorization as aggressively as business functionality;
- do not open RDS publicly to simplify debugging;
- verify deployment through API, database, monitoring, and alarms—not only a green workflow.
