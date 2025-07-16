# AWS Resource Naming Conventions

This document defines the standardized naming patterns for all AWS resources in the DevSecOps Platform to ensure consistency, clarity, and operational efficiency across all environments.

## Overview

Consistent resource naming is critical for:
- **Operational Clarity**: Easy identification of resources and their purpose
- **Cost Management**: Accurate cost allocation and tracking
- **Security**: Clear ownership and access control
- **Automation**: Reliable resource discovery and management
- **Compliance**: Audit trail and regulatory requirements

## General Naming Pattern

All AWS resources follow this standardized pattern:

```
{project}-{environment}-{service}-{component}-{identifier}
```

### Pattern Components

| Component | Description | Examples | Required |
|-----------|-------------|----------|----------|
| `project` | Project identifier (3-8 chars) | `dso`, `platform`, `analytics` | Yes |
| `environment` | Environment identifier | `dev`, `staging`, `prod` | Yes |
| `service` | Service or domain | `data`, `ml`, `api`, `infra` | Yes |
| `component` | Specific component type | `ingestion`, `storage`, `compute` | Yes |
| `identifier` | Unique identifier | `001`, `primary`, `backup` | Optional |

## Environment Identifiers

| Environment | Identifier | Description |
|-------------|------------|-------------|
| Development | `dev` | Development and testing environment |
| Staging | `staging` | Pre-production staging environment |
| Production | `prod` | Production environment |
| Sandbox | `sandbox` | Experimental and learning environment |
| DR | `dr` | Disaster recovery environment |

## Service Categories

| Service | Identifier | Description |
|---------|------------|-------------|
| Data Ingestion | `data` | Data ingestion and processing |
| Machine Learning | `ml` | AI/ML workloads and models |
| API Services | `api` | API gateways and services |
| Infrastructure | `infra` | Core infrastructure components |
| Messaging | `msg` | Messaging and streaming |
| Security | `sec` | Security and compliance |
| Monitoring | `mon` | Monitoring and observability |

## AWS Service-Specific Naming Rules

### S3 Buckets

**Pattern**: `{project}-{environment}-{service}-{component}-{region}`

**Rules**:
- Must be globally unique
- 3-63 characters
- Lowercase letters, numbers, hyphens only
- No consecutive hyphens
- Cannot start/end with hyphen

**Examples**:
```
dso-prod-data-ingestion-us-east-1
dso-dev-ml-artifacts-us-west-2
dso-staging-api-logs-eu-west-1
```

### Lambda Functions

**Pattern**: `{project}-{environment}-{service}-{function-name}`

**Rules**:
- 1-64 characters
- Letters, numbers, hyphens, underscores
- Case sensitive

**Examples**:
```
dso-prod-data-raw-processor
dso-dev-ml-model-trainer
dso-staging-api-auth-handler
```

### DynamoDB Tables

**Pattern**: `{project}-{environment}-{service}-{table-purpose}`

**Rules**:
- 3-255 characters
- Letters, numbers, hyphens, underscores, periods
- Case sensitive

**Examples**:
```
dso-prod-data-metadata
dso-dev-ml-experiments
dso-staging-api-sessions
```

### RDS Instances

**Pattern**: `{project}-{environment}-{service}-{db-type}-{identifier}`

**Rules**:
- 1-63 characters
- Letters, numbers, hyphens only
- Must start with letter
- Cannot end with hyphen

**Examples**:
```
dso-prod-data-postgres-primary
dso-dev-ml-mysql-experiments
dso-staging-api-postgres-sessions
```

### EC2 Instances

**Pattern**: `{project}-{environment}-{service}-{role}-{az}`

**Rules**:
- Use Name tag for identification
- Include availability zone for multi-AZ deployments

**Examples**:
```
dso-prod-data-processor-1a
dso-dev-ml-training-1b
dso-staging-api-web-1c
```

### ECS Services

**Pattern**: `{project}-{environment}-{service}-{component}`

**Rules**:
- 1-255 characters
- Letters, numbers, hyphens, underscores
- Case sensitive

