# AWS Resource Tagging Strategy

This document defines the comprehensive tagging strategy for all AWS resources in the DevSecOps Platform to ensure proper governance, cost management, security, and compliance.

## Overview

Resource tagging is essential for:
- **Cost Management**: Accurate cost allocation and chargeback
- **Security**: Access control and compliance validation
- **Operations**: Resource discovery and automation
- **Governance**: Ownership and lifecycle management
- **Compliance**: Regulatory requirements and audit trails

## Tagging Principles

1. **Consistency**: All resources must have required tags
2. **Automation**: Tags applied automatically during resource creation
3. **Validation**: Tag values validated against defined formats
4. **Inheritance**: Child resources inherit parent resource tags
5. **Immutability**: Critical tags cannot be modified after creation

## Required Tags

All AWS resources MUST have these tags:

| Tag Key | Description | Format | Example |
|---------|-------------|--------|---------|
| `Environment` | Deployment environment | `dev\|staging\|prod\|sandbox\|dr` | `prod` |
| `Project` | Project identifier | `[a-z0-9-]{3,20}` | `devsecops-platform` |
| `Owner` | Resource owner/team | `team-name` or `email` | `platform-team` |
| `CostCenter` | Cost allocation code | `CC-[0-9]{4}` | `CC-1234` |
| `Application` | Application name | `[a-z0-9-]{3,30}` | `data-ingestion` |
| `Component` | Component type | `[a-z0-9-]{3,30}` | `lambda-processor` |
| `CreatedBy` | Creation method | `cdk\|terraform\|manual\|automation` | `cdk` |
| `CreatedDate` | Creation timestamp | `YYYY-MM-DD` | `2024-01-15` |

## Conditional Required Tags

These tags are required based on specific conditions:

### Data Classification Tags (Required for data resources)

| Tag Key | Description | Values | When Required |
|---------|-------------|--------|---------------|
| `DataClassification` | Data sensitivity level | `public\|internal\|confidential\|restricted` | S3, RDS, DynamoDB, EFS |
| `DataRetention` | Data retention period | `30d\|90d\|1y\|3y\|7y\|permanent` | Data storage resources |
| `PIIData` | Contains PII data | `true\|false` | Data processing resources |
| `EncryptionRequired` | Encryption requirement | `true\|false` | All data resources |

### Backup and Recovery Tags (Required for stateful resources)

| Tag Key | Description | Values | When Required |
|---------|-------------|--------|---------------|
| `BackupSchedule` | Backup frequency | `daily\|weekly\|monthly\|none` | RDS, EBS, EFS |
| `BackupRetention` | Backup retention | `7d\|30d\|90d\|1y\|3y` | Backup-enabled resources |
| `DisasterRecovery` | DR requirement | `critical\|important\|standard\|none` | Production resources |
| `RPO` | Recovery Point Objective | `1h\|4h\|24h\|72h` | Critical resources |
| `RTO` | Recovery Time Objective | `15m\|1h\|4h\|24h` | Critical resources |

### Security Tags (Required for security-sensitive resources)

| Tag Key | Description | Values | When Required |
|---------|-------------|--------|---------------|
| `SecurityZone` | Security zone | `public\|dmz\|internal\|restricted` | Network resources |
| `ComplianceFramework` | Compliance requirements | `sox\|pci\|hipaa\|gdpr\|iso27001` | Regulated resources |
| `SecurityReview` | Security review status | `approved\|pending\|exempt` | All resources |
| `VulnerabilityScanning` | Scanning requirement | `required\|optional\|exempt` | Compute resources |

## Optional Tags

These tags provide additional context and functionality:

### Operational Tags

| Tag Key | Description | Format | Example |
|---------|-------------|--------|---------|
| `MaintenanceWindow` | Maintenance schedule | `day:HH:MM-HH:MM` | `sunday:02:00-04:00` |
| `MonitoringLevel` | Monitoring intensity | `basic\|standard\|enhanced` | `enhanced` |
| `AlertingEnabled` | Alerting configuration | `true\|false` | `true` |
| `AutoShutdown` | Auto-shutdown schedule | `weekends\|nights\|never` | `nights` |
| `ScalingPolicy` | Auto-scaling behavior | `aggressive\|moderate\|conservative` | `moderate` |

### Business Tags

| Tag Key | Description | Format | Example |
|---------|-------------|--------|---------|
| `BusinessUnit` | Business unit | `[a-z0-9-]{2,20}` | `engineering` |
| `Department` | Department | `[a-z0-9-]{2,20}` | `platform` |
| `BudgetCode` | Budget allocation | `BG-[0-9]{4}` | `BG-5678` |
| `ChargebackCode` | Chargeback identifier | `CB-[0-9]{4}` | `CB-9012` |
| `ServiceLevel` | Service level agreement | `gold\|silver\|bronze` | `gold` |

