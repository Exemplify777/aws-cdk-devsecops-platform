# Best Practices Guide

Comprehensive guide to best practices for using the DevSecOps Platform effectively, securely, and efficiently.

## Development Best Practices

### 1. Project Organization

#### Naming Conventions

```bash
# Project names: use kebab-case
customer-analytics-pipeline
fraud-detection-ml
real-time-streaming-etl

# Resource names: include environment and purpose
sales-data-bucket-dev
ml-model-endpoint-prod
analytics-lambda-staging
```

#### Directory Structure

```
my-project/
├── README.md                 # Project documentation
├── CHANGELOG.md              # Version history
├── .gitignore               # Git ignore patterns
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # Development dependencies
├── app.py                   # CDK application entry
├── cdk.json                 # CDK configuration
├── infrastructure/          # Infrastructure code
│   ├── stacks/             # CDK stacks
│   ├── constructs/         # Reusable constructs
│   └── config/             # Configuration files
├── src/                    # Application source code
│   ├── lambda/             # Lambda functions
│   ├── glue/               # Glue jobs
│   └── common/             # Shared utilities
├── tests/                  # Test files
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test data
├── docs/                   # Project documentation
├── scripts/                # Utility scripts
└── .github/workflows/      # CI/CD workflows
```

#### Documentation Standards

```markdown
# Project README Template

## Overview
Brief description of the project purpose and functionality.

## Architecture
High-level architecture diagram and component description.

## Getting Started
### Prerequisites
- List of required tools and dependencies
- AWS permissions required

### Installation
Step-by-step installation instructions

### Configuration
Environment variables and configuration options

## Usage
### Deployment
How to deploy the project

### Monitoring
How to monitor the project

### Troubleshooting
Common issues and solutions

## Contributing
Guidelines for contributing to the project
```

### 2. Code Quality

#### Python Code Standards

```python
# Use type hints
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

def process_data(
    input_data: List[Dict[str, Any]],
    config: Dict[str, str],
    dry_run: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Process input data according to configuration.
    
    Args:
        input_data: List of data records to process
        config: Configuration dictionary
        dry_run: If True, don't make actual changes
        
    Returns:
        Processing results or None if dry_run
        
    Raises:
        ValueError: If input_data is empty
        ConfigError: If configuration is invalid
    """
    if not input_data:
        raise ValueError("Input data cannot be empty")
    
    logger.info(f"Processing {len(input_data)} records")
    
    # Implementation here
    pass
```

#### Error Handling

```python
# Comprehensive error handling
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional

def safe_s3_operation(bucket: str, key: str) -> Optional[str]:
    """Safely perform S3 operation with proper error handling."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8')
        
    except NoCredentialsError:
        logger.error("AWS credentials not found")
        raise
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            logger.warning(f"Object {key} not found in bucket {bucket}")
            return None
        elif error_code == 'AccessDenied':
            logger.error(f"Access denied to {bucket}/{key}")
            raise
        else:
            logger.error(f"Unexpected error: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Unexpected error in S3 operation: {e}")
        raise
```

#### Testing Standards

```python
# Comprehensive test coverage
import pytest
from unittest.mock import Mock, patch
from moto import mock_s3
import boto3

class TestDataProcessor:
    """Test suite for data processor."""
    
    @pytest.fixture
    def sample_data(self):
        """Provide sample test data."""
        return [
            {"id": 1, "name": "test1", "value": 100},
            {"id": 2, "name": "test2", "value": 200}
        ]
    
    @pytest.fixture
    def config(self):
        """Provide test configuration."""
        return {
            "output_format": "json",
            "validation_enabled": "true"
        }
    
    def test_process_data_success(self, sample_data, config):
        """Test successful data processing."""
        result = process_data(sample_data, config)
        
        assert result is not None
        assert result['status'] == 'success'
        assert result['processed_count'] == 2
    
    def test_process_data_empty_input(self, config):
        """Test handling of empty input."""
        with pytest.raises(ValueError, match="Input data cannot be empty"):
            process_data([], config)
    
    @mock_s3
    def test_s3_integration(self):
        """Test S3 integration with moto."""
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        s3_client.put_object(
            Bucket='test-bucket',
            Key='test-key',
            Body='test content'
        )
        
        # Test the function
        result = safe_s3_operation('test-bucket', 'test-key')
        assert result == 'test content'
```

