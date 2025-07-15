# Web Portal User Guide

Complete guide to using the DevSecOps Platform self-service web portal for project management and monitoring.

## Overview

The web portal provides a user-friendly interface for:

- **Project Management**: Create, deploy, and manage projects
- **Real-time Monitoring**: View dashboards, metrics, and logs
- **Security & Compliance**: Monitor security posture and compliance status
- **Cost Management**: Track and optimize infrastructure costs
- **Team Collaboration**: Share projects and collaborate with team members

## Accessing the Portal

### Portal URL

After deploying the platform, access the portal at:
```
https://portal.devsecops-platform.company.com
```

### Authentication

The portal supports multiple authentication methods:

1. **AWS IAM**: Use your AWS credentials
2. **SAML/SSO**: Single sign-on with your organization's identity provider
3. **Cognito**: AWS Cognito user pools

### First-Time Setup

1. Navigate to the portal URL
2. Sign in with your credentials
3. Complete your profile setup
4. Configure notification preferences
5. Set up your default AWS region and preferences

## Dashboard Overview

### Main Dashboard

The main dashboard provides an overview of:

- **Project Summary**: Total projects, active deployments, recent activity
- **Health Status**: Overall system health and alerts
- **Cost Overview**: Current month spending and budget status
- **Recent Activity**: Latest deployments, security scans, and compliance checks

### Navigation

- **Projects**: Manage your data pipeline projects
- **Templates**: Browse and use project templates
- **Monitoring**: View metrics, logs, and dashboards
- **Security**: Security scanning and compliance reports
- **Settings**: Configure preferences and integrations

## Project Management

### Creating Projects

#### 1. Using the Project Wizard

1. Click **"Create Project"** on the dashboard
2. Select a project template
3. Configure project parameters
4. Choose deployment environment
5. Review and create

#### 2. Template Selection

Available templates are displayed with:
- **Template Name**: e.g., "Data Pipeline", "ML Workflow"
- **Description**: Brief overview of the template
- **Use Cases**: Common scenarios for the template
- **Complexity**: Beginner, Intermediate, Advanced
- **Estimated Cost**: Monthly cost estimate

#### 3. Configuration

Configure your project with:
- **Basic Information**: Name, description, owner
- **Technical Settings**: AWS region, VPC configuration
- **Data Sources**: S3 buckets, databases, APIs
- **Processing Options**: Batch vs. streaming, compute resources
- **Monitoring**: Enable detailed monitoring, log retention
- **Security**: Compliance frameworks, encryption settings

### Managing Existing Projects

#### Project List View

The project list shows:
- **Project Name**: Click to view details
- **Status**: Deployed, Failed, In Progress, Stopped
- **Environment**: Dev, Staging, Production
- **Last Updated**: Timestamp of last deployment
- **Owner**: Project owner and team
- **Cost**: Current month spending

#### Project Details

Click on a project to view:
- **Overview**: Project summary and status
- **Infrastructure**: Deployed resources and their status
- **Deployments**: Deployment history and logs
- **Monitoring**: Metrics, dashboards, and alerts
- **Security**: Security scan results and compliance status
- **Settings**: Project configuration and team access

### Deployment Management

#### Deploy Project

1. Navigate to project details
2. Click **"Deploy"**
3. Select target environment
4. Review changes (if any)
5. Confirm deployment

#### Deployment Status

Monitor deployment progress with:
- **Progress Bar**: Visual deployment progress
- **Step Details**: Current deployment step
- **Logs**: Real-time deployment logs
- **Estimated Time**: Time remaining for deployment

#### Rollback

If a deployment fails or issues are detected:
1. Go to **Deployments** tab
2. Find the last successful deployment
3. Click **"Rollback"**
4. Confirm rollback action

## Monitoring and Observability

### Real-time Dashboards

#### Infrastructure Dashboard

Monitor infrastructure health:
- **Compute Resources**: Lambda functions, ECS tasks, EC2 instances
- **Storage**: S3 bucket usage, RDS connections, DynamoDB metrics
- **Network**: VPC traffic, API Gateway requests, CloudFront hits
- **Errors**: Error rates, failed executions, timeout issues

#### Application Dashboard

Track application performance:
- **Business Metrics**: Records processed, data quality scores
- **Performance**: Execution time, throughput, latency
- **Data Flow**: Data pipeline stages and bottlenecks
- **Quality**: Data validation results and anomalies

#### Cost Dashboard

Monitor spending and optimization:
- **Current Costs**: This month's spending by service
- **Trends**: Cost trends over time
- **Budget Alerts**: Budget utilization and alerts
- **Optimization**: Cost optimization recommendations

### Metrics and Alerts

#### Custom Metrics

Create custom metrics for:
- **Business KPIs**: Revenue impact, customer metrics
- **Data Quality**: Completeness, accuracy, timeliness
- **Performance**: Custom performance indicators
- **Operational**: Custom operational metrics

#### Alert Configuration

Set up alerts for:
- **Thresholds**: Metric-based alerts
- **Anomalies**: ML-powered anomaly detection
- **Composite**: Multi-metric composite alerts
- **Escalation**: Alert escalation policies

### Log Management

#### Log Viewer

Access logs with:
- **Real-time Streaming**: Live log streaming
- **Search and Filter**: Full-text search and filtering
- **Time Range**: Flexible time range selection
- **Export**: Export logs for analysis

#### Log Analytics

