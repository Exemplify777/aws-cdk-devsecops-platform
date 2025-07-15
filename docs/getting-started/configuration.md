# Configuration Guide

Complete guide to configuring the DevSecOps Platform for your environment and requirements.

## Overview

The platform supports multiple configuration methods:

- **Environment Variables**: For runtime configuration
- **Configuration Files**: For persistent settings
- **CLI Configuration**: For user-specific preferences
- **Infrastructure Configuration**: For deployment settings

## Environment Variables

### Core Environment Variables

Set these environment variables for basic platform operation:

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export AWS_PROFILE=default

# Account IDs for different environments
export DEV_ACCOUNT_ID=123456789012
export STAGING_ACCOUNT_ID=123456789013
export PROD_ACCOUNT_ID=123456789014

# Project Configuration
export PROJECT_NAME=devsecops-platform
export ORGANIZATION=data-ai-org

# Security Configuration
export ENABLE_SECURITY_SCANNING=true
export COMPLIANCE_FRAMEWORKS=SOC2,ISO27001,GDPR

# Monitoring Configuration
export ENABLE_DETAILED_MONITORING=true
export LOG_RETENTION_DAYS=30
```

### Optional Environment Variables

```bash
# GitHub Integration
export GITHUB_ORG=your-organization
export GITHUB_TOKEN=ghp_your_token_here

# Notification Configuration
export NOTIFICATION_EMAIL=platform-team@company.com
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Feature Flags
export ENABLE_AI_TOOLS=true
export ENABLE_PORTAL=true
export ENABLE_ADVANCED_MONITORING=true

# Development Configuration
export DEBUG=false
export LOG_LEVEL=INFO
```

## Configuration Files

### Platform Configuration

Create a `.env` file in the project root:

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
vim .env
```

Example `.env` file:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default
DEV_ACCOUNT_ID=123456789012
STAGING_ACCOUNT_ID=123456789013
PROD_ACCOUNT_ID=123456789014

# VPC Configuration
VPC_CIDR=10.0.0.0/16
AVAILABILITY_ZONES=us-east-1a,us-east-1b

# Security Configuration
ENABLE_VPC_FLOW_LOGS=true
ENABLE_CLOUDTRAIL=true
ENABLE_CONFIG=true
ENABLE_GUARDDUTY=true

# Database Configuration
DB_INSTANCE_CLASS=db.t3.micro
DB_ALLOCATED_STORAGE=20
DB_BACKUP_RETENTION=7

# Cost Management
COST_ALERT_THRESHOLD=100.0
```

### CDK Configuration

Configure CDK context in `cdk.json`:

```json
{
  "app": "python app.py",
  "context": {
    "dev": {
      "account": "123456789012",
      "region": "us-east-1",
      "vpc_cidr": "10.0.0.0/16",
      "enable_nat_gateway": false,
      "enable_deletion_protection": false
    },
    "staging": {
      "account": "123456789013",
      "region": "us-east-1",
      "vpc_cidr": "10.1.0.0/16",
      "enable_nat_gateway": true,
      "enable_deletion_protection": true
    },
    "prod": {
      "account": "123456789014",
      "region": "us-east-1",
      "vpc_cidr": "10.2.0.0/16",
      "enable_nat_gateway": true,
      "enable_deletion_protection": true
    }
  }
}
```

## CLI Configuration

### Initialize CLI Configuration

```bash
# Interactive configuration
ddk-cli init

# Non-interactive configuration
ddk-cli init --no-interactive \
  --aws-region us-east-1 \
  --github-org my-org \
  --default-template data-pipeline
```

### CLI Configuration File

The CLI configuration is stored in `~/.ddk/config.yaml`:

```yaml
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
  template_repository: https://github.com/my-org/ddk-templates

security:
  enable_scanning: true
  scan_on_deploy: true
  compliance_frameworks:
    - SOC2
    - ISO27001
    - GDPR

monitoring:
  enable_detailed_monitoring: true
  log_retention_days: 30
  cost_alert_threshold: 100.0

notifications:
  email: platform-team@company.com
  slack_webhook: https://hooks.slack.com/services/...
  enable_deployment_notifications: true
  enable_security_notifications: true
```

### Update CLI Configuration

```bash
# View current configuration
ddk-cli config show

# Set specific values
ddk-cli config set aws.region us-west-2
ddk-cli config set github.organization my-new-org
ddk-cli config set security.enable_scanning true

# Reset configuration
ddk-cli config reset
```

## Environment-Specific Configuration

### Development Environment

```yaml
# config/dev.yaml
environment: dev
enable_deletion_protection: false
enable_backup: false
instance_types:
  small: t3.micro
  medium: t3.small
  large: t3.medium
monitoring:
  detailed_monitoring: false
  log_retention_days: 7
cost_optimization:
  enable_spot_instances: true
  enable_scheduled_scaling: false
```

### Staging Environment

```yaml
# config/staging.yaml
environment: staging
enable_deletion_protection: true
enable_backup: true
instance_types:
  small: t3.small
  medium: t3.medium
  large: t3.large
monitoring:
  detailed_monitoring: true
  log_retention_days: 30
cost_optimization:
  enable_spot_instances: false
  enable_scheduled_scaling: true
```

### Production Environment

```yaml
# config/prod.yaml
environment: prod
enable_deletion_protection: true
enable_backup: true
instance_types:
  small: t3.medium
  medium: t3.large
  large: t3.xlarge
