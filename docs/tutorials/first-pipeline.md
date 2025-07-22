# Tutorial: Building Your First Data Pipeline

This tutorial will guide you through creating, deploying, and managing your first data pipeline using the DevSecOps Platform.

## What You'll Build

By the end of this tutorial, you'll have:

- A complete ETL data pipeline processing CSV files
- Infrastructure deployed to AWS with security best practices
- Monitoring and alerting configured
- CI/CD pipeline set up with GitHub Actions
- Security scanning and compliance validation

## Prerequisites

Before starting, ensure you have:

- DevSecOps Platform installed and configured
- AWS CLI configured with appropriate permissions
- GitHub account (optional, for CI/CD)
- Basic understanding of data processing concepts

## Step 1: Initialize Your Environment

### Configure the CLI

First, let's set up the CLI with your preferences:

```bash
ddk-cli init
```

You'll be prompted for:
- AWS region (e.g., `us-east-1`)
- AWS account IDs for different environments
- GitHub organization (optional)
- Default notification settings

### Verify Configuration

Check that everything is configured correctly:

```bash
# Verify CLI configuration
ddk-cli config show

# Check AWS connectivity
aws sts get-caller-identity

# List available templates
ddk-cli templates
```

## Step 2: Create Your First Project

### Choose a Template

We'll use the `data-pipeline` template for this tutorial:

```bash
ddk-cli templates --filter data-pipeline
```

### Create the Project

Create a new project called `sales-analytics`:

```bash
ddk-cli create-project sales-analytics --template data-pipeline
```

You'll be prompted to configure:
- **Data source type**: Choose `s3`
- **Processing engine**: Choose `glue`
- **Output format**: Choose `parquet`
- **Enable streaming**: Choose `no`
- **Data quality checks**: Choose `yes`

### Explore the Project Structure

Navigate to your new project and explore the structure:

```bash
cd sales-analytics
ls -la
```

You should see:
```
sales-analytics/
├── README.md                 # Project documentation
├── app.py                    # CDK application entry point
├── cdk.json                  # CDK configuration
├── requirements.txt          # Python dependencies
├── infrastructure/           # CDK infrastructure code
├── src/                     # Source code
├── tests/                   # Test files
├── data/                    # Sample data
└── .github/workflows/       # CI/CD workflows
```

## Step 3: Understand the Infrastructure

### Review the CDK Stacks

Open `app.py` to see the CDK application structure:

```python
#!/usr/bin/env python3
import aws_cdk as cdk
from infrastructure.stacks.data_pipeline_stack import DataPipelineStack

app = cdk.App()

DataPipelineStack(
    app,
    "SalesAnalyticsStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region")
    )
)

app.synth()
```

### Examine the Data Pipeline Stack

Look at `infrastructure/stacks/data_pipeline_stack.py`:

```python
class DataPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 buckets for data lake
        self.raw_bucket = s3.Bucket(self, "RawDataBucket")
        self.processed_bucket = s3.Bucket(self, "ProcessedDataBucket")
        self.curated_bucket = s3.Bucket(self, "CuratedDataBucket")
        
        # Glue database and crawler
        self.database = glue.CfnDatabase(self, "DataDatabase")
        self.crawler = glue.CfnCrawler(self, "DataCrawler")
        
        # Lambda functions for processing
        self.processor_function = lambda_.Function(self, "ProcessorFunction")
        
        # Step Functions for orchestration
        self.state_machine = stepfunctions.StateMachine(self, "DataPipeline")
```

## Step 4: Deploy to Development

### Install Dependencies

First, install the required dependencies:

```bash
pip install -r requirements.txt
```

### Deploy the Infrastructure

Deploy your pipeline to the development environment:

```bash
ddk-cli deploy --env dev
```

This will:
1. Synthesize the CDK templates
2. Create CloudFormation stacks
3. Deploy AWS resources
4. Configure monitoring and alerting
5. Set up security controls