## Security Best Practices

### 1. Secrets Management

#### Never Hardcode Secrets

```python
# ❌ Bad: Hardcoded secrets
API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgresql://user:password@host:5432/db"

# ✅ Good: Use environment variables or Secrets Manager
import os
import boto3

def get_secret(secret_name: str) -> str:
    """Retrieve secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Use environment variables for non-sensitive config
API_ENDPOINT = os.getenv('API_ENDPOINT', 'https://api.example.com')
DATABASE_URL = get_secret('prod/database/url')
```

#### Secure Configuration

```python
# Use AWS Systems Manager Parameter Store
def get_parameter(parameter_name: str, encrypted: bool = True) -> str:
    """Get parameter from SSM Parameter Store."""
    ssm_client = boto3.client('ssm')
    response = ssm_client.get_parameter(
        Name=parameter_name,
        WithDecryption=encrypted
    )
    return response['Parameter']['Value']

# Configuration class
class Config:
    def __init__(self):
        self.api_key = get_secret('prod/api/key')
        self.database_url = get_parameter('/prod/database/url')
        self.debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
```

### 2. IAM Best Practices

#### Least Privilege Principle

```python
# ✅ Good: Specific permissions
lambda_policy = iam.PolicyDocument(
    statements=[
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject"
            ],
            resources=[
                f"{specific_bucket.bucket_arn}/data/*"
            ]
        ),
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["dynamodb:PutItem"],
            resources=[specific_table.table_arn]
        )
    ]
)

# ❌ Bad: Overly broad permissions
bad_policy = iam.PolicyDocument(
    statements=[
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["*"],
            resources=["*"]
        )
    ]
)
```

#### Role-Based Access Control

```python
# Define roles with specific purposes
developer_role = iam.Role(
    self,
    "DeveloperRole",
    assumed_by=iam.FederatedPrincipal(
        "arn:aws:iam::123456789012:saml-provider/ExampleProvider",
        conditions={
            "StringEquals": {
                "SAML:Role": "Developer"
            }
        }
    ),
    managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name("ReadOnlyAccess")
    ],
    inline_policies={
        "DevEnvironmentAccess": iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["*"],
                    resources=["*"],
                    conditions={
                        "StringEquals": {
                            "aws:RequestedRegion": "us-east-1"
                        },
                        "ForAllValues:StringLike": {
                            "aws:ResourceTag/Environment": "dev"
                        }
                    }
                )
            ]
        )
    }
)
```

### 3. Data Protection

#### Encryption Best Practices

```python
# Always encrypt sensitive data
s3.Bucket(
    self,
    "SensitiveDataBucket",
    encryption=s3.BucketEncryption.KMS,
    encryption_key=customer_managed_key,
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
    versioning=True,
    lifecycle_rules=[
        s3.LifecycleRule(
            noncurrent_version_expiration=Duration.days(30)
        )
    ]
)

# Use HTTPS for all communications
api_gateway.RestApi(
    self,
    "SecureAPI",
    endpoint_configuration=apigateway.EndpointConfiguration(
        types=[apigateway.EndpointType.REGIONAL]
    ),
    policy=iam.PolicyDocument(
        statements=[
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["execute-api:Invoke"],
                resources=["*"],
                conditions={
                    "Bool": {
                        "aws:SecureTransport": "false"
                    }
                }
            )
        ]
    )
)
```

## Deployment Best Practices

### 1. Environment Strategy

