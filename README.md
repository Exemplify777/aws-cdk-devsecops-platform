# DevSecOps Platform for Data & AI Organization

A comprehensive DevSecOps solution built with AWS CDK and Python, designed specifically for data engineering teams developing ETL/ELT pipelines, ML workflows, and data processing jobs.

## 🚀 Features

### Core Capabilities
- **Project Initialization System**: CLI tool for automated project setup with pre-configured templates
- **CI/CD Pipeline**: GitHub Actions workflows with automated testing, security scanning, and multi-environment deployment
- **AI-Powered Development**: AWS MCP integration for intelligent code generation and error analysis
- **Security & Compliance**: Security-by-design with automated SAST/DAST scanning and compliance validation
- **Self-Service Portal**: Web interface for project management and resource monitoring
- **Comprehensive Observability**: CloudWatch integration with AI-assisted troubleshooting

### Architecture Principles
- **AWS Well-Architected Framework**: Security, Reliability, Performance, Cost Optimization, Operational Excellence, Sustainability
- **Security-by-Design**: Least-privilege IAM, encryption at rest/transit, automated vulnerability scanning
- **Infrastructure as Code**: Complete AWS CDK implementation with Python
- **Multi-Environment**: Dev → Staging → Production deployment pipeline
- **Scalable & Resilient**: Auto-scaling, disaster recovery, and cost optimization

## 📁 Project Structure

```
mcp-cdk-ddk/
├── infrastructure/          # AWS CDK infrastructure code
│   ├── stacks/             # CDK stack definitions
│   ├── constructs/         # Reusable CDK constructs
│   └── config/             # Environment configurations
├── platform/               # Platform services and tools
│   ├── cli/                # Project generator CLI
│   ├── portal/             # Self-service web portal
│   └── ai-tools/           # AI-powered development tools
├── templates/              # Project templates
│   ├── data-pipeline/      # ETL/ELT pipeline templates
│   ├── ml-workflow/        # ML pipeline templates
│   └── streaming/          # Real-time processing templates
├── .github/                # GitHub Actions workflows
├── monitoring/             # Observability configurations
├── security/               # Security policies and tools
├── docs/                   # Documentation
└── tests/                  # Test suites
```

## 🛠️ Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- AWS CLI configured
- AWS CDK CLI installed
- Docker (for local development)

### Installation

1. **Clone and setup the repository:**
```bash
git clone <repository-url>
cd mcp-cdk-ddk
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Install AWS CDK:**
```bash
npm install -g aws-cdk
cdk bootstrap
```

3. **Deploy the platform:**
```bash
# Deploy to development environment
cdk deploy --all --profile dev

# Deploy to production (requires approval)
cdk deploy --all --profile prod --require-approval=broadening
```

### Creating Your First Data Pipeline

```bash
# Use the CLI tool to create a new project
python -m platform.cli create-project \
  --name my-data-pipeline \
  --type etl \
  --template batch-processing \
  --environment dev
```

## 🔧 Development

### Local Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run security scans
bandit -r infrastructure/ platform/
safety check

# Format code
black .
isort .
```

### Infrastructure Development
```bash
# Synthesize CloudFormation templates
cdk synth

# Deploy specific stack
cdk deploy DataPipelineStack

# View differences
cdk diff
```

## 📊 Monitoring & Observability

- **CloudWatch Dashboards**: Real-time metrics and logs
- **Automated Alerting**: Intelligent alert routing with escalation
- **Cost Monitoring**: Resource usage and optimization recommendations
- **Data Quality**: ML-based anomaly detection
- **Performance**: Application and infrastructure monitoring

## 🔒 Security

- **IAM**: Least-privilege access with automated role management
- **Encryption**: Data encrypted at rest and in transit
- **Scanning**: Automated SAST/DAST in CI/CD pipeline
- **Compliance**: Automated policy validation and audit logging
- **Vulnerability Management**: Dependency scanning and remediation

## 📚 Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Architecture Overview](docs/architecture.md)
- [Security Best Practices](docs/security.md)
- [API Documentation](docs/api.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🤝 Contributing

Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Emergency**: Contact the platform team

---

Built with ❤️ for Data & AI Engineering Teams