### Monitor the Deployment

Watch the deployment progress:

```bash
# Check deployment status
ddk-cli status --env dev

# Follow deployment logs
ddk-cli logs --env dev --follow
```

Expected output:
```
📊 Project Status: sales-analytics (dev)

┌─────────────────────┬─────────────────┬─────────────────────┐
│ Stack               │ Status          │ Last Updated        │
├─────────────────────┼─────────────────┼─────────────────────┤
│ SalesAnalyticsStack │ CREATE_COMPLETE │ 2024-01-15 10:30:00 │
└─────────────────────┴─────────────────┴─────────────────────┘

🏥 Health Checks:
✅ S3 Buckets: 3 buckets created
✅ Lambda Functions: 2 functions deployed
✅ Glue Database: Database ready
✅ Step Functions: State machine active
```

## Step 5: Test Your Pipeline

### Upload Sample Data

Upload the provided sample data to test your pipeline:

```bash
# Upload sample CSV file
aws s3 cp data/sample-sales.csv s3://sales-analytics-raw-dev-123456789012/input/

# Or use the CLI helper
ddk-cli upload-data --file data/sample-sales.csv --env dev
```

### Trigger the Pipeline

Start the data processing pipeline:

```bash
# Trigger pipeline execution
ddk-cli execute --env dev

# Monitor execution
ddk-cli executions --env dev
```

### Verify Results

Check that the pipeline processed the data correctly:

```bash
# List processed files
aws s3 ls s3://sales-analytics-processed-dev-123456789012/

# Check curated data
aws s3 ls s3://sales-analytics-curated-dev-123456789012/
```

## Step 6: Monitor Your Pipeline

### View Dashboards

Access the monitoring dashboard:

```bash
# Open CloudWatch dashboard
ddk-cli dashboard --env dev
```

Or access through the web portal at the provided URL.

### Check Metrics

View key pipeline metrics:

```bash
# View pipeline metrics
ddk-cli metrics --env dev

# View specific metric
ddk-cli metrics --env dev --metric ProcessedRecords
```

### Set Up Alerts

Configure alerting for your pipeline:

```bash
# Configure email alerts
ddk-cli alerts --env dev --email your-email@company.com

# Configure Slack alerts
ddk-cli alerts --env dev --slack-webhook https://hooks.slack.com/services/...
```

## Step 7: Security and Compliance

### Run Security Scans

Perform comprehensive security scanning:

```bash
# Run all security scans
ddk-cli scan --type all --env dev

# View scan results
ddk-cli scan-results --env dev --latest
```

### Check Compliance

Validate compliance with organizational standards:

```bash
# Check SOC 2 compliance
ddk-cli compliance --framework SOC2 --env dev

# Generate compliance report
ddk-cli compliance --framework SOC2 --env dev --output compliance-report.html
```

## Step 8: Set Up CI/CD

### Connect to GitHub

If you want to set up CI/CD with GitHub:

```bash
# Initialize git repository
git init
git add .
git commit -m "Initial data pipeline implementation"

# Create GitHub repository and push
gh repo create sales-analytics --private
git remote add origin https://github.com/Exemplify777/sales-analytics.git
git push -u origin main
```

### Configure GitHub Secrets

Add these secrets to your GitHub repository:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_REGION`: Your AWS region
- `DEV_ACCOUNT_ID`: Development account ID
- `STAGING_ACCOUNT_ID`: Staging account ID (if applicable)
- `PROD_ACCOUNT_ID`: Production account ID (if applicable)

### Test CI/CD Pipeline

Make a small change and push to trigger the CI/CD pipeline:

```bash
# Make a small change
echo "# Updated README" >> README.md