#### Environment Configuration

```yaml
# config/environments.yaml
environments:
  dev:
    account_id: "123456789012"
    region: "us-east-1"
    vpc_cidr: "10.0.0.0/16"
    instance_types:
      small: "t3.micro"
      medium: "t3.small"
    enable_deletion_protection: false
    backup_retention_days: 1
    
  staging:
    account_id: "123456789013"
    region: "us-east-1"
    vpc_cidr: "10.1.0.0/16"
    instance_types:
      small: "t3.small"
      medium: "t3.medium"
    enable_deletion_protection: true
    backup_retention_days: 7
    
  prod:
    account_id: "123456789014"
    region: "us-east-1"
    vpc_cidr: "10.2.0.0/16"
    instance_types:
      small: "t3.medium"
      medium: "t3.large"
    enable_deletion_protection: true
    backup_retention_days: 30
```

#### Deployment Pipeline

```bash
# Deployment workflow
# 1. Development
ddk-cli deploy --env dev --auto-approve

# 2. Automated testing
ddk-cli test --env dev --type unit
ddk-cli test --env dev --type integration

# 3. Security scanning
ddk-cli scan --env dev --type all

# 4. Staging deployment (manual approval)
ddk-cli deploy --env staging

# 5. Staging validation
ddk-cli test --env staging --type smoke
ddk-cli test --env staging --type performance

# 6. Production deployment (manual approval + security review)
ddk-cli deploy --env prod --approve
```

### 2. Infrastructure as Code

#### Modular Design

```python
# Reusable constructs
class DataLakeConstruct(Construct):
    """Reusable data lake construct."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)
        
        # Create buckets with consistent naming
        self.raw_bucket = self._create_bucket("raw", environment)
        self.processed_bucket = self._create_bucket("processed", environment)
        self.curated_bucket = self._create_bucket("curated", environment)
    
    def _create_bucket(self, zone: str, environment: str) -> s3.Bucket:
        """Create S3 bucket with standard configuration."""
        return s3.Bucket(
            self,
            f"{zone.title()}Bucket",
            bucket_name=f"{self.node.id}-{zone}-{environment}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioning=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        )
                    ]
                )
            ]
        )
```

#### Configuration Management

```python
# Environment-specific configuration
class EnvironmentConfig:
    def __init__(self, environment: str):
        self.environment = environment
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load environment-specific configuration."""
        config_file = f"config/{self.environment}.yaml"
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    @property
    def vpc_cidr(self) -> str:
        return self.config['vpc_cidr']
    
    @property
    def instance_types(self) -> Dict[str, str]:
        return self.config['instance_types']
    
    @property
    def enable_deletion_protection(self) -> bool:
        return self.config.get('enable_deletion_protection', True)
```

## Monitoring Best Practices

### 1. Observability Strategy

#### Three Pillars Implementation

```python
# Metrics
custom_metric = cloudwatch.Metric(
    namespace="Application/DataPipeline",
    metric_name="ProcessedRecords",
    dimensions_map={
        "Environment": environment,
        "Pipeline": pipeline_name
    }
)

# Logs
log_group = logs.LogGroup(
    self,
    "ApplicationLogs",
    log_group_name=f"/aws/lambda/{function_name}",
    retention=logs.RetentionDays.ONE_MONTH
)

# Traces
lambda_.Function(
    self,
    "TracedFunction",
    tracing=lambda_.Tracing.ACTIVE,
    environment={
        "_X_AMZN_TRACE_ID": "Root=1-5e1b4151-5ac6c58dc39a6b6b1a4c8c5e"
    }
)
```

#### Alerting Strategy

