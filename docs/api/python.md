# Python API Reference

Complete reference for the DevSecOps Platform Python SDK and libraries.

## Installation

```bash
pip install ddk-platform
# or for development
pip install -e .
```

## Core Modules

### `platform.cli`

CLI functionality and command implementations.

#### `platform.cli.config.CLIConfig`

Configuration management for the CLI.

```python
from platform.cli.config import CLIConfig

# Load configuration
config = CLIConfig()

# Get configuration value
aws_region = config.get('aws.region', 'us-east-1')

# Set configuration value
config.set('aws.region', 'us-west-2')

# Save configuration
config.save()
```

**Methods:**

- `get(key: str, default: Any = None) -> Any`: Get configuration value
- `set(key: str, value: Any) -> None`: Set configuration value
- `save() -> None`: Save configuration to file
- `load() -> None`: Load configuration from file
- `reset() -> None`: Reset configuration to defaults

#### `platform.cli.aws.AWSManager`

AWS integration and deployment management.

```python
from platform.cli.aws import AWSManager

# Initialize AWS manager
aws_manager = AWSManager(
    region='us-east-1',
    profile='default'
)

# Deploy project
result = aws_manager.deploy_project(
    project_name='my-pipeline',
    environment='dev',
    auto_approve=False
)

# Get project status
status = aws_manager.get_project_status(
    project_name='my-pipeline',
    environment='dev'
)
```

**Methods:**

- `deploy_project(project_name: str, environment: str, **kwargs) -> Dict[str, Any]`
- `destroy_project(project_name: str, environment: str, **kwargs) -> Dict[str, Any]`
- `get_project_status(project_name: str, environment: str) -> Dict[str, Any]`
- `list_projects(environment: str = None) -> List[Dict[str, Any]]`
- `get_logs(project_name: str, environment: str, **kwargs) -> List[str]`

#### `platform.cli.templates.TemplateManager`

Project template management.

```python
from platform.cli.templates import TemplateManager

# Initialize template manager
template_manager = TemplateManager()

# List available templates
templates = template_manager.list_templates()

# Create project from template
template_manager.create_project(
    project_name='my-pipeline',
    template_name='data-pipeline',
    output_dir='./projects',
    context={'author': 'John Doe'}
)
```

**Methods:**

- `list_templates() -> List[Dict[str, Any]]`
- `get_template(name: str) -> Dict[str, Any]`
- `create_project(project_name: str, template_name: str, **kwargs) -> None`
- `validate_template(template_path: str) -> bool`

### `infrastructure.config`

Infrastructure configuration and settings.

#### `infrastructure.config.settings.Settings`

Platform configuration settings.

```python
from infrastructure.config.settings import Settings, get_settings

# Get settings instance
settings = get_settings()

# Access configuration
aws_region = settings.aws_region
vpc_cidr = settings.vpc_cidr
environment_config = settings.get_environment_config()
```

**Properties:**

- `project_name: str`: Project name
- `aws_region: str`: AWS region
- `vpc_cidr: str`: VPC CIDR block
- `availability_zones: List[str]`: Availability zones
- `environment: str`: Current environment

**Methods:**

- `get_environment_config() -> Dict[str, Any]`: Get environment-specific configuration

### `security.scanner`

Security scanning functionality.

#### `security.scanner.SecurityScanner`

Comprehensive security scanning.

```python
from security.scanner import SecurityScanner

# Initialize scanner
scanner = SecurityScanner()

# Run comprehensive scan
results = scanner.scan_all(
    path='.',
    output_format='json'
)

# Run specific scan types
code_results = scanner.scan_code('.')
dependency_results = scanner.scan_dependencies('.')
secrets_results = scanner.scan_secrets('.')
```

**Methods:**

