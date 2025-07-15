# API Reference

Complete API reference for the DevSecOps Platform, including CLI, Python SDK, and REST APIs.

## Overview

The DevSecOps Platform provides multiple APIs for different use cases:

- **[CLI API](cli.md)**: Command-line interface for developers and operators
- **[Python API](python.md)**: Python SDK for programmatic access and automation
- **[REST API](rest.md)**: HTTP REST API for web applications and integrations

## Quick Start

### CLI API

Install and use the CLI:

```bash
# Install CLI
pip install ddk-cli

# Initialize configuration
ddk-cli init

# Create a project
ddk-cli create-project my-pipeline --template data-pipeline

# Deploy project
ddk-cli deploy --env dev
```

### Python API

Use the Python SDK:

```python
from platform.cli.aws import AWSManager
from platform.cli.templates import TemplateManager

# Create project from template
template_manager = TemplateManager()
template_manager.create_project(
    project_name='my-pipeline',
    template_name='data-pipeline',
    output_dir='./projects'
)

# Deploy project
aws_manager = AWSManager(region='us-east-1')
result = aws_manager.deploy_project(
    project_name='my-pipeline',
    environment='dev'
)
```

### REST API

Access via HTTP:

```bash
# List projects
curl -X GET \
  https://api.devsecops-platform.company.com/v1/projects \
  -H "X-API-Key: your-api-key"

# Create project
curl -X POST \
  https://api.devsecops-platform.company.com/v1/projects \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "my-pipeline",
    "template": "data-pipeline",
    "environment": "dev"
  }'
```

## Authentication

### CLI Authentication

The CLI uses AWS credentials and configuration:

```bash
# Configure AWS credentials
aws configure

# Or use environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1
```

### Python SDK Authentication

The Python SDK inherits AWS credentials from the environment:

```python
import boto3
from platform.cli.aws import AWSManager

# Use default credentials
aws_manager = AWSManager()

# Use specific profile
aws_manager = AWSManager(profile='my-profile')

# Use explicit credentials
aws_manager = AWSManager(
    access_key_id='your-access-key',
    secret_access_key='your-secret-key',
    region='us-east-1'
)
```

### REST API Authentication

The REST API supports multiple authentication methods:

```bash
# AWS IAM Signature v4
curl --aws-sigv4 "aws:amz:us-east-1:execute-api" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
  https://api.devsecops-platform.company.com/v1/projects

# API Key
curl -H "X-API-Key: your-api-key" \
  https://api.devsecops-platform.company.com/v1/projects

# Bearer Token (JWT)
curl -H "Authorization: Bearer your-jwt-token" \
  https://api.devsecops-platform.company.com/v1/projects
```

## Common Patterns

### Project Lifecycle

Complete project lifecycle using different APIs:

#### CLI Approach

```bash
# 1. Create project
ddk-cli create-project sales-pipeline --template data-pipeline

# 2. Deploy to development
cd sales-pipeline
ddk-cli deploy --env dev

# 3. Run tests
ddk-cli test --env dev

# 4. Deploy to staging
ddk-cli deploy --env staging

# 5. Deploy to production
ddk-cli deploy --env prod --approve
```

#### Python SDK Approach

```python
from platform.cli.templates import TemplateManager
from platform.cli.aws import AWSManager

# 1. Create project
template_manager = TemplateManager()
template_manager.create_project(
    project_name='sales-pipeline',
    template_name='data-pipeline'
)

# 2. Deploy to development
aws_manager = AWSManager()
result = aws_manager.deploy_project(
    project_name='sales-pipeline',
    environment='dev'
)

# 3. Check status
status = aws_manager.get_project_status(
    project_name='sales-pipeline',
    environment='dev'
)

# 4. Deploy to staging
if status['health'] == 'healthy':
    aws_manager.deploy_project(
        project_name='sales-pipeline',
        environment='staging'
    )
```

#### REST API Approach

```bash
# 1. Create project
curl -X POST \
  https://api.devsecops-platform.company.com/v1/projects \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "sales-pipeline",
    "template": "data-pipeline",
    "environment": "dev"
  }'

# 2. Check deployment status
curl -X GET \
  https://api.devsecops-platform.company.com/v1/projects/sales-pipeline/deployments \
  -H "X-API-Key: your-api-key"

# 3. Deploy to staging
curl -X POST \
  https://api.devsecops-platform.company.com/v1/projects/sales-pipeline/deployments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"environment": "staging"}'
```

### Security and Compliance

Security scanning and compliance checking:

#### CLI

```bash
# Run security scan
ddk-cli scan my-project --type all

# Check compliance
ddk-cli compliance my-project --framework SOC2

# Generate report
ddk-cli compliance my-project --framework SOC2 --output report.html
```

#### Python SDK

```python
from security.scanner import SecurityScanner
from security.compliance import ComplianceChecker

# Security scanning
scanner = SecurityScanner()
results = scanner.scan_all('.')

# Compliance checking
checker = ComplianceChecker()
compliance_results = checker.check_compliance('.', 'SOC2')

# Generate report
report = checker.generate_report(
    compliance_results,
    format='html',
    output_path='compliance-report.html'
)
```

#### REST API