monitoring:
  detailed_monitoring: true
  log_retention_days: 90
cost_optimization:
  enable_spot_instances: false
  enable_scheduled_scaling: true
security:
  enable_enhanced_monitoring: true
  enable_compliance_scanning: true
```

## Security Configuration

### IAM Configuration

```yaml
# security/iam-config.yaml
iam:
  password_policy:
    minimum_length: 14
    require_symbols: true
    require_numbers: true
    require_uppercase: true
    require_lowercase: true
    max_age_days: 90
    reuse_prevention: 24
  
  mfa_required: true
  
  roles:
    developer:
      permissions:
        - read_projects
        - deploy_dev
        - view_logs
    
    operator:
      permissions:
        - read_projects
        - deploy_staging
        - manage_monitoring
    
    admin:
      permissions:
        - manage_projects
        - deploy_production
        - manage_security
```

### Security Scanning Configuration

```yaml
# security/scanning-config.yaml
security_scanning:
  code_scanning:
    enabled: true
    tools:
      - bandit
      - semgrep
    severity_threshold: medium
  
  dependency_scanning:
    enabled: true
    tools:
      - safety
      - pip-audit
    auto_update: false
  
  secrets_scanning:
    enabled: true
    tools:
      - detect-secrets
    exclude_patterns:
      - "*.test.js"
      - "test_*.py"
  
  infrastructure_scanning:
    enabled: true
    tools:
      - checkov
      - cfn-lint
    fail_on_high: true
```

## Monitoring Configuration

### CloudWatch Configuration

```yaml
# monitoring/cloudwatch-config.yaml
cloudwatch:
  metrics:
    retention_days: 30
    detailed_monitoring: true
    custom_metrics:
      - business_kpis
      - data_quality
      - performance
  
  logs:
    retention_days: 30
    log_groups:
      - /aws/lambda/
      - /aws/apigateway/
      - /aws/ecs/
  
  alarms:
    error_rate_threshold: 0.01
    latency_threshold: 5000
    cost_threshold: 100.0
    
  dashboards:
    - infrastructure
    - application
    - business
    - security
```

### Notification Configuration

```yaml
# monitoring/notifications-config.yaml
notifications:
  email:
    enabled: true
    recipients:
      - platform-team@company.com
      - security-team@company.com
    
  slack:
    enabled: true
    webhook_url: https://hooks.slack.com/services/...
    channels:
      alerts: "#platform-alerts"
      deployments: "#deployments"
      security: "#security-alerts"
  
  pagerduty:
    enabled: false
    integration_key: your-integration-key
    
  sns:
    enabled: true
    topics:
      - platform-alerts
      - security-alerts
      - cost-alerts
```

## Validation and Testing

### Configuration Validation

```bash
# Validate platform configuration
ddk-cli validate-config

# Validate specific environment
ddk-cli validate-config --env prod

# Validate security configuration
ddk-cli validate-config --type security
```

### Configuration Testing

```bash
# Test AWS connectivity
aws sts get-caller-identity

# Test CDK synthesis
cdk synth --context environment=dev

# Test CLI configuration
ddk-cli config test

# Test security scanning
python security/scanner.py test-config
```

## Best Practices

### Configuration Management

1. **Use Environment Variables**: For sensitive information and runtime configuration
2. **Version Control**: Store configuration files in version control (except secrets)
3. **Environment Separation**: Use separate configurations for each environment
4. **Validation**: Always validate configuration before deployment
5. **Documentation**: Document all configuration options and their purposes

### Security Best Practices

1. **Secrets Management**: Never store secrets in configuration files
2. **Least Privilege**: Configure minimal required permissions
3. **Encryption**: Enable encryption for all sensitive data
4. **Monitoring**: Enable comprehensive monitoring and alerting
5. **Regular Reviews**: Regularly review and update configurations

### Performance Optimization

1. **Resource Sizing**: Configure appropriate resource sizes for each environment
2. **Auto-scaling**: Enable auto-scaling for variable workloads
3. **Caching**: Configure caching where appropriate
4. **Monitoring**: Monitor performance metrics and optimize accordingly

## Troubleshooting

### Common Configuration Issues

#### 1. AWS Credentials

```bash
# Check AWS credentials
aws sts get-caller-identity

# Configure AWS CLI
aws configure

# Use specific profile
export AWS_PROFILE=my-profile
```

#### 2. Permission Issues

```bash
# Check IAM permissions
aws iam get-user

# List attached policies
aws iam list-attached-user-policies --user-name my-user
```

#### 3. CDK Configuration

```bash
# Check CDK context
cdk context

# Clear CDK context
cdk context --clear

# Bootstrap CDK
cdk bootstrap
```

### Configuration Validation Errors

```bash
# Check configuration syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Validate environment variables
env | grep -E "(AWS_|DDK_)"

# Test configuration
ddk-cli config test --verbose
```

## Additional Resources

- [Installation Guide](installation.md): Platform installation instructions
- [Quick Start](quickstart.md): Getting started tutorial
- [Security Configuration](../security/overview.md): Detailed security configuration
- [Monitoring Setup](../operations/monitoring.md): Monitoring configuration
- [Troubleshooting](../operations/troubleshooting.md): Common issues and solutions