- `scan_all(path: str, **kwargs) -> Dict[str, Any]`
- `scan_code(path: str, **kwargs) -> Dict[str, Any]`
- `scan_dependencies(path: str, **kwargs) -> Dict[str, Any]`
- `scan_secrets(path: str, **kwargs) -> Dict[str, Any]`
- `scan_infrastructure(path: str, **kwargs) -> Dict[str, Any]`

#### Security Scanning Functions

```python
from security.scanner import (
    run_bandit,
    run_semgrep,
    run_safety,
    scan_secrets,
    calculate_summary
)

# Run individual scanners
bandit_results = run_bandit(path='.')
semgrep_results = run_semgrep(path='.')
safety_results = run_safety(path='.')

# Calculate summary
summary = calculate_summary(results)
```

### `security.compliance`

Compliance checking and validation.

#### `security.compliance.ComplianceChecker`

Multi-framework compliance checking.

```python
from security.compliance import ComplianceChecker

# Initialize compliance checker
checker = ComplianceChecker()

# Check SOC 2 compliance
soc2_results = checker.check_compliance(
    path='.',
    framework='SOC2'
)

# Check multiple frameworks
results = checker.check_multiple_frameworks(
    path='.',
    frameworks=['SOC2', 'ISO27001', 'GDPR']
)

# Generate compliance report
report = checker.generate_report(
    results,
    format='html',
    output_path='compliance-report.html'
)
```

**Methods:**

- `check_compliance(path: str, framework: str) -> Dict[str, Any]`
- `check_multiple_frameworks(path: str, frameworks: List[str]) -> Dict[str, Any]`
- `generate_report(results: Dict, format: str, output_path: str) -> str`
- `validate_rules(rules_path: str) -> bool`

## CDK Constructs

### `infrastructure.constructs`

Reusable CDK constructs for common patterns.

#### `infrastructure.constructs.data_lake.DataLakeConstruct`

Data lake construct with multiple zones.

```python
from aws_cdk import Stack
from infrastructure.constructs.data_lake import DataLakeConstruct

class MyStack(Stack):
    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Create data lake
        data_lake = DataLakeConstruct(
            self,
            "DataLake",
            environment="dev",
            enable_lifecycle_rules=True
        )
        
        # Access buckets
        raw_bucket = data_lake.raw_bucket
        processed_bucket = data_lake.processed_bucket
        curated_bucket = data_lake.curated_bucket
```

**Properties:**

- `raw_bucket: s3.Bucket`: Raw data bucket
- `processed_bucket: s3.Bucket`: Processed data bucket
- `curated_bucket: s3.Bucket`: Curated data bucket
- `database: glue.CfnDatabase`: Glue database
- `glue_role: iam.Role`: Glue service role

#### `infrastructure.constructs.monitoring.MonitoringConstruct`

Monitoring and alerting construct.

```python
from infrastructure.constructs.monitoring import MonitoringConstruct

# Create monitoring
monitoring = MonitoringConstruct(
    self,
    "Monitoring",
    project_name="my-pipeline",
    environment="dev",
    notification_email="alerts@company.com"
)

# Access components
dashboard = monitoring.dashboard
alarm_topic = monitoring.alarm_topic
```

**Properties:**

- `dashboard: cloudwatch.Dashboard`: CloudWatch dashboard
- `alarm_topic: sns.Topic`: SNS topic for alarms
- `log_group: logs.LogGroup`: CloudWatch log group

## Utilities

### `platform.utils`

Common utility functions.

#### File Operations

```python
from platform.utils.files import (
    read_yaml,
    write_yaml,
    read_json,
    write_json,
    ensure_directory
)

# Read YAML file
config = read_yaml('config.yaml')

# Write JSON file
write_json('output.json', data)

# Ensure directory exists
ensure_directory('./output')
```

#### AWS Utilities

```python
from platform.utils.aws import (
    get_account_id,
    get_region,
    assume_role,
    get_caller_identity
)

# Get current account ID
account_id = get_account_id()

# Get current region
region = get_region()

# Assume role
credentials = assume_role(
    role_arn='arn:aws:iam::123456789012:role/MyRole',
    session_name='my-session'
)
```