```bash
# Start security scan
curl -X POST \
  https://api.devsecops-platform.company.com/v1/projects/my-project/security/scan \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"scan_types": ["code", "dependencies", "secrets"]}'

# Check compliance
curl -X POST \
  https://api.devsecops-platform.company.com/v1/projects/my-project/compliance/check \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"frameworks": ["SOC2", "ISO27001"]}'
```

### Monitoring and Observability

Monitoring project health and performance:

#### CLI

```bash
# Check project status
ddk-cli status my-project --env prod

# View metrics
ddk-cli metrics my-project --env prod

# Stream logs
ddk-cli logs my-project --env prod --follow
```

#### Python SDK

```python
from platform.cli.aws import AWSManager

aws_manager = AWSManager()

# Get project status
status = aws_manager.get_project_status('my-project', 'prod')

# Get metrics
metrics = aws_manager.get_metrics('my-project', 'prod')

# Get logs
logs = aws_manager.get_logs('my-project', 'prod', follow=True)
```

#### REST API

```bash
# Get project metrics
curl -X GET \
  "https://api.devsecops-platform.company.com/v1/projects/my-project/metrics?environment=prod" \
  -H "X-API-Key: your-api-key"

# Get project logs
curl -X GET \
  "https://api.devsecops-platform.company.com/v1/projects/my-project/logs?environment=prod&follow=true" \
  -H "X-API-Key: your-api-key"
```

## Error Handling

### CLI Error Handling

The CLI provides detailed error messages and suggestions:

```bash
$ ddk-cli deploy non-existent-project
Error: Project 'non-existent-project' not found.

Suggestions:
  - Check the project name spelling
  - Use 'ddk-cli list-projects' to see available projects
  - Create the project with 'ddk-cli create-project'
```

### Python SDK Error Handling

Use try-catch blocks for error handling:

```python
from platform.exceptions import DeploymentError, ValidationError

try:
    result = aws_manager.deploy_project('my-project', 'dev')
except DeploymentError as e:
    print(f"Deployment failed: {e}")
    print(f"Suggestions: {e.suggestions}")
except ValidationError as e:
    print(f"Validation failed: {e}")
    print(f"Details: {e.details}")
```

### REST API Error Handling

REST API returns structured error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid project name",
    "details": {
      "field": "name",
      "reason": "Project name must be alphanumeric with hyphens"
    },
    "request_id": "req_123456789"
  }
}
```

## Rate Limits

### CLI Rate Limits

CLI operations are subject to AWS API rate limits. The CLI automatically handles retries with exponential backoff.

### Python SDK Rate Limits

The Python SDK includes built-in rate limiting and retry logic:

```python
from platform.utils.rate_limiting import RateLimiter

# Configure rate limiting
rate_limiter = RateLimiter(requests_per_second=10)

with rate_limiter:
    result = aws_manager.deploy_project('my-project', 'dev')
```

### REST API Rate Limits

REST API requests are rate limited:

- **Authenticated requests**: 1000 requests per hour
- **Unauthenticated requests**: 100 requests per hour

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642262400
```

## Versioning

### API Versioning

All APIs follow semantic versioning:

- **CLI**: Version specified in package (`ddk-cli==1.0.0`)
- **Python SDK**: Version specified in package (`ddk-platform==1.0.0`)
- **REST API**: Version specified in URL (`/v1/projects`)

### Backward Compatibility

- **Major versions**: May include breaking changes
- **Minor versions**: New features, backward compatible
- **Patch versions**: Bug fixes, backward compatible

## SDKs and Libraries

### Official SDKs

- **Python SDK**: Complete Python SDK with all platform features
- **CLI**: Command-line interface built on Python SDK
- **REST API**: HTTP REST API for any programming language

### Community SDKs

Community-maintained SDKs:

- **JavaScript/Node.js**: Community-maintained SDK
- **Go**: Community-maintained SDK
- **Java**: Community-maintained SDK

### Creating Custom SDKs

Use the REST API to create SDKs for other languages:

1. **Authentication**: Implement API key or AWS signature authentication
2. **HTTP Client**: Create HTTP client with proper error handling
3. **Models**: Define data models for API requests and responses
4. **Methods**: Implement methods for each API endpoint
5. **Testing**: Create comprehensive test suite

## Examples and Tutorials

### Getting Started

- [CLI Quick Start](../getting-started/quickstart.md)
- [Python SDK Tutorial](../tutorials/python-sdk.md)
- [REST API Tutorial](../tutorials/rest-api.md)

### Advanced Usage

- [Custom Templates](../user-guide/templates.md)
- [Security Integration](../security/scanning.md)
- [Monitoring Setup](../operations/monitoring.md)

### Integration Examples

- [CI/CD Integration](../operations/cicd.md)
- [Terraform Integration](../developer-guide/terraform.md)
- [Kubernetes Integration](../developer-guide/kubernetes.md)

## Support

### Documentation

- **API Reference**: Complete API documentation
- **Tutorials**: Step-by-step tutorials and examples
- **Best Practices**: Recommended patterns and practices

### Community

- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community discussions and Q&A
- **Slack Channel**: Real-time community support

### Enterprise Support

- **Professional Services**: Implementation and consulting
- **Training**: Custom training programs
- **Support Plans**: Dedicated support with SLAs

For detailed API documentation, see the individual API reference pages:

- **[CLI API Reference](cli.md)**
- **[Python API Reference](python.md)**
- **[REST API Reference](rest.md)**