```python
# Tiered alerting
class AlertingTiers:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

def create_alarm(
    metric: cloudwatch.Metric,
    threshold: float,
    tier: str,
    description: str
) -> cloudwatch.Alarm:
    """Create alarm with appropriate notification."""
    
    alarm_actions = []
    if tier == AlertingTiers.CRITICAL:
        alarm_actions.extend([
            pagerduty_topic,
            slack_critical_topic,
            email_topic
        ])
    elif tier == AlertingTiers.WARNING:
        alarm_actions.extend([
            slack_warning_topic,
            email_topic
        ])
    else:
        alarm_actions.append(email_topic)
    
    return cloudwatch.Alarm(
        self,
        f"Alarm{tier.title()}",
        metric=metric,
        threshold=threshold,
        evaluation_periods=2,
        alarm_description=description,
        alarm_actions=alarm_actions
    )
```

### 2. Performance Monitoring

#### Key Performance Indicators

```python
# Business KPIs
business_metrics = [
    "RecordsProcessedPerHour",
    "DataQualityScore",
    "PipelineSuccessRate",
    "CostPerRecord",
    "TimeToInsight"
]

# Technical KPIs
technical_metrics = [
    "LambdaExecutionDuration",
    "GlueJobExecutionTime",
    "S3RequestLatency",
    "DatabaseConnectionTime",
    "ErrorRate"
]

# Create dashboard with all KPIs
dashboard = cloudwatch.Dashboard(
    self,
    "KPIDashboard",
    dashboard_name=f"{project_name}-kpis"
)

for metric_name in business_metrics + technical_metrics:
    dashboard.add_widgets(
        cloudwatch.GraphWidget(
            title=metric_name,
            left=[
                cloudwatch.Metric(
                    namespace="Application/DataPipeline",
                    metric_name=metric_name
                )
            ]
        )
    )
```

## Cost Optimization Best Practices

### 1. Resource Right-Sizing

#### Environment-Specific Sizing

```python
# Environment-specific instance types
instance_config = {
    "dev": {
        "lambda_memory": 128,
        "rds_instance": "db.t3.micro",
        "ecs_cpu": 256,
        "ecs_memory": 512
    },
    "staging": {
        "lambda_memory": 512,
        "rds_instance": "db.t3.small",
        "ecs_cpu": 512,
        "ecs_memory": 1024
    },
    "prod": {
        "lambda_memory": 1024,
        "rds_instance": "db.t3.medium",
        "ecs_cpu": 1024,
        "ecs_memory": 2048
    }
}

# Use configuration in resources
lambda_.Function(
    self,
    "OptimizedFunction",
    memory_size=instance_config[environment]["lambda_memory"],
    timeout=Duration.minutes(5 if environment == "prod" else 1)
)
```

#### Auto-Scaling Configuration

```python
# Intelligent auto-scaling
scalable_target = ecs_service.auto_scale_task_count(
    min_capacity=1 if environment == "dev" else 2,
    max_capacity=5 if environment == "dev" else 20
)

# Scale based on multiple metrics
scalable_target.scale_on_cpu_utilization(
    "CpuScaling",
    target_utilization_percent=70,
    scale_in_cooldown=Duration.minutes(5),
    scale_out_cooldown=Duration.minutes(1)
)

scalable_target.scale_on_memory_utilization(
    "MemoryScaling",
    target_utilization_percent=80
)

# Custom metric scaling
scalable_target.scale_on_metric(
    "QueueScaling",
    metric=cloudwatch.Metric(
        namespace="AWS/SQS",
        metric_name="ApproximateNumberOfMessages",
        dimensions_map={"QueueName": queue.queue_name}
    ),
    scaling_steps=[
        autoscaling.ScalingInterval(upper=0, change=0),
        autoscaling.ScalingInterval(lower=1, change=+1),
        autoscaling.ScalingInterval(lower=50, change=+5)
    ]
)
```

### 2. Storage Optimization

#### S3 Lifecycle Policies

