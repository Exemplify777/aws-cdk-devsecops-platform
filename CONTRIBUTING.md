# Contributing to DevSecOps Platform

We welcome contributions to the DevSecOps Platform for Data & AI Organization! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Security](#security)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

### Our Standards

- Be respectful and inclusive
- Focus on constructive feedback
- Collaborate effectively
- Maintain professionalism
- Respect different viewpoints and experiences

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- AWS CLI configured
- Git
- Docker (for local development)

### Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/your-username/mcp-cdk-ddk.git
   cd mcp-cdk-ddk
   ```

2. **Set Up Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   pip install -e .
   ```

3. **Install Pre-commit Hooks**:
   ```bash
   pre-commit install
   ```

4. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run Tests**:
   ```bash
   pytest
   ```

## Contributing Process

### 1. Create an Issue

Before starting work, create an issue to discuss:
- Bug reports
- Feature requests
- Documentation improvements
- Performance enhancements

### 2. Fork and Branch

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/your-username/mcp-cdk-ddk.git

# Create a feature branch
git checkout -b feature/your-feature-name
```

### 3. Make Changes

- Follow coding standards
- Write tests for new functionality
- Update documentation
- Ensure security best practices

### 4. Test Your Changes

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run security scans
python security/scanner.py scan .

# Run compliance checks
python security/compliance.py check
```

### 5. Submit Pull Request

1. Push your branch to your fork
2. Create a pull request against the main branch
3. Fill out the pull request template
4. Wait for review and address feedback

## Coding Standards

### Python Code Style

We follow PEP 8 with some modifications:

```python
# Use Black for formatting
black --line-length 88 .

# Use isort for import sorting
isort .

# Use mypy for type checking
mypy .

# Use pylint for linting
pylint infrastructure/ platform/ security/
```

### Code Quality Requirements

- **Type Hints**: All functions must have type hints
- **Docstrings**: All public functions and classes must have docstrings
- **Error Handling**: Proper exception handling and logging
- **Security**: Follow security best practices
- **Performance**: Consider performance implications

### Example Code Structure

```python
"""
Module docstring describing the purpose and functionality.
"""

import os
from typing import Dict, List, Optional, Any
from pathlib import Path

import boto3
from aws_cdk import Stack
from constructs import Construct


class ExampleStack(Stack):
    """
    Example CDK stack demonstrating coding standards.
    
    This stack creates example resources following best practices
    for security, monitoring, and maintainability.
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_config: Dict[str, Any],
        **kwargs
    ) -> None:
        """
        Initialize the example stack.
        
        Args:
            scope: The scope in which to define this construct
            construct_id: The scoped construct ID
            env_config: Environment-specific configuration
            **kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_config = env_config
        self.environment_name = env_config["environment_name"]
        
        # Create resources
        self._create_resources()
    
    def _create_resources(self) -> None:
        """Create stack resources."""
        # Implementation here
        pass
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── test_stacks/       # CDK stack tests
│   ├── test_cli/          # CLI tests
│   └── test_security/     # Security tests
├── integration/           # Integration tests
├── infrastructure/        # Infrastructure tests
├── smoke/                # Smoke tests
└── conftest.py           # Pytest configuration
```

### Writing Tests

```python
"""Test example demonstrating testing standards."""

import pytest
from unittest.mock import Mock, patch
from moto import mock_s3

from infrastructure.stacks.example_stack import ExampleStack


class TestExampleStack:
    """Test suite for ExampleStack."""
    
    @pytest.fixture
    def env_config(self):
        """Provide test environment configuration."""
        return {
            "environment_name": "test",
            "project_name": "test-project",
            "aws_region": "us-east-1"
        }
    
    @mock_s3
    def test_stack_creation(self, env_config):
        """Test stack creates resources correctly."""
        # Arrange
        app = App()
        
        # Act
        stack = ExampleStack(app, "TestStack", env_config)
        
        # Assert
        template = Template.from_stack(stack)
        template.has_resource_properties("AWS::S3::Bucket", {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }
        })
    
    def test_invalid_configuration(self):
        """Test stack handles invalid configuration."""
        # Test error handling
        with pytest.raises(ValueError):
            ExampleStack(App(), "TestStack", {})
```

### Test Requirements

- **Coverage**: Minimum 80% code coverage
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Mocking**: Use mocks for external dependencies
- **Assertions**: Clear and specific assertions
- **Documentation**: Document test purpose and setup

## Documentation

### Documentation Standards

- **README**: Keep README.md up to date
- **API Documentation**: Document all public APIs
- **Architecture**: Maintain architecture documentation
- **Examples**: Provide working examples
- **Changelog**: Update CHANGELOG.md for releases

### Writing Documentation

```markdown
# Component Name

Brief description of the component's purpose.

## Overview

Detailed explanation of what the component does and why it exists.

## Usage

```python
# Example usage
from platform.component import Component

component = Component(config)
result = component.process(data)
```

## Configuration

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `config` | `Dict` | Yes | Configuration dictionary |
| `timeout` | `int` | No | Timeout in seconds (default: 300) |

## Examples

### Basic Usage

```python
# Basic example
component = Component({"key": "value"})
```

### Advanced Usage

```python
# Advanced example with error handling
try:
    component = Component(config)
    result = component.process(data)
except ComponentError as e:
    logger.error(f"Processing failed: {e}")
```
```

## Security

### Security Requirements

- **No Secrets**: Never commit secrets or credentials
- **Input Validation**: Validate all inputs
- **Error Handling**: Don't expose sensitive information in errors
- **Dependencies**: Keep dependencies up to date
- **Scanning**: Run security scans before submitting

### Security Checklist

- [ ] No hardcoded secrets or credentials
- [ ] Input validation implemented
- [ ] Error messages don't expose sensitive data
- [ ] Dependencies are up to date
- [ ] Security scan passes
- [ ] Compliance checks pass

## Release Process

### Version Numbering

We use Semantic Versioning (SemVer):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps

1. **Update Version**: Update version in `pyproject.toml`
2. **Update Changelog**: Add release notes to `CHANGELOG.md`
3. **Create Release**: Create GitHub release with tag
4. **Deploy**: Automated deployment via GitHub Actions

## Getting Help

- **Documentation**: [Complete Documentation](https://your-org.github.io/mcp-cdk-ddk)
- **Issues**: [GitHub Issues](https://github.com/your-org/mcp-cdk-ddk/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/mcp-cdk-ddk/discussions)
- **Slack**: [#devsecops-platform](https://your-org.slack.com/channels/devsecops-platform)

## Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- Project documentation
- Community highlights

Thank you for contributing to the DevSecOps Platform!