### Technical Tags

| Tag Key | Description | Format | Example |
|---------|-------------|--------|---------|
| `Version` | Resource version | `v[0-9]+\.[0-9]+\.[0-9]+` | `v1.2.3` |
| `GitCommit` | Git commit hash | `[a-f0-9]{7,40}` | `abc1234` |
| `DeploymentId` | Deployment identifier | `[a-z0-9-]{8,32}` | `deploy-20240115-001` |
| `ConfigVersion` | Configuration version | `[0-9]+` | `42` |
| `FeatureFlag` | Feature flag status | `enabled\|disabled` | `enabled` |

## Tag Value Formats and Validation

### Format Specifications

| Tag Type | Pattern | Max Length | Case Sensitivity |
|----------|---------|------------|------------------|
| Environment | `^(dev\|staging\|prod\|sandbox\|dr)$` | 10 | Lowercase |
| Project | `^[a-z0-9-]{3,20}$` | 20 | Lowercase |
| Email | `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$` | 100 | Case-insensitive |
| Cost Center | `^CC-[0-9]{4}$` | 7 | Uppercase |
| Date | `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` | 10 | N/A |
| Boolean | `^(true\|false)$` | 5 | Lowercase |
| Version | `^v[0-9]+\.[0-9]+\.[0-9]+$` | 20 | Lowercase |

### Validation Rules

1. **Required Tags**: All required tags must be present
2. **Format Compliance**: Tag values must match defined patterns
3. **Length Limits**: Tag values must not exceed maximum length
4. **Character Sets**: Only allowed characters per AWS service limits
5. **Reserved Values**: Cannot use AWS reserved tag prefixes (`aws:`, `AWS:`)

## Compliance Framework Tagging

### SOC 2 Compliance

Required tags for SOC 2 compliance:

```yaml
ComplianceFramework: "sox"
SecurityReview: "approved"
DataClassification: "confidential"
EncryptionRequired: "true"
BackupSchedule: "daily"
MonitoringLevel: "enhanced"
```

### ISO 27001 Compliance

Required tags for ISO 27001 compliance:

```yaml
ComplianceFramework: "iso27001"
SecurityZone: "internal"
VulnerabilityScanning: "required"
DataRetention: "3y"
DisasterRecovery: "critical"
```

### GDPR Compliance

Required tags for GDPR compliance:

```yaml
ComplianceFramework: "gdpr"
PIIData: "true"
DataClassification: "restricted"
DataRetention: "1y"
EncryptionRequired: "true"
```

### HIPAA Compliance

Required tags for HIPAA compliance:

```yaml
ComplianceFramework: "hipaa"
DataClassification: "restricted"
PIIData: "true"
EncryptionRequired: "true"
SecurityZone: "restricted"
BackupSchedule: "daily"
```

## Environment-Specific Tag Examples

### Development Environment

```yaml
Environment: "dev"
Project: "devsecops-platform"
Owner: "platform-team"
CostCenter: "CC-1234"
Application: "data-ingestion"
Component: "lambda-processor"
CreatedBy: "cdk"
CreatedDate: "2024-01-15"
AutoShutdown: "nights"
MonitoringLevel: "basic"
BackupSchedule: "none"
```

### Staging Environment

```yaml
Environment: "staging"
Project: "devsecops-platform"
Owner: "platform-team"
CostCenter: "CC-1234"
Application: "data-ingestion"
Component: "lambda-processor"
CreatedBy: "cdk"
CreatedDate: "2024-01-15"
MonitoringLevel: "standard"
BackupSchedule: "daily"
BackupRetention: "7d"
SecurityReview: "approved"
```

### Production Environment

```yaml
Environment: "prod"
Project: "devsecops-platform"
Owner: "platform-team"
CostCenter: "CC-1234"
Application: "data-ingestion"
Component: "lambda-processor"
CreatedBy: "cdk"
CreatedDate: "2024-01-15"
DataClassification: "confidential"
EncryptionRequired: "true"
BackupSchedule: "daily"
BackupRetention: "30d"
DisasterRecovery: "critical"
MonitoringLevel: "enhanced"
SecurityReview: "approved"
ComplianceFramework: "sox"
```

## Resource-Specific Tagging Examples

### S3 Bucket (Data Storage)

```yaml
# Required tags
Environment: "prod"
Project: "devsecops-platform"
Owner: "data-team"
CostCenter: "CC-1234"
Application: "data-lake"
Component: "raw-storage"
CreatedBy: "cdk"
CreatedDate: "2024-01-15"

# Data-specific tags
DataClassification: "confidential"
DataRetention: "3y"
PIIData: "true"
EncryptionRequired: "true"
BackupSchedule: "daily"
BackupRetention: "90d"

# Compliance tags
ComplianceFramework: "gdpr"
SecurityReview: "approved"
```