# Commit and push
git add README.md
git commit -m "Update README"
git push
```

Check the GitHub Actions tab to see the pipeline running.

## Step 9: Deploy to Staging

### Prepare for Staging

Before deploying to staging, ensure:
- All tests pass in development
- Security scans show no critical issues
- Compliance checks pass

### Deploy to Staging

```bash
# Deploy to staging environment
ddk-cli deploy --env staging
```

This deployment will require manual approval due to the staging environment configuration.

### Validate Staging Deployment

```bash
# Check staging status
ddk-cli status --env staging

# Run smoke tests
ddk-cli test --env staging --type smoke

# Upload test data
ddk-cli upload-data --file data/test-data.csv --env staging

# Execute pipeline
ddk-cli execute --env staging
```

## Step 10: Production Deployment

### Pre-Production Checklist

Before deploying to production:

- [ ] All staging tests pass
- [ ] Security review completed
- [ ] Performance testing completed
- [ ] Disaster recovery plan in place
- [ ] Monitoring and alerting configured
- [ ] Team trained on operations

### Deploy to Production

```bash
# Deploy to production (requires approval)
ddk-cli deploy --env prod --approve
```

### Post-Deployment Validation

```bash
# Verify production deployment
ddk-cli status --env prod

# Run production smoke tests
ddk-cli test --env prod --type smoke

# Monitor for issues
ddk-cli logs --env prod --follow --level ERROR
```

## Step 11: Ongoing Operations

### Daily Operations

Regular tasks for maintaining your pipeline:

```bash
# Check pipeline health
ddk-cli status --env prod

# Review error logs
ddk-cli logs --env prod --level ERROR --since 24h

# Check cost metrics
ddk-cli costs --env prod
```

### Weekly Maintenance

Weekly maintenance tasks:

```bash
# Run security scans
ddk-cli scan --type all --env prod

# Review compliance status
ddk-cli compliance --framework SOC2 --env prod

# Check for cost optimization opportunities
ddk-cli optimize --env prod
```

### Monthly Reviews

Monthly review activities:

```bash
# Generate monthly reports
ddk-cli report --env prod --period monthly

# Review and update documentation
# Update team access and permissions
# Plan capacity and scaling needs
```

## Troubleshooting

### Common Issues

#### 1. Deployment Failures

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name SalesAnalyticsStack-dev

# Review deployment logs
ddk-cli logs --env dev --level ERROR

# Validate configuration
ddk-cli validate --env dev
```

#### 2. Pipeline Execution Failures

```bash
# Check Step Functions execution
aws stepfunctions list-executions --state-machine-arn <state-machine-arn>

# Review Lambda function logs
aws logs tail /aws/lambda/sales-analytics-processor-dev --follow

# Check Glue job status
aws glue get-job-runs --job-name sales-analytics-etl-dev
```

#### 3. Data Quality Issues

```bash
# Check data quality metrics
ddk-cli metrics --env dev --metric DataQualityScore

# Review data validation logs
ddk-cli logs --env dev --service data-validator

# Examine failed records
aws s3 ls s3://sales-analytics-errors-dev-123456789012/
```

## Next Steps

Now that you have a working data pipeline:

1. **Customize the Pipeline**: Modify the Lambda functions and Glue jobs for your specific use case
2. **Add More Data Sources**: Configure additional input sources (databases, APIs, etc.)
3. **Implement Advanced Features**: Add real-time processing, machine learning, or advanced analytics
4. **Scale the Pipeline**: Optimize for larger data volumes and higher throughput
5. **Enhance Monitoring**: Add custom metrics and business-specific dashboards

## Additional Resources

- [CLI Reference](../user-guide/cli.md): Complete CLI command reference
- [Template Guide](../user-guide/templates.md): Customizing and creating templates
- [Security Guide](../security/overview.md): Security best practices
- [Monitoring Guide](../operations/monitoring.md): Advanced monitoring setup
- [Troubleshooting Guide](../operations/troubleshooting.md): Common issues and solutions

Congratulations! You've successfully built, deployed, and operated your first data pipeline using the DevSecOps Platform. 🎉
