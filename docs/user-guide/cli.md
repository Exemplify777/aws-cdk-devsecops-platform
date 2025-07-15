# CLI User Guide

Complete guide for using the DevSecOps Platform CLI (`ddk-cli`) for day-to-day development and operations.

## Overview

The `ddk-cli` is a powerful command-line interface that provides:

- **Project Management**: Create, deploy, and manage data pipeline projects
- **Environment Management**: Deploy across multiple environments (dev, staging, prod)
- **Security Integration**: Built-in security scanning and compliance checking
- **Monitoring**: Real-time status monitoring and log streaming
- **Template System**: Extensible project templates for common patterns

## Installation

### Prerequisites

- Python 3.9 or higher
- AWS CLI configured with appropriate credentials
- Node.js 18+ (for CDK)

### Install CLI

```bash
# Install from PyPI (when available)
pip install ddk-cli

# Or install from source
git clone https://github.com/your-org/mcp-cdk-ddk.git
cd mcp-cdk-ddk
pip install -e .
```

### Verify Installation

```bash
ddk-cli --version
ddk-cli --help
```

## Initial Setup

### Configure CLI

Run the interactive setup to configure your CLI:

```bash
ddk-cli init
```

This will prompt you for:
- AWS region and account IDs
- GitHub organization (optional)
- Default project template
- Notification preferences

### Manual Configuration

Alternatively, create the configuration file manually:

```bash
mkdir -p ~/.ddk
cat > ~/.ddk/config.yaml << EOF
aws:
  region: us-east-1
  profile: default
  dev_account_id: "123456789012"
  staging_account_id: "123456789013"
  prod_account_id: "123456789014"

github:
  organization: my-org
  token: ghp_xxxxxxxxxxxx

templates:
  default_template: data-pipeline

security:
  enable_scanning: true
  scan_on_deploy: true
EOF
```

## Working with Projects

### Create a New Project

Create a project from a template:

```bash
# Create basic data pipeline
ddk-cli create-project sales-analytics --template data-pipeline

# Create with specific options
ddk-cli create-project ml-model \
  --template ml-workflow \
  --env dev \
  --github \
  --deploy
```

### List Available Templates

```bash
ddk-cli templates
```

Output:
```
📋 Available Project Templates:

┌─────────────────┬─────────────────────────────────────────┬──────────────┐
│ Template        │ Description                             │ Type         │
├─────────────────┼─────────────────────────────────────────┼──────────────┤
│ data-pipeline   │ ETL/ELT data processing pipeline        │ Data         │
│ ml-workflow     │ Machine learning training pipeline      │ ML/AI        │
│ streaming       │ Real-time data streaming pipeline       │ Streaming    │
│ api-service     │ REST API service with database         │ Service      │
└─────────────────┴─────────────────────────────────────────┴──────────────┘
```

### Project Structure

After creating a project, you'll have this structure:

```
my-project/
├── README.md                 # Project documentation
├── app.py                    # CDK application entry point
├── cdk.json                  # CDK configuration
├── requirements.txt          # Python dependencies
├── infrastructure/           # CDK infrastructure code
│   ├── stacks/              # CDK stacks
│   └── constructs/          # Reusable constructs
├── src/                     # Source code
│   ├── lambda/              # Lambda functions
│   ├── glue/                # Glue jobs
│   └── step_functions/      # Step Functions definitions
├── tests/                   # Test files
├── data/                    # Sample data
└── .github/workflows/       # CI/CD workflows
```

## Deployment

### Deploy to Development

```bash
cd my-project
ddk-cli deploy --env dev
```

### Deploy with Options

```bash
# Deploy specific stack
ddk-cli deploy --env dev --stack DataPipelineStack

# Deploy with auto-approval
ddk-cli deploy --env dev --approve

# Deploy with rollback disabled
ddk-cli deploy --env dev --no-rollback
```

### Multi-Environment Deployment

```bash
# Deploy to staging (requires manual approval)
ddk-cli deploy --env staging

# Deploy to production (requires security review)
ddk-cli deploy --env prod --approve
```

## Monitoring and Management

### Check Project Status

```bash
# Basic status
ddk-cli status my-project --env dev

# Detailed status with health checks
ddk-cli status my-project --env dev --detailed

# Watch status in real-time
ddk-cli status my-project --env dev --watch
```

Example output:
```
📊 Project Status: sales-analytics (dev)

┌─────────────────────┬─────────────────┬─────────────────────┐
│ Stack               │ Status          │ Last Updated        │
├─────────────────────┼─────────────────┼─────────────────────┤
│ CoreInfrastructure  │ CREATE_COMPLETE │ 2024-01-15 10:30:00 │
│ DataPipelineStack   │ CREATE_COMPLETE │ 2024-01-15 10:35:00 │
│ MonitoringStack     │ CREATE_COMPLETE │ 2024-01-15 10:40:00 │
└─────────────────────┴─────────────────┴─────────────────────┘

🏥 Health Checks:
✅ Lambda Functions: 3 functions healthy
✅ S3 Buckets: 2 buckets accessible
✅ Glue Jobs: 1 job ready
✅ Step Functions: 1 state machine active

💰 Cost Information:
Current Month: $45.67
Projected Month: $52.34
Budget Alert: 45% of $100 budget used
```

### View Logs

```bash
# View recent logs
ddk-cli logs my-project --env dev

# Follow logs in real-time
ddk-cli logs my-project --env dev --follow

# Filter by log level
ddk-cli logs my-project --env dev --level ERROR

# Filter by service
ddk-cli logs my-project --env dev --service lambda
```