Analyze logs with:
- **Patterns**: Automatic pattern detection
- **Trends**: Log volume and error trends
- **Correlations**: Cross-service log correlation
- **Insights**: AI-powered log insights

## Security and Compliance

### Security Dashboard

Monitor security posture:
- **Vulnerability Summary**: High, medium, low severity issues
- **Compliance Status**: SOC 2, ISO 27001, GDPR compliance
- **Security Trends**: Security improvements over time
- **Threat Detection**: GuardDuty findings and alerts

### Security Scanning

#### Automated Scans

View automated scan results:
- **Code Scanning**: SAST results from Bandit, Semgrep
- **Dependency Scanning**: Vulnerability scanning results
- **Infrastructure Scanning**: IaC security validation
- **Secrets Detection**: Hardcoded secrets detection

#### Manual Scans

Trigger manual scans:
1. Navigate to **Security** section
2. Select scan type
3. Choose scope (project or organization)
4. Click **"Start Scan"**
5. Monitor scan progress

### Compliance Reporting

#### Compliance Dashboard

Track compliance status:
- **Framework Overview**: SOC 2, ISO 27001, GDPR status
- **Control Status**: Individual control compliance
- **Remediation**: Required actions and timelines
- **Reports**: Generate compliance reports

#### Audit Trail

Access audit information:
- **User Actions**: All user actions and changes
- **System Events**: Automated system events
- **Compliance Events**: Compliance-related activities
- **Export**: Export audit logs for compliance

## Cost Management

### Cost Overview

Monitor spending with:
- **Current Month**: Month-to-date spending
- **Projections**: End-of-month cost projections
- **Budget Status**: Budget utilization and alerts
- **Trends**: Spending trends and patterns

### Cost Optimization

#### Recommendations

Get cost optimization suggestions:
- **Right-sizing**: Optimize instance sizes
- **Reserved Instances**: RI recommendations
- **Storage Optimization**: S3 lifecycle policies
- **Unused Resources**: Identify unused resources

#### Cost Allocation

Track costs by:
- **Projects**: Cost per project
- **Teams**: Cost per team or department
- **Environments**: Cost per environment
- **Services**: Cost per AWS service

### Budget Management

#### Budget Setup

Create and manage budgets:
1. Go to **Cost Management**
2. Click **"Create Budget"**
3. Set budget amount and period
4. Configure alert thresholds
5. Set notification recipients

#### Budget Alerts

Receive alerts when:
- **Threshold Reached**: Budget threshold exceeded
- **Forecast**: Projected to exceed budget
- **Anomalies**: Unusual spending patterns detected

## Team Collaboration

### User Management

#### Team Members

Manage team access:
- **Add Members**: Invite team members to projects
- **Roles**: Assign appropriate roles and permissions
- **Remove Access**: Remove team member access
- **Audit**: Track team member activities

#### Permissions

Control access with roles:
- **Viewer**: Read-only access to projects
- **Developer**: Deploy to dev environment
- **Operator**: Deploy to staging environment
- **Admin**: Full project access including production

### Sharing and Collaboration

#### Project Sharing

Share projects with:
- **Internal Teams**: Share within organization
- **External Partners**: Share with external collaborators
- **Public**: Make projects publicly visible (if allowed)

#### Comments and Notes

Collaborate with:
- **Project Comments**: Add comments to projects
- **Deployment Notes**: Add notes to deployments
- **Issue Tracking**: Track and resolve issues
- **Documentation**: Collaborative documentation

## Settings and Configuration

### User Preferences

Configure personal settings:
- **Profile**: Update profile information
- **Notifications**: Email and Slack notification preferences
- **Dashboard**: Customize dashboard layout
- **Timezone**: Set your timezone for accurate timestamps

### Integration Settings

Configure integrations:
- **GitHub**: Connect GitHub repositories
- **Slack**: Configure Slack notifications
- **Email**: Set up email notifications
- **JIRA**: Integrate with JIRA for issue tracking

### Organization Settings

Manage organization-wide settings:
- **Default Templates**: Set default project templates
- **Compliance**: Configure compliance frameworks
- **Cost Policies**: Set cost management policies
- **Security Policies**: Configure security policies

## Mobile Access

### Mobile App

Access the portal on mobile devices:
- **Responsive Design**: Optimized for mobile browsers
- **Native Apps**: iOS and Android apps (if available)
- **Offline Access**: Limited offline functionality

### Mobile Features

Key mobile features:
- **Dashboard**: View project status and alerts
- **Notifications**: Receive push notifications
- **Monitoring**: View metrics and logs
- **Approvals**: Approve deployments on the go

## Troubleshooting

### Common Issues

#### 1. Login Problems

- Check your credentials
- Verify network connectivity
- Clear browser cache and cookies
- Contact your administrator

#### 2. Project Creation Failures

- Verify AWS permissions
- Check template configuration
- Review error messages
- Contact support if needed

#### 3. Deployment Issues

- Check deployment logs
- Verify infrastructure limits
- Review security group settings
- Monitor CloudFormation events

### Getting Help

#### Support Channels

- **Help Documentation**: Built-in help system
- **Support Tickets**: Submit support requests
- **Community Forum**: Community discussions
- **Live Chat**: Real-time support (if available)

#### Self-Service Resources

- **Knowledge Base**: Searchable knowledge base
- **Video Tutorials**: Step-by-step video guides
- **FAQ**: Frequently asked questions
- **Best Practices**: Recommended practices and patterns

For more detailed information, see the [CLI Guide](cli.md) and [API Reference](../api/rest.md).
