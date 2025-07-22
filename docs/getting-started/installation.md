# Installation Guide

This guide will walk you through installing and setting up the DevSecOps Platform for data pipelines and ML workflows.

## Prerequisites

Before installing the platform, ensure you have the following prerequisites:

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL2
- **Python**: 3.9 or higher
- **Node.js**: 18.x or higher
- **Git**: Latest version
- **Docker**: Latest version (for local development)

### AWS Requirements

- **AWS Account**: Active AWS account with appropriate permissions
- **AWS CLI**: Configured with credentials
- **AWS CDK**: Version 2.100.0 or higher

### Development Tools

- **IDE**: VS Code, PyCharm, or similar
- **Terminal**: Bash, Zsh, or PowerShell

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Exemplify777/aws-cdk-devsecops-platform.git
cd aws-cdk-devsecops-platform
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt

# Install the CLI tool in development mode
pip install -e .
```

### 4. Install AWS CDK

```bash
# Install AWS CDK globally
npm install -g aws-cdk

# Verify installation
cdk --version
```

### 5. Configure AWS Credentials

```bash
# Configure AWS CLI (if not already done)
aws configure

# Verify configuration
aws sts get-caller-identity
```

### 6. Bootstrap AWS CDK

```bash
# Bootstrap CDK for your account and region
cdk bootstrap

# Bootstrap for multiple environments (optional)
cdk bootstrap --profile dev
cdk bootstrap --profile staging
cdk bootstrap --profile prod
```

### 7. Initialize CLI Configuration

```bash
# Initialize the CLI with interactive setup
ddk-cli init

# Or initialize with specific configuration
ddk-cli init --config config.yaml --no-interactive
```

### 8. Verify Installation

```bash
# Check CLI functionality
ddk-cli --help

# List available templates
ddk-cli templates

# Run platform tests
python scripts/test_platform.py

# Run security scans
python security/scanner.py scan .
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Development Account
DEV_ACCOUNT_ID=123456789012

# Staging Account (optional)
STAGING_ACCOUNT_ID=123456789013

# Production Account (optional)
PROD_ACCOUNT_ID=123456789014

# GitHub Configuration (optional)
GITHUB_ORG=Exemplify777
GITHUB_TOKEN=ghp_your_token_here

# Notification Configuration (optional)
NOTIFICATION_EMAIL=platform-team@company.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Feature Flags
ENABLE_AI_TOOLS=true
ENABLE_PORTAL=true
ENABLE_ADVANCED_MONITORING=true
```

### CLI Configuration

The CLI configuration is stored in `~/.ddk/config.yaml`:

```yaml
aws:
  region: us-east-1
  profile: default
  dev_account_id: "123456789012"
  staging_account_id: "123456789013"
  prod_account_id: "123456789014"

github:
  organization: Exemplify777
  token: ghp_your_token_here

templates:
  default_template: data-pipeline
  template_repository: https://github.com/Exemplify777/aws-cdk-devsecops-platform

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
```

## Troubleshooting

### Common Issues

#### 1. Python Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### 2. AWS Permission Errors

```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify IAM permissions
aws iam get-user
```

#### 3. CDK Bootstrap Issues

```bash
# Re-bootstrap with explicit account and region
cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

#### 4. CLI Command Not Found

```bash
# Reinstall CLI in development mode
pip install -e .

# Check if CLI is in PATH
which ddk-cli
```

### Getting Help

- **Documentation**: [Complete Documentation](https://Exemplify777.github.io/aws-cdk-devsecops-platform)
- **GitHub Issues**: [Report Issues](https://github.com/Exemplify777/aws-cdk-devsecops-platform/issues)
- **Slack Channel**: [#devsecops-platform](https://Exemplify777.slack.com/channels/devsecops-platform)

## Next Steps

After successful installation:

1. **Create Your First Project**: Follow the [Quick Start Guide](../getting-started/quickstart.md)
2. **Deploy to Development**: See [Deployment Guide](../operations/deployment.md)
3. **Set Up CI/CD**: Configure [GitHub Actions](../operations/cicd.md)
4. **Enable Security Scanning**: Set up [Security Scanning](../security/scanning.md)
5. **Configure Monitoring**: Enable [Monitoring and Alerting](../operations/monitoring.md)

## Uninstallation

To remove the platform:

```bash
# Destroy all deployed resources
ddk-cli destroy --env dev --force
ddk-cli destroy --env staging --force
ddk-cli destroy --env prod --force

# Remove CLI configuration
rm -rf ~/.ddk

# Deactivate and remove virtual environment
deactivate
rm -rf venv

# Remove project directory
cd ..
rm -rf aws-cdk-devsecops-platform
```
