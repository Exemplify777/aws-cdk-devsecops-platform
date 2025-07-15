# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Overview

This data pipeline project provides a scalable, secure, and maintainable infrastructure for ETL/ELT data processing. It is built using AWS CDK with Python and follows DevSecOps best practices.

## Architecture

The pipeline architecture includes:

- **Data Ingestion**: Automated ingestion from multiple sources ({% for source in cookiecutter.data_sources %}{{ source }}{% if not loop.last %}, {% endif %}{% endfor %})
- **Data Processing**: Serverless compute using {% for engine in cookiecutter.processing_engine %}{{ engine }}{% if not loop.last %}, {% endif %}{% endfor %}
- **Data Storage**: S3-based data lake with partitioning and lifecycle policies
- **Orchestration**: Step Functions workflow with error handling and retry logic
- **Scheduling**: EventBridge rules for {{ cookiecutter.schedule }} execution
- **Monitoring**: CloudWatch dashboards, alarms, and logs
- **Security**: IAM least privilege, encryption, VPC isolation

## Getting Started

### Prerequisites

- Python {{ cookiecutter.python_version }}+
- AWS CLI configured
- AWS CDK CLI installed
- Docker (for local development)

### Installation

1. Clone the repository:
```bash
git clone {% if cookiecutter.github_org %}https://github.com/{{ cookiecutter.github_org }}/{{ cookiecutter.project_slug }}{% else %}[repository-url]{% endif %}
cd {{ cookiecutter.project_slug }}
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Deploy the infrastructure:
```bash
cdk deploy --all --context environment={{ cookiecutter.environment }}
```

## Project Structure

```
{{ cookiecutter.project_slug }}/
├── infrastructure/           # CDK infrastructure code
│   ├── stacks/              # CDK stack definitions
│   └── constructs/          # Reusable CDK constructs
├── src/                     # Application source code
│   ├── lambda/              # Lambda function code
│   ├── glue/                # Glue job scripts
│   └── utils/               # Shared utilities
├── tests/                   # Test files
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── .github/                 # GitHub Actions workflows
├── docs/                    # Documentation
└── cdk.json                 # CDK configuration
```

## Development

### Local Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black .
isort .

# Type checking
mypy .

# Security scanning
bandit -r .
```

### Adding a New Data Source

1. Create a new connector in `src/lambda/connectors/`
2. Update the ingestion Lambda function
3. Add necessary IAM permissions in the infrastructure stack
4. Update the Step Functions workflow to include the new source

### Deployment Pipeline

The project includes a CI/CD pipeline with:

1. **Continuous Integration**: Automated testing, linting, and security scanning
2. **Continuous Deployment**: Multi-environment deployment (dev → staging → prod)
3. **Approval Gates**: Manual approval required for production deployment
4. **Rollback**: Automated rollback on deployment failure

## Monitoring and Observability

{% if cookiecutter.use_monitoring == 'y' %}
The pipeline includes comprehensive monitoring:

- **CloudWatch Dashboards**: Real-time metrics and logs
- **Alarms**: Automated alerting for failures and performance issues
- **Logs**: Centralized logging with structured format
- **Tracing**: X-Ray tracing for performance analysis
{% else %}
Monitoring can be enabled by setting `use_monitoring` to `y` in the project configuration.
{% endif %}

## Security

The pipeline implements security best practices:

- **Encryption**: Data encrypted at rest and in transit
- **IAM**: Least privilege access control
- **Network**: VPC isolation with private subnets
- **Secrets**: Secure secrets management
- **Scanning**: Automated vulnerability scanning

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Created with DevSecOps Platform CLI on {{ cookiecutter.created_date }}
