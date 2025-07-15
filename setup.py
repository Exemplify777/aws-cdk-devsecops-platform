"""
Setup configuration for DevSecOps Platform CLI
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
def read_requirements(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

requirements = read_requirements("requirements.txt")

setup(
    name="ddk-cli",
    version="1.0.0",
    author="Data & AI Platform Team",
    author_email="data-platform@company.com",
    description="DevSecOps Platform CLI for Data & AI Organization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/mcp-cdk-ddk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
            "pylint>=2.17.0",
            "bandit>=1.7.5",
            "safety>=2.3.0",
            "pre-commit>=3.3.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.1.0",
            "mkdocs-mermaid2-plugin>=0.6.0",
        ],
        "security": [
            "bandit>=1.7.5",
            "safety>=2.3.0",
            "semgrep>=1.32.0",
            "checkov>=2.3.0",
            "detect-secrets>=1.4.0",
            "pip-audit>=2.6.0",
            "pip-licenses>=4.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ddk-cli=platform.cli.main:app",
            "security-scanner=security.scanner:app",
            "compliance-checker=security.compliance:app",
        ],
    },
    include_package_data=True,
    package_data={
        "platform": ["cli/templates/**/*"],
        "security": ["rules/*.yaml"],
        "templates": ["**/*"],
    },
    zip_safe=False,
    keywords="devsecops, aws, cdk, data-engineering, ai, ml, security, compliance",
    project_urls={
        "Bug Reports": "https://github.com/your-org/mcp-cdk-ddk/issues",
        "Source": "https://github.com/your-org/mcp-cdk-ddk",
        "Documentation": "https://your-org.github.io/mcp-cdk-ddk",
    },
)