**Examples**:
```
dso-prod-data-ingestion-service
dso-dev-ml-training-service
dso-staging-api-gateway-service
```

### Kinesis Streams

**Pattern**: `{project}-{environment}-{service}-{stream-purpose}`

**Rules**:
- 1-128 characters
- Letters, numbers, hyphens, underscores, periods
- Case sensitive

**Examples**:
```
dso-prod-data-events-stream
dso-dev-ml-metrics-stream
dso-staging-api-logs-stream
```

### SQS Queues

**Pattern**: `{project}-{environment}-{service}-{queue-purpose}`

**Rules**:
- 1-80 characters
- Letters, numbers, hyphens, underscores
- Case sensitive
- FIFO queues must end with `.fifo`

**Examples**:
```
dso-prod-data-processing-queue
dso-dev-ml-training-queue.fifo
dso-staging-api-notifications-dlq
```

### SNS Topics

**Pattern**: `{project}-{environment}-{service}-{topic-purpose}`

**Rules**:
- 1-256 characters
- Letters, numbers, hyphens, underscores
- Case sensitive
- FIFO topics must end with `.fifo`

**Examples**:
```
dso-prod-data-alerts-topic
dso-dev-ml-notifications-topic
dso-staging-api-events-topic.fifo
```

### CloudWatch Log Groups

**Pattern**: `/aws/{service}/{project}-{environment}-{component}`

**Rules**:
- 1-512 characters
- Letters, numbers, periods, hyphens, underscores, forward slashes
- Case sensitive

**Examples**:
```
/aws/lambda/dso-prod-data-processor
/aws/ecs/dso-dev-ml-training
/aws/apigateway/dso-staging-api-gateway
```

### IAM Roles

**Pattern**: `{project}-{environment}-{service}-{role-purpose}-role`

**Rules**:
- 1-64 characters
- Letters, numbers, plus signs, equal signs, commas, periods, at signs, hyphens
- Case sensitive

**Examples**:
```
dso-prod-data-lambda-execution-role
dso-dev-ml-sagemaker-training-role
dso-staging-api-ecs-task-role
```

### KMS Keys

**Pattern**: `{project}-{environment}-{service}-{purpose}-key`

**Rules**:
- Use alias for human-readable names
- 1-256 characters for alias

**Examples**:
```
alias/dso-prod-data-encryption-key
alias/dso-dev-ml-artifacts-key
alias/dso-staging-api-secrets-key
```

## Special Naming Considerations

### Multi-Region Resources

For resources deployed across multiple regions:

```
{project}-{environment}-{service}-{component}-{region}
```

Example: `dso-prod-data-backup-us-west-2`

### High Availability Resources

For resources with primary/secondary configurations:

```
{project}-{environment}-{service}-{component}-{role}
```

Examples:
- `dso-prod-data-postgres-primary`
- `dso-prod-data-postgres-replica`

### Versioned Resources

For resources that require versioning:

```
{project}-{environment}-{service}-{component}-v{version}
```

Example: `dso-prod-ml-model-endpoint-v2`

### Temporary Resources

For temporary or ephemeral resources:

```
{project}-{environment}-{service}-{component}-temp-{timestamp}
```

Example: `dso-dev-data-migration-temp-20240101`

## Validation Rules

### Character Limits by Service

| AWS Service | Min Length | Max Length | Allowed Characters |
|-------------|------------|------------|-------------------|
| S3 Bucket | 3 | 63 | a-z, 0-9, - |
| Lambda Function | 1 | 64 | a-zA-Z, 0-9, -, _ |
| DynamoDB Table | 3 | 255 | a-zA-Z, 0-9, -, _, . |
| RDS Instance | 1 | 63 | a-zA-Z, 0-9, - |
| EC2 Instance (Name) | 1 | 255 | Any UTF-8 |
| ECS Service | 1 | 255 | a-zA-Z, 0-9, -, _ |
| Kinesis Stream | 1 | 128 | a-zA-Z, 0-9, -, _, . |
| SQS Queue | 1 | 80 | a-zA-Z, 0-9, -, _ |
| SNS Topic | 1 | 256 | a-zA-Z, 0-9, -, _ |
| IAM Role | 1 | 64 | a-zA-Z, 0-9, +=,.@- |
| KMS Key Alias | 1 | 256 | a-zA-Z, 0-9, -, _, / |

