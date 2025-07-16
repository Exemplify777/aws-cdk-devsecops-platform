"""
Template Management for Project Generation
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional


class TemplateManager:
    """Manages project templates."""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or self._get_default_templates_dir()
    
    def _get_default_templates_dir(self) -> Path:
        """Get default templates directory."""
        # Assume templates are in the project root
        current_dir = Path(__file__).parent.parent.parent
        return current_dir / "templates"
    
    def list_templates(self) -> List[str]:
        """List available templates."""
        if not self.templates_dir.exists():
            return []
        
        templates = []
        for item in self.templates_dir.iterdir():
            if item.is_dir() and (item / "cookiecutter.json").exists():
                templates.append(item.name)
        
        return sorted(templates)
    
    def template_exists(self, template_name: str) -> bool:
        """Check if template exists."""
        template_path = self.templates_dir / template_name
        return template_path.exists() and (template_path / "cookiecutter.json").exists()
    
    def get_template_path(self, template_name: str) -> Path:
        """Get path to template."""
        return self.templates_dir / template_name
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get template information."""
        template_path = self.get_template_path(template_name)
        
        if not self.template_exists(template_name):
            return {}
        
        # Read cookiecutter.json for template info
        cookiecutter_file = template_path / "cookiecutter.json"
        try:
            with open(cookiecutter_file, 'r') as f:
                config = json.load(f)
            
            # Read template metadata if available
            metadata_file = template_path / "template.json"
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            return {
                "name": template_name,
                "description": metadata.get("description", config.get("description", "No description")),
                "type": metadata.get("type", "data-pipeline"),
                "version": metadata.get("version", "1.0.0"),
                "author": metadata.get("author", "DevSecOps Platform"),
                "tags": metadata.get("tags", []),
                "requirements": metadata.get("requirements", {}),
                "config": config,
            }
        
        except (json.JSONDecodeError, IOError):
            return {
                "name": template_name,
                "description": "Template information unavailable",
                "type": "unknown",
            }
    
    def create_template(self, name: str, description: str, template_type: str = "data-pipeline") -> Path:
        """Create a new template."""
        template_path = self.templates_dir / name
        
        if template_path.exists():
            raise ValueError(f"Template '{name}' already exists")
        
        template_path.mkdir(parents=True)
        
        # Create cookiecutter.json
        cookiecutter_config = {
            "project_name": "my-project",
            "project_slug": "{{ cookiecutter.project_name.lower().replace(' ', '-').replace('_', '-') }}",
            "description": "A data pipeline project",
            "author": "{{ cookiecutter.author_name }}",
            "author_email": "{{ cookiecutter.author_email }}",
            "version": "0.1.0",
            "environment": "dev",
            "aws_region": "us-east-1",
            "github_org": "",
            "python_version": "3.11",
            "use_docker": "y",
            "use_github_actions": "y",
            "use_monitoring": "y",
        }
        
        with open(template_path / "cookiecutter.json", 'w') as f:
            json.dump(cookiecutter_config, f, indent=2)
        
        # Create template metadata
        metadata = {
            "name": name,
            "description": description,
            "type": template_type,
            "version": "1.0.0",
            "author": "DevSecOps Platform",
            "created_at": "{{ cookiecutter.created_date }}",
            "tags": [template_type, "aws", "cdk", "python"],
            "requirements": {
                "python": ">=3.9",
                "aws_cdk": ">=2.100.0",
            }
        }
        
        with open(template_path / "template.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create template structure
        project_dir = template_path / "{{ cookiecutter.project_slug }}"
        project_dir.mkdir()
        
        self._create_template_structure(project_dir, template_type)
        
        return template_path
    
    def _create_template_structure(self, project_dir: Path, template_type: str) -> None:
        """Create template project structure."""
        # Common structure
        directories = [
            "infrastructure/stacks",
            "infrastructure/constructs",
            "src",
            "tests/unit",
            "tests/integration",
            "docs",
            ".github/workflows",
        ]
        
        for directory in directories:
            (project_dir / directory).mkdir(parents=True, exist_ok=True)
        
        # Create basic files
        files = {
            "README.md": self._get_readme_template(),
            "requirements.txt": self._get_requirements_template(),
            "app.py": self._get_app_template(template_type),
            "cdk.json": self._get_cdk_json_template(),
            ".gitignore": self._get_gitignore_template(),
            "pyproject.toml": self._get_pyproject_template(),
            ".github/workflows/ci.yml": self._get_ci_workflow_template(),
            "tests/unit/test_stack.py": self._get_test_template(),
        }
        
        for file_path, content in files.items():
            full_path = project_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
    
    def _get_readme_template(self) -> str:
        return """# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Deploy infrastructure:
```bash
cdk deploy
```

## Project Structure

```
{{ cookiecutter.project_slug }}/
├── infrastructure/     # CDK infrastructure code
├── src/               # Application source code
├── tests/             # Test files
├── docs/              # Documentation
└── .github/           # GitHub Actions workflows
```

## Development

### Prerequisites
- Python {{ cookiecutter.python_version }}+
- AWS CLI configured
- AWS CDK CLI

### Local Development
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Deploy to dev environment
cdk deploy --context environment=dev
```

## Deployment

### Environments
- **dev**: Development environment
- **staging**: Staging environment  
- **prod**: Production environment

### Deploy to specific environment
```bash
cdk deploy --context environment=staging
```

## Monitoring

The project includes comprehensive monitoring with:
- CloudWatch dashboards
- Automated alerting
- Log aggregation
- Performance metrics

## Security

Security features include:
- Encryption at rest and in transit
- IAM least privilege access
- VPC network isolation
- Automated security scanning

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
"""
    
    def _get_requirements_template(self) -> str:
        return """# AWS CDK
aws-cdk-lib>=2.100.0
constructs>=10.0.0

# AWS SDK
boto3>=1.28.0

# Development tools
pytest>=7.4.0
black>=23.7.0
isort>=5.12.0
mypy>=1.5.0
"""
    
    def _get_app_template(self, template_type: str) -> str:
        return f"""#!/usr/bin/env python3
\"\"\"
{{ cookiecutter.project_name }}
CDK Application Entry Point
\"\"\"

import aws_cdk as cdk
from infrastructure.stacks.main_stack import MainStack

app = cdk.App()

# Get environment configuration
environment = app.node.try_get_context("environment") or "dev"

# Create main stack
MainStack(
    app,
    f"{{{{ cookiecutter.project_slug }}}}-{{environment}}",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region="{{ cookiecutter.aws_region }}"
    ),
    environment=environment,
)

app.synth()
"""
    
    def _get_cdk_json_template(self) -> str:
        return """{
  "app": "python app.py",
  "watch": {
    "include": ["**"],
    "exclude": ["README.md", "cdk*.json", "requirements*.txt", "**/__pycache__", "**/.venv"]
  },
  "context": {
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true,
    "@aws-cdk/core:checkSecretUsage": true,
    "@aws-cdk/core:target-partitions": ["aws", "aws-cn"],
    "@aws-cdk/aws-iam:minimizePolicies": true,
    "@aws-cdk/core:validateSnapshotRemovalPolicy": true,
    "@aws-cdk/aws-s3:createDefaultLoggingPolicy": true,
    "@aws-cdk/core:enablePartitionLiterals": true,
    "@aws-cdk/aws-ec2:restrictDefaultSecurityGroup": true
  }
}"""
    
    def _get_gitignore_template(self) -> str:
        return """# CDK
cdk.out/
cdk.context.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/

# Secrets
*.pem
*.key
secrets.json
.secrets/
"""
    
    def _get_pyproject_template(self) -> str:
        return """[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{{ cookiecutter.project_slug }}"
version = "{{ cookiecutter.version }}"
description = "{{ cookiecutter.description }}"
authors = [
    {name = "{{ cookiecutter.author }}", email = "{{ cookiecutter.author_email }}"}
]
requires-python = ">={{ cookiecutter.python_version }}"

[tool.black]
line-length = 88
target-version = ['py39', 'py310', 'py311']

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88

[tool.mypy]
python_version = "{{ cookiecutter.python_version }}"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
"""
    
    def _get_ci_workflow_template(self) -> str:
        return """name: CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '{{ cookiecutter.python_version }}'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest black isort mypy
    - name: Run tests
      run: pytest
    - name: Code quality
      run: |
        black --check .
        isort --check-only .
        mypy .

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '{{ cookiecutter.python_version }}'
    - name: Install CDK
      run: npm install -g aws-cdk
    - name: Deploy
      run: cdk deploy --require-approval=never
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        AWS_DEFAULT_REGION: {{ cookiecutter.aws_region }}
"""
    
    def _get_test_template(self) -> str:
        return """import pytest
from aws_cdk import App
from infrastructure.stacks.main_stack import MainStack

def test_stack_creation():
    app = App()
    stack = MainStack(app, "test-stack", environment="test")
    # Add your tests here
    assert stack is not None
"""