#### Validation Utilities

```python
from platform.utils.validation import (
    validate_project_name,
    validate_environment,
    validate_aws_region,
    validate_email
)

# Validate project name
is_valid = validate_project_name('my-pipeline')

# Validate environment
is_valid = validate_environment('dev')
```

## Error Handling

### Custom Exceptions

```python
from platform.exceptions import (
    PlatformError,
    ConfigurationError,
    DeploymentError,
    ValidationError,
    SecurityError
)

try:
    # Platform operation
    result = deploy_project(name, env)
except DeploymentError as e:
    print(f"Deployment failed: {e}")
    print(f"Suggestions: {e.suggestions}")
except ValidationError as e:
    print(f"Validation failed: {e}")
    print(f"Details: {e.details}")
```

### Error Context

```python
from platform.utils.errors import ErrorContext

with ErrorContext("Deploying project"):
    # Operations that might fail
    deploy_infrastructure()
    configure_monitoring()
    validate_deployment()
```

## Configuration

### Environment Configuration

```python
from infrastructure.config.settings import get_settings

settings = get_settings()

# Environment-specific configuration
env_config = settings.get_environment_config()

# Access configuration values
vpc_cidr = env_config['vpc_cidr']
instance_types = env_config['instance_types']
enable_backup = env_config['enable_backup']
```

### Feature Flags

```python
from platform.utils.features import FeatureFlags

flags = FeatureFlags()

if flags.is_enabled('ai_tools'):
    # AI tools functionality
    pass

if flags.is_enabled('advanced_monitoring'):
    # Advanced monitoring
    pass
```

## Testing

### Test Utilities

```python
from platform.testing import (
    MockAWSManager,
    MockTemplateManager,
    create_test_config,
    create_test_project
)

# Mock AWS manager for testing
aws_manager = MockAWSManager()

# Create test configuration
config = create_test_config({
    'aws.region': 'us-east-1',
    'github.organization': 'test-org'
})

# Create test project
project = create_test_project(
    name='test-project',
    template='data-pipeline'
)
```

### CDK Testing

```python
from aws_cdk import App, Template
from infrastructure.stacks.core_infrastructure_stack import CoreInfrastructureStack

# Test CDK stack
app = App()
stack = CoreInfrastructureStack(
    app,
    "TestStack",
    env_config={'environment_name': 'test'}
)

template = Template.from_stack(stack)

# Assert resources exist
template.has_resource_properties("AWS::S3::Bucket", {
    "BucketEncryption": {
        "ServerSideEncryptionConfiguration": [
            {
                "ServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }
        ]
    }
})
```

## Examples

### Complete Project Deployment

```python
from platform.cli.aws import AWSManager
from platform.cli.config import CLIConfig
from infrastructure.config.settings import get_settings

# Load configuration
config = CLIConfig()
settings = get_settings()

# Initialize AWS manager
aws_manager = AWSManager(
    region=settings.aws_region,
    profile=config.get('aws.profile')
)

# Deploy project
result = aws_manager.deploy_project(
    project_name='my-pipeline',
    environment='dev',
    auto_approve=False
)

if result['success']:
    print("Deployment successful!")
    print(f"Outputs: {result['outputs']}")
else:
    print(f"Deployment failed: {result['error']}")
```

### Security Scanning

```python
from security.scanner import SecurityScanner
from security.compliance import ComplianceChecker

# Run security scan
scanner = SecurityScanner()
scan_results = scanner.scan_all('.')

# Check compliance
checker = ComplianceChecker()
compliance_results = checker.check_compliance('.', 'SOC2')

# Generate combined report
if scan_results['summary']['risk_level'] == 'HIGH':
    print("High security risk detected!")
    
if compliance_results['compliant']:
    print("SOC 2 compliance check passed")
else:
    print(f"Compliance issues: {compliance_results['violations']}")
```
