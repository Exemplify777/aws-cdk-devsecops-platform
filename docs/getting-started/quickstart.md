# Quick Start Guide

Get up and running with the DevSecOps Platform in under 30 minutes.

## Overview

This guide will help you:
1. Create your first data pipeline project
2. Deploy it to AWS
3. Monitor and manage the deployment
4. Run security scans and compliance checks

## Prerequisites

- Platform installed and configured (see [Installation Guide](installation.md))
- AWS credentials configured
- CLI initialized with `ddk-cli init`

## Step 1: Create Your First Project

### List Available Templates

```bash
ddk-cli templates
```

Expected output:
```
📋 Available Project Templates:

┌─────────────────┬─────────────────────────────────────────┬──────────────┐
│ Template        │ Description                             │ Type         │
├─────────────────┼─────────────────────────────────────────┼──────────────┤
│ data-pipeline   │ ETL/ELT data processing pipeline        │ Data         │
│ ml-workflow     │ Machine learning training pipeline      │ ML/AI        │
│ streaming       │ Real-time data streaming pipeline       │ Streaming    │
└─────────────────┴─────────────────────────────────────────┴──────────────┘
```

### Create a Data Pipeline Project

```bash
# Create a new data pipeline project
ddk-cli create-project my-first-pipeline \
  --template data-pipeline \
  --env dev \
  --github \
  --deploy
```

This command will:
- Generate a new project from the data-pipeline template
- Create a GitHub repository (if `--github` is specified)
- Deploy the infrastructure to the dev environment (if `--deploy` is specified)

### Project Structure

After creation, your project will have this structure:

```
my-first-pipeline/
├── README.md
├── app.py                    # CDK application entry point
├── cdk.json                  # CDK configuration
├── requirements.txt          # Python dependencies
├── src/                      # Source code
│   ├── lambda/              # Lambda functions
│   ├── glue/                # Glue jobs
│   └── step_functions/      # Step Functions definitions
├── infrastructure/          # CDK infrastructure code
│   ├── stacks/             # CDK stacks
│   └── constructs/         # Reusable constructs
├── tests/                   # Test files
├── data/                    # Sample data
└── .github/workflows/       # CI/CD workflows
```

## Step 2: Deploy Your Project

### Manual Deployment

If you didn't use the `--deploy` flag during creation:

```bash
cd my-first-pipeline

# Deploy to development environment
ddk-cli deploy --env dev

# Deploy specific stack
ddk-cli deploy --env dev --stack DataPipelineStack

# Deploy with auto-approval
ddk-cli deploy --env dev --approve
```

### Monitor Deployment

```bash
# Check deployment status
ddk-cli status my-first-pipeline --env dev

# View deployment logs
ddk-cli logs my-first-pipeline --env dev --follow
```

Expected output:
```
📊 Project Status: my-first-pipeline (dev)

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
```

## Step 3: Test Your Pipeline

### Upload Sample Data

```bash
# Upload sample data to the input bucket
aws s3 cp data/sample.csv s3://my-first-pipeline-input-dev-123456789012/

# Or use the CLI helper
ddk-cli upload-data my-first-pipeline --env dev --file data/sample.csv
```

### Trigger Pipeline Execution

```bash
# Trigger the pipeline manually
ddk-cli execute my-first-pipeline --env dev

# Or trigger with specific parameters
ddk-cli execute my-first-pipeline --env dev \
  --input-path s3://my-first-pipeline-input-dev-123456789012/sample.csv \
  --output-path s3://my-first-pipeline-output-dev-123456789012/processed/
```

### Monitor Execution

```bash
# View pipeline execution status
ddk-cli executions my-first-pipeline --env dev

# View detailed execution logs
ddk-cli logs my-first-pipeline --env dev --execution-id abc123
```

## Step 4: Security and Compliance

### Run Security Scans

```bash
# Run comprehensive security scan
python security/scanner.py scan . --type all --output security-report.json

# Run specific scan types
python security/scanner.py scan . --type code
python security/scanner.py scan . --type dependencies
python security/scanner.py scan . --type secrets
```

### Check Compliance