### Lambda Function (Compute)

```yaml
# Required tags
Environment: "prod"
Project: "devsecops-platform"
Owner: "platform-team"
CostCenter: "CC-1234"
Application: "data-processing"
Component: "event-processor"
CreatedBy: "cdk"
CreatedDate: "2024-01-15"

# Operational tags
MonitoringLevel: "enhanced"
AlertingEnabled: "true"
ScalingPolicy: "moderate"
Version: "v1.2.3"
GitCommit: "abc1234"

# Security tags
SecurityZone: "internal"
VulnerabilityScanning: "required"
```

### RDS Database (Data Storage)

```yaml
# Required tags
Environment: "prod"
Project: "devsecops-platform"
Owner: "data-team"
CostCenter: "CC-1234"
Application: "user-management"
Component: "postgres-primary"
CreatedBy: "cdk"
CreatedDate: "2024-01-15"

# Data-specific tags
DataClassification: "restricted"
DataRetention: "7y"
PIIData: "true"
EncryptionRequired: "true"
BackupSchedule: "daily"
BackupRetention: "30d"
DisasterRecovery: "critical"
RPO: "1h"
RTO: "15m"

# Compliance tags
ComplianceFramework: "hipaa"
SecurityReview: "approved"
MaintenanceWindow: "sunday:02:00-04:00"
```

## Automation and Implementation

### CDK Implementation

```python
from infrastructure.constructs.common.conventions import ResourceTagging

# Initialize tagging utility
tagging = ResourceTagging(
    environment="prod",
    project="devsecops-platform",
    owner="platform-team",
    cost_center="CC-1234"
)

# Apply tags to S3 bucket
bucket_tags = tagging.get_tags(
    application="data-lake",
    component="raw-storage",
    data_classification="confidential",
    pii_data=True,
    compliance_framework="gdpr"
)

s3_bucket = s3.Bucket(
    self,
    "DataLakeBucket",
    bucket_name="dso-prod-data-lake-us-east-1",
    **bucket_tags
)
```

### Tag Inheritance

Child resources automatically inherit parent tags:

```python
# Parent VPC tags
vpc_tags = {
    "Environment": "prod",
    "Project": "devsecops-platform",
    "SecurityZone": "internal"
}

# Subnet inherits VPC tags plus specific tags
subnet_tags = {
    **vpc_tags,  # Inherited
    "Component": "private-subnet",
    "AvailabilityZone": "us-east-1a"
}
```

## Monitoring and Compliance

### Tag Compliance Monitoring

The platform automatically monitors for:
- Missing required tags
- Invalid tag values
- Untagged resources
- Tag drift detection
- Compliance violations

### Automated Remediation

- **Missing Tags**: Automatically apply default tags
- **Invalid Values**: Alert and require manual correction
- **Untagged Resources**: Quarantine until properly tagged
- **Compliance Violations**: Immediate security team notification

### Reporting and Dashboards

- **Cost Allocation**: Real-time cost breakdown by tags
- **Compliance Status**: Compliance framework adherence
- **Resource Inventory**: Complete tagged resource catalog
- **Tag Coverage**: Percentage of properly tagged resources

## Best Practices

1. **Consistency**: Use standardized tag keys and values
2. **Automation**: Leverage CDK constructs for automatic tagging
3. **Validation**: Validate all tags before resource creation
4. **Documentation**: Document any custom or exception tags
5. **Regular Audits**: Periodic review of tag compliance
6. **Training**: Ensure team understanding of tagging strategy
7. **Evolution**: Regular review and update of tagging strategy

## Tag Management Tools

### CLI Tools

```bash
# Validate resource tags
aws-tag-validator --resource-arn arn:aws:s3:::my-bucket

# Apply missing tags
aws-tag-applier --environment prod --dry-run

# Generate tag compliance report
aws-tag-reporter --format json --output compliance-report.json
```

### API Integration

```python
from infrastructure.constructs.common.conventions import TagValidator

validator = TagValidator()
is_compliant = validator.validate_resource_tags(resource_arn)
missing_tags = validator.get_missing_required_tags(resource_arn)
```

## Migration and Legacy Resources

For existing untagged resources:
1. **Discovery**: Identify all untagged resources
2. **Classification**: Determine appropriate tag values
3. **Batch Tagging**: Apply tags using automation tools
4. **Validation**: Verify tag compliance
5. **Monitoring**: Ongoing compliance monitoring

## Support and Governance

- **Tag Strategy Owner**: Platform Architecture Team
- **Compliance Review**: Monthly tag compliance audits
- **Exception Process**: RFC process for tag strategy changes
- **Training**: Quarterly tagging best practices sessions
- **Documentation**: Keep this document updated with changes