### List All Projects

```bash
# List all projects
ddk-cli list-projects

# Filter by environment
ddk-cli list-projects --env prod

# Filter by owner
ddk-cli list-projects --owner john.doe
```

## Security and Compliance

### Run Security Scans

```bash
# Run comprehensive security scan
ddk-cli scan my-project --type all

# Run specific scan types
ddk-cli scan my-project --type code
ddk-cli scan my-project --type dependencies
ddk-cli scan my-project --type secrets
```

### Check Compliance

```bash
# Check SOC 2 compliance
ddk-cli compliance my-project --framework SOC2

# Check multiple frameworks
ddk-cli compliance my-project --framework SOC2 --framework ISO27001

# Generate compliance report
ddk-cli compliance my-project --framework SOC2 --output report.html
```

## Configuration Management

### View Configuration

```bash
# Show current configuration
ddk-cli config show

# Show specific configuration section
ddk-cli config show aws
```

### Update Configuration

```bash
# Set AWS region
ddk-cli config set aws.region us-west-2

# Set GitHub organization
ddk-cli config set github.organization my-new-org

# Enable security scanning
ddk-cli config set security.enable_scanning true
```

### Environment-Specific Configuration

```bash
# Set environment-specific account ID
ddk-cli config set aws.staging_account_id 123456789013

# Set environment-specific settings
ddk-cli config set environments.staging.enable_backup true
```

## Advanced Features

### Custom Templates

Create and use custom templates:

```bash
# Create template from existing project
ddk-cli template create my-custom-template --from-project my-project

# Use custom template
ddk-cli create-project new-project --template my-custom-template
```

### Batch Operations

Perform operations on multiple projects:

```bash
# Deploy all projects in an environment
ddk-cli batch deploy --env dev --all

# Update all projects with new template version
ddk-cli batch update --template data-pipeline --version 2.0
```

### Integration with CI/CD

Generate GitHub Actions workflows:

```bash
# Generate CI/CD workflows
ddk-cli generate workflows --output .github/workflows/

# Update existing workflows
ddk-cli generate workflows --update
```

## Troubleshooting

### Common Issues

#### 1. Authentication Errors

```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify CLI configuration
ddk-cli config show aws
```

#### 2. Deployment Failures

```bash
# Check deployment logs
ddk-cli logs my-project --env dev --level ERROR

# Validate project configuration
ddk-cli validate my-project --env dev

# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name MyStack-dev
```

#### 3. Permission Issues

```bash
# Check IAM permissions
aws iam get-user

# Verify account access
aws sts assume-role --role-arn arn:aws:iam::ACCOUNT:role/ROLE --role-session-name test
```

### Debug Mode

Enable verbose output for debugging:

```bash
# Enable verbose output
ddk-cli --verbose deploy my-project --env dev

# Enable debug logging
DDK_LOG_LEVEL=DEBUG ddk-cli deploy my-project --env dev
```

### Getting Help

```bash
# General help
ddk-cli --help

# Command-specific help
ddk-cli deploy --help

# Show version information
ddk-cli --version
```

## Best Practices

### Project Organization

1. **Use Descriptive Names**: Choose clear, descriptive project names
2. **Follow Naming Conventions**: Use kebab-case for project names
3. **Tag Resources**: Use consistent tagging for cost tracking and organization
4. **Document Projects**: Maintain comprehensive README files

### Environment Management

1. **Start with Development**: Always test in dev environment first
2. **Use Approval Gates**: Require manual approval for staging and production
3. **Monitor Deployments**: Watch deployment status and logs
4. **Plan Rollbacks**: Have rollback procedures ready

### Security

1. **Scan Regularly**: Run security scans before deployments
2. **Check Compliance**: Validate compliance requirements
3. **Review Permissions**: Regularly audit IAM permissions
4. **Monitor Costs**: Track and optimize infrastructure costs

### Development Workflow

1. **Version Control**: Commit all changes to Git
2. **Test Locally**: Validate changes before deployment
3. **Use Feature Branches**: Develop features in separate branches
4. **Automate Testing**: Use CI/CD for automated testing

## Examples

### Complete Development Workflow

```bash
# 1. Create new project
ddk-cli create-project customer-analytics --template data-pipeline

# 2. Navigate to project
cd customer-analytics

# 3. Customize project (edit files)
# ... make changes to infrastructure and code ...

# 4. Validate changes
ddk-cli validate --env dev

# 5. Run security scan
ddk-cli scan --type all

# 6. Deploy to development
ddk-cli deploy --env dev

# 7. Test deployment
ddk-cli status --env dev
ddk-cli logs --env dev

# 8. Deploy to staging
ddk-cli deploy --env staging

# 9. Run compliance check
ddk-cli compliance --framework SOC2

# 10. Deploy to production
ddk-cli deploy --env prod --approve
```

### Monitoring and Maintenance

```bash
# Daily monitoring routine
ddk-cli list-projects --env prod
ddk-cli status --env prod --all
ddk-cli logs --env prod --level ERROR --since 24h

# Weekly security scan
ddk-cli scan --type all --all-projects

# Monthly compliance check
ddk-cli compliance --framework SOC2 --all-projects --output monthly-report.html
```

For more detailed information, see the [API Reference](../api/cli.md) and [Troubleshooting Guide](../operations/troubleshooting.md).