```bash
# Check SOC 2 compliance
python security/compliance.py check . --framework SOC2

# Check multiple frameworks
python security/compliance.py check . --framework SOC2 --framework ISO27001 --framework GDPR

# Generate compliance report
python security/compliance.py check . --output compliance-report.html --format html
```

## Step 5: Monitoring and Observability

### View Dashboards

```bash
# Open CloudWatch dashboard
ddk-cli dashboard my-first-pipeline --env dev

# View cost dashboard
ddk-cli costs my-first-pipeline --env dev
```

### Set Up Alerts

```bash
# Configure alerting
ddk-cli alerts my-first-pipeline --env dev \
  --email platform-team@company.com \
  --slack-webhook https://hooks.slack.com/services/...
```

### View Metrics

```bash
# View pipeline metrics
ddk-cli metrics my-first-pipeline --env dev

# View specific metric
ddk-cli metrics my-first-pipeline --env dev --metric ExecutionSuccess
```

## Step 6: CI/CD Integration

### GitHub Actions

Your project comes with pre-configured GitHub Actions workflows:

- **CI Pipeline** (`.github/workflows/ci.yml`): Runs on every push and PR
- **CD Pipeline** (`.github/workflows/cd.yml`): Deploys to environments
- **Security Scanning** (`.github/workflows/security.yml`): Runs security scans

### Configure Secrets

Add these secrets to your GitHub repository:

```bash
# AWS credentials
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION

# Environment-specific account IDs
DEV_ACCOUNT_ID
STAGING_ACCOUNT_ID
PROD_ACCOUNT_ID

# Notification webhooks (optional)
SLACK_WEBHOOK_URL
```

### Trigger Deployment

```bash
# Push changes to trigger CI/CD
git add .
git commit -m "Initial pipeline implementation"
git push origin main
```

## Step 7: Promote to Staging

### Deploy to Staging

```bash
# Deploy to staging environment
ddk-cli deploy my-first-pipeline --env staging --approve

# Or use GitHub Actions with manual approval
# Create a pull request to the staging branch
```

### Validate Staging Deployment

```bash
# Run smoke tests
ddk-cli test my-first-pipeline --env staging --type smoke

# Run integration tests
ddk-cli test my-first-pipeline --env staging --type integration
```

## Common Commands Reference

### Project Management

```bash
# List all projects
ddk-cli list-projects

# Get project info
ddk-cli info my-first-pipeline

# Update project
ddk-cli update my-first-pipeline --template data-pipeline-v2

# Delete project
ddk-cli destroy my-first-pipeline --env dev --force
```

### Environment Management

```bash
# List environments
ddk-cli environments

# Switch environment
ddk-cli config set environment staging

# Compare environments
ddk-cli diff my-first-pipeline --source dev --target staging
```

### Troubleshooting

```bash
# View detailed logs
ddk-cli logs my-first-pipeline --env dev --level ERROR

# Debug deployment issues
ddk-cli debug my-first-pipeline --env dev

# Validate configuration
ddk-cli validate my-first-pipeline
```

## Next Steps

Now that you have a working pipeline:

1. **Customize Your Pipeline**: Modify the Lambda functions and Glue jobs
2. **Add More Data Sources**: Configure additional input sources
3. **Set Up Data Quality**: Implement data validation and quality checks
4. **Enable Advanced Monitoring**: Set up custom metrics and dashboards
5. **Implement Data Governance**: Add data cataloging and lineage tracking

## Getting Help

- **Documentation**: [Complete Documentation](https://Exemplify777.github.io/aws-cdk-devsecops-platform)
- **CLI Help**: `ddk-cli --help` or `ddk-cli COMMAND --help`
- **GitHub Issues**: [Report Issues](https://github.com/Exemplify777/aws-cdk-devsecops-platform/issues)
- **Slack Channel**: [#devsecops-platform](https://Exemplify777.slack.com/channels/devsecops-platform)

## Troubleshooting

### Common Issues

1. **Deployment Fails**: Check AWS permissions and account limits
2. **Pipeline Doesn't Trigger**: Verify S3 event notifications
3. **Lambda Timeout**: Increase timeout or optimize code
4. **Glue Job Fails**: Check data format and schema compatibility

For detailed troubleshooting, see the [Troubleshooting Guide](../operations/troubleshooting.md).