### Forbidden Patterns

- **Reserved Words**: Avoid AWS reserved words (aws, amazon, etc.)
- **IP Addresses**: Do not use IP address patterns
- **Sensitive Data**: Never include passwords, keys, or sensitive information
- **Special Characters**: Avoid special characters not allowed by the service
- **Consecutive Separators**: Avoid multiple consecutive hyphens or underscores

## Implementation Examples

### Data Ingestion Construct Resources

```python
# S3 Bucket for raw data
bucket_name = "dso-prod-data-raw-ingestion-us-east-1"

# Lambda function for processing
function_name = "dso-prod-data-raw-processor"

# DynamoDB table for metadata
table_name = "dso-prod-data-ingestion-metadata"

# SQS queue for failed messages
queue_name = "dso-prod-data-processing-dlq"

# CloudWatch log group
log_group = "/aws/lambda/dso-prod-data-raw-processor"
```

### ML Construct Resources

```python
# SageMaker endpoint
endpoint_name = "dso-prod-ml-model-endpoint"

# S3 bucket for model artifacts
artifacts_bucket = "dso-prod-ml-artifacts-us-east-1"

# IAM role for SageMaker
execution_role = "dso-prod-ml-sagemaker-execution-role"

# KMS key for encryption
encryption_key = "alias/dso-prod-ml-encryption-key"
```

### Infrastructure Construct Resources

```python
# VPC
vpc_name = "dso-prod-infra-vpc"

# ECS cluster
cluster_name = "dso-prod-infra-ecs-cluster"

# RDS instance
db_instance = "dso-prod-infra-postgres-primary"

# Load balancer
alb_name = "dso-prod-infra-application-lb"
```

## Automation and Validation

### Naming Utility Functions

The platform provides utility functions for consistent naming:

```python
from infrastructure.constructs.common.conventions import ResourceNaming

# Generate standardized names
naming = ResourceNaming(project="dso", environment="prod", service="data")

bucket_name = naming.s3_bucket("ingestion", region="us-east-1")
# Returns: "dso-prod-data-ingestion-us-east-1"

function_name = naming.lambda_function("processor")
# Returns: "dso-prod-data-processor"

table_name = naming.dynamodb_table("metadata")
# Returns: "dso-prod-data-metadata"
```

### Validation Checks

All resource names are automatically validated against:
- Service-specific character limits
- Allowed character sets
- Naming pattern compliance
- Uniqueness requirements
- Reserved word conflicts

## Compliance and Governance

### Audit Requirements

Resource names must support:
- **Traceability**: Clear ownership and purpose identification
- **Cost Allocation**: Environment and service-based cost tracking
- **Security**: Access control and compliance validation
- **Operations**: Automated discovery and management

### Monitoring and Alerting

The platform monitors for:
- Non-compliant resource names
- Naming pattern violations
- Resource naming conflicts
- Orphaned or untagged resources

## Best Practices

1. **Consistency**: Always use the standardized patterns
2. **Clarity**: Names should be self-explanatory
3. **Brevity**: Keep names as short as possible while maintaining clarity
4. **Future-Proofing**: Consider scalability and evolution
5. **Documentation**: Document any exceptions or special cases
6. **Automation**: Use provided utility functions for name generation
7. **Validation**: Always validate names before resource creation
8. **Review**: Regular audits of naming compliance

## Migration and Legacy Resources

For existing resources that don't follow these conventions:
1. **Assessment**: Identify non-compliant resources
2. **Planning**: Create migration plan with minimal disruption
3. **Gradual Migration**: Migrate during maintenance windows
4. **Validation**: Ensure new names meet all requirements
5. **Documentation**: Update all references and documentation

## Support and Exceptions

For naming convention exceptions or questions:
- **Platform Team**: platform-team@company.com
- **Architecture Review**: Submit RFC for review
- **Documentation**: Update this document for approved exceptions
- **Tooling**: Request new utility functions for special cases