```python
# Intelligent tiering and lifecycle
s3.Bucket(
    self,
    "OptimizedBucket",
    intelligent_tiering_configurations=[
        s3.IntelligentTieringConfiguration(
            name="EntireBucket",
            prefix="",
            archive_access_tier_time=Duration.days(90),
            deep_archive_access_tier_time=Duration.days(180)
        )
    ],
    lifecycle_rules=[
        s3.LifecycleRule(
            id="DataLifecycle",
            enabled=True,
            transitions=[
                s3.Transition(
                    storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                    transition_after=Duration.days(30)
                ),
                s3.Transition(
                    storage_class=s3.StorageClass.GLACIER,
                    transition_after=Duration.days(90)
                ),
                s3.Transition(
                    storage_class=s3.StorageClass.DEEP_ARCHIVE,
                    transition_after=Duration.days(365)
                )
            ],
            expiration=Duration.days(2555),  # 7 years
            noncurrent_version_expiration=Duration.days(30)
        )
    ]
)
```

## Team Collaboration Best Practices

### 1. Git Workflow

#### Branch Strategy

```bash
# Feature branch workflow
git checkout -b feature/new-data-source
# Make changes
git add .
git commit -m "feat: add new data source integration"
git push origin feature/new-data-source
# Create pull request

# Hotfix workflow
git checkout -b hotfix/critical-bug
# Fix the issue
git add .
git commit -m "fix: resolve critical data processing bug"
git push origin hotfix/critical-bug
# Create pull request to main and develop
```

#### Commit Message Standards

```bash
# Use conventional commits
feat: add new ML model training pipeline
fix: resolve S3 permission issue in data processor
docs: update API documentation
test: add integration tests for data validation
refactor: optimize Lambda function memory usage
chore: update dependencies to latest versions
```

### 2. Code Review Process

#### Review Checklist

```markdown
## Code Review Checklist

### Functionality
- [ ] Code accomplishes the intended purpose
- [ ] Edge cases are handled appropriately
- [ ] Error handling is comprehensive

### Security
- [ ] No hardcoded secrets or credentials
- [ ] Input validation is implemented
- [ ] Proper authentication and authorization

### Performance
- [ ] Code is efficient and optimized
- [ ] Resource usage is appropriate
- [ ] Caching is used where beneficial

### Maintainability
- [ ] Code is readable and well-documented
- [ ] Functions are appropriately sized
- [ ] Naming conventions are followed

### Testing
- [ ] Unit tests are included
- [ ] Test coverage is adequate
- [ ] Integration tests are provided where needed
```

## Troubleshooting Best Practices

### 1. Debugging Strategy

#### Structured Logging

```python
import logging
import json
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def log_structured(level: str, message: str, **kwargs):
    """Log structured data for better searchability."""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "message": message,
        "context": kwargs
    }
    
    if level == "ERROR":
        logger.error(json.dumps(log_data))
    elif level == "WARNING":
        logger.warning(json.dumps(log_data))
    else:
        logger.info(json.dumps(log_data))

# Usage
log_structured(
    "INFO",
    "Processing data batch",
    batch_id="batch_123",
    record_count=1000,
    environment="prod"
)
```

#### Error Tracking

```python
# Comprehensive error tracking
import traceback
from typing import Optional

class ErrorTracker:
    def __init__(self, context: Dict[str, Any]):
        self.context = context
    
    def track_error(
        self,
        error: Exception,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Track error with full context."""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": self.context
        }
        
        if additional_context:
            error_data["additional_context"] = additional_context
        
        # Log error
        logger.error(json.dumps(error_data))
        
        # Send to monitoring system
        self._send_to_monitoring(error_data)
    
    def _send_to_monitoring(self, error_data: Dict[str, Any]):
        """Send error data to monitoring system."""
        # Implementation for sending to CloudWatch, Datadog, etc.
        pass
```

For more detailed information, see:
- [Security Best Practices](../security/overview.md)
- [Deployment Guide](../operations/deployment.md)
- [Monitoring Guide](../operations/monitoring.md)
- [Troubleshooting Guide](../operations/troubleshooting.md)
