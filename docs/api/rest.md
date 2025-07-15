# REST API Reference

Complete reference for the DevSecOps Platform REST APIs.

## Base URL

```
https://api.devsecops-platform.company.com/v1
```

## Authentication

All API requests require authentication using AWS IAM or API keys.

### AWS IAM Authentication

Use AWS Signature Version 4 for authentication:

```bash
curl -X GET \
  https://api.devsecops-platform.company.com/v1/projects \
  --aws-sigv4 "aws:amz:us-east-1:execute-api" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY"
```

### API Key Authentication

Include the API key in the `X-API-Key` header:

```bash
curl -X GET \
  https://api.devsecops-platform.company.com/v1/projects \
  -H "X-API-Key: your-api-key"
```

## Projects API

### List Projects

Get a list of all projects.

```http
GET /projects
```

**Query Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `environment` | string | Filter by environment | |
| `owner` | string | Filter by owner | |
| `status` | string | Filter by status | |
| `limit` | integer | Number of results to return | `50` |
| `offset` | integer | Number of results to skip | `0` |

**Response:**

```json
{
  "projects": [
    {
      "id": "proj_123456789",
      "name": "sales-analytics",
      "description": "Sales data analytics pipeline",
      "template": "data-pipeline",
      "environment": "dev",
      "status": "deployed",
      "owner": "john.doe@company.com",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T14:20:00Z",
      "tags": {
        "team": "data-engineering",
        "cost-center": "analytics"
      }
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### Get Project

Get details of a specific project.

```http
GET /projects/{project_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Project ID |

**Response:**

```json
{
  "id": "proj_123456789",
  "name": "sales-analytics",
  "description": "Sales data analytics pipeline",
  "template": "data-pipeline",
  "environment": "dev",
  "status": "deployed",
  "owner": "john.doe@company.com",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T14:20:00Z",
  "configuration": {
    "aws_region": "us-east-1",
    "vpc_cidr": "10.0.0.0/16",
    "enable_monitoring": true
  },
  "infrastructure": {
    "stacks": [
      {
        "name": "CoreInfrastructure-dev",
        "status": "CREATE_COMPLETE",
        "last_updated": "2024-01-15T10:35:00Z"
      }
    ]
  },
  "tags": {
    "team": "data-engineering",
    "cost-center": "analytics"
  }
}
```

### Create Project

Create a new project.

```http
POST /projects
```

**Request Body:**

```json
{
  "name": "new-pipeline",
  "description": "New data pipeline project",
  "template": "data-pipeline",
  "environment": "dev",
  "configuration": {
    "aws_region": "us-east-1",
    "enable_monitoring": true
  },
  "tags": {
    "team": "data-engineering"
  }
}
```

**Response:**

```json
{
  "id": "proj_987654321",
  "name": "new-pipeline",
  "status": "creating",
  "created_at": "2024-01-15T15:00:00Z"
}
```

### Update Project

Update an existing project.

```http
PUT /projects/{project_id}
```

**Request Body:**

```json
{
  "description": "Updated description",
  "configuration": {
    "enable_monitoring": true,
    "log_retention_days": 30
  },
  "tags": {
    "team": "data-engineering",
    "updated": "true"
  }
}
```

### Delete Project

Delete a project and its infrastructure.

```http
DELETE /projects/{project_id}
```

**Query Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `force` | boolean | Force deletion without confirmation | `false` |
| `retain_data` | boolean | Retain data resources | `true` |

**Response:**

```json
{
  "message": "Project deletion initiated",
  "deletion_id": "del_123456789"
}
```

## Deployments API

### List Deployments

Get deployment history for a project.

```http
GET /projects/{project_id}/deployments
```

**Response:**

```json
{
  "deployments": [
    {
      "id": "dep_123456789",
      "project_id": "proj_123456789",
      "environment": "dev",
      "status": "succeeded",
      "started_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:45:00Z",
      "duration": 900,
      "deployed_by": "john.doe@company.com",
      "commit_sha": "abc123def456",
      "changes": [
        "Updated Lambda function timeout",
        "Added new S3 bucket"
      ]
    }
  ]
}
```

### Create Deployment

Deploy a project to an environment.

```http
POST /projects/{project_id}/deployments
```

**Request Body:**

```json
{
  "environment": "staging",
  "auto_approve": false,
  "rollback_on_failure": true,
  "notification_channels": [
    "slack://team-channel",
    "email://team@company.com"
  ]
}
```

**Response:**

```json
{
  "id": "dep_987654321",
  "status": "pending",
  "created_at": "2024-01-15T15:00:00Z"
}
```

### Get Deployment Status

Get the status of a specific deployment.

```http
GET /projects/{project_id}/deployments/{deployment_id}
```

**Response:**

```json
{
  "id": "dep_123456789",
  "project_id": "proj_123456789",
  "environment": "dev",
  "status": "in_progress",
  "progress": 65,
  "started_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T10:45:00Z",
  "steps": [
    {
      "name": "Validate Configuration",
      "status": "completed",
      "duration": 30
    },
    {
      "name": "Deploy Infrastructure",
      "status": "in_progress",
      "progress": 80
    },
    {
      "name": "Run Tests",
      "status": "pending"
    }
  ]
}
```

## Monitoring API

### Get Project Metrics

Get metrics for a project.

```http
GET /projects/{project_id}/metrics
```

**Query Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `environment` | string | Environment to get metrics for | `dev` |
| `start_time` | string | Start time (ISO 8601) | 24 hours ago |
| `end_time` | string | End time (ISO 8601) | now |
| `metrics` | array | Specific metrics to retrieve | all |

**Response:**

```json
{
  "project_id": "proj_123456789",
  "environment": "dev",
  "time_range": {
    "start": "2024-01-14T15:00:00Z",
    "end": "2024-01-15T15:00:00Z"
  },
  "metrics": {
    "lambda_invocations": {
      "value": 1250,
      "unit": "Count",
      "trend": "+15%"
    },
    "lambda_errors": {
      "value": 3,
      "unit": "Count",
      "trend": "-50%"
    },
    "lambda_duration": {
      "value": 2.5,
      "unit": "Seconds",
      "trend": "-10%"
    },
    "s3_requests": {
      "value": 850,
      "unit": "Count",
      "trend": "+5%"
    },
    "cost": {
      "value": 12.45,
      "unit": "USD",
      "trend": "+8%"
    }
  }
}
```

### Get Project Logs

Get logs for a project.

```http
GET /projects/{project_id}/logs
```

**Query Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `environment` | string | Environment | `dev` |
| `start_time` | string | Start time (ISO 8601) | 1 hour ago |
| `end_time` | string | End time (ISO 8601) | now |
| `level` | string | Log level filter | |
| `service` | string | Service filter | |
| `limit` | integer | Number of log entries | `100` |

**Response:**

```json
{
  "logs": [
    {
      "timestamp": "2024-01-15T14:30:00Z",
      "level": "INFO",
      "service": "data-processor",
      "message": "Processing batch completed successfully",
      "metadata": {
        "batch_id": "batch_123",
        "records_processed": 1000
      }
    }
  ],
  "total": 1,
  "has_more": false
}
```

## Security API

### Run Security Scan

Initiate a security scan for a project.

```http
POST /projects/{project_id}/security/scan
```

**Request Body:**

```json
{
  "scan_types": ["code", "dependencies", "secrets", "infrastructure"],
  "severity_threshold": "medium",
  "notification_channels": ["email://security@company.com"]
}
```

**Response:**

```json
{
  "scan_id": "scan_123456789",
  "status": "initiated",
  "estimated_duration": 300
}
```

### Get Security Scan Results

Get results of a security scan.

```http
GET /projects/{project_id}/security/scans/{scan_id}
```

**Response:**

```json
{
  "scan_id": "scan_123456789",
  "project_id": "proj_123456789",
  "status": "completed",
  "started_at": "2024-01-15T14:00:00Z",
  "completed_at": "2024-01-15T14:05:00Z",
  "summary": {
    "total_issues": 5,
    "high_severity": 1,
    "medium_severity": 2,
    "low_severity": 2,
    "risk_level": "MEDIUM"
  },
  "results": {
    "code": {
      "issues": [
        {
          "severity": "HIGH",
          "type": "hardcoded_secret",
          "file": "src/config.py",
          "line": 15,
          "description": "Hardcoded API key detected"
        }
      ]
    },
    "dependencies": {
      "vulnerabilities": [
        {
          "package": "requests",
          "version": "2.25.1",
          "vulnerability": "CVE-2021-33503",
          "severity": "MEDIUM"
        }
      ]
    }
  }
}
```

## Compliance API

### Check Compliance

Run compliance checks for a project.

```http
POST /projects/{project_id}/compliance/check
```

**Request Body:**

```json
{
  "frameworks": ["SOC2", "ISO27001", "GDPR"],
  "generate_report": true,
  "report_format": "html"
}
```

**Response:**

```json
{
  "check_id": "comp_123456789",
  "status": "initiated",
  "frameworks": ["SOC2", "ISO27001", "GDPR"]
}
```

### Get Compliance Results

Get compliance check results.

```http
GET /projects/{project_id}/compliance/checks/{check_id}
```

**Response:**

```json
{
  "check_id": "comp_123456789",
  "project_id": "proj_123456789",
  "status": "completed",
  "frameworks": {
    "SOC2": {
      "compliant": true,
      "score": 95,
      "controls_passed": 38,
      "controls_total": 40,
      "violations": []
    },
    "ISO27001": {
      "compliant": false,
      "score": 85,
      "controls_passed": 85,
      "controls_total": 100,
      "violations": [
        {
          "control": "A.12.1.2",
          "description": "Change management procedures",
          "severity": "MEDIUM"
        }
      ]
    }
  }
}
```

## Templates API

### List Templates

Get available project templates.

```http
GET /templates
```

**Response:**

```json
{
  "templates": [
    {
      "name": "data-pipeline",
      "display_name": "Data Pipeline",
      "description": "ETL/ELT data processing pipeline",
      "category": "data",
      "version": "1.0.0",
      "parameters": [
        {
          "name": "data_source_type",
          "type": "choice",
          "choices": ["s3", "rds", "api"],
          "default": "s3"
        }
      ]
    }
  ]
}
```

### Get Template

Get details of a specific template.

```http
GET /templates/{template_name}
```

**Response:**

```json
{
  "name": "data-pipeline",
  "display_name": "Data Pipeline",
  "description": "ETL/ELT data processing pipeline",
  "category": "data",
  "version": "1.0.0",
  "parameters": [
    {
      "name": "project_name",
      "type": "string",
      "required": true,
      "description": "Name of the project"
    },
    {
      "name": "data_source_type",
      "type": "choice",
      "choices": ["s3", "rds", "dynamodb", "api"],
      "default": "s3",
      "description": "Type of data source"
    }
  ],
  "files": [
    "app.py",
    "requirements.txt",
    "infrastructure/",
    "src/lambda/",
    "tests/"
  ]
}
```

## Error Responses

All API endpoints return consistent error responses:

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

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |

## Rate Limiting

API requests are rate limited:

- **Authenticated requests**: 1000 requests per hour
- **Unauthenticated requests**: 100 requests per hour

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642262400
```

## Webhooks

Configure webhooks to receive notifications about project events.

### Webhook Events

- `project.created`
- `project.updated`
- `project.deleted`
- `deployment.started`
- `deployment.completed`
- `deployment.failed`
- `security.scan_completed`
- `compliance.check_completed`

### Webhook Payload

```json
{
  "event": "deployment.completed",
  "timestamp": "2024-01-15T15:00:00Z",
  "data": {
    "project_id": "proj_123456789",
    "deployment_id": "dep_987654321",
    "environment": "dev",
    "status": "succeeded",
    "duration": 900
  }
}
```
