#!/usr/bin/env python3
"""
{{ cookiecutter.project_name }}
CDK Application Entry Point
"""

import os
from typing import Dict, Any

import aws_cdk as cdk
from aws_cdk import Environment

from infrastructure.stacks.data_pipeline_stack import DataPipelineStack
from infrastructure.stacks.monitoring_stack import MonitoringStack
from infrastructure.stacks.security_stack import SecurityStack


def get_environment_config(env_name: str) -> Dict[str, Any]:
    """Get environment-specific configuration."""
    environments = {
        "dev": {
            "environment_name": "dev",
            "vpc_cidr": "10.0.0.0/16",
            "availability_zones": ["{{ cookiecutter.aws_region }}a", "{{ cookiecutter.aws_region }}b"],
            "enable_deletion_protection": False,
            "enable_backup": False,
            "instance_types": {
                "small": "t3.micro",
                "medium": "t3.small",
                "large": "t3.medium"
            },
            "min_capacity": 1,
            "max_capacity": 2,
            "desired_capacity": 1,
        },
        "staging": {
            "environment_name": "staging",
            "vpc_cidr": "10.1.0.0/16",
            "availability_zones": ["{{ cookiecutter.aws_region }}a", "{{ cookiecutter.aws_region }}b"],
            "enable_deletion_protection": True,
            "enable_backup": True,
            "instance_types": {
                "small": "t3.small",
                "medium": "t3.medium",
                "large": "t3.large"
            },
            "min_capacity": 2,
            "max_capacity": 4,
            "desired_capacity": 2,
        },
        "prod": {
            "environment_name": "prod",
            "vpc_cidr": "10.2.0.0/16",
            "availability_zones": ["{{ cookiecutter.aws_region }}a", "{{ cookiecutter.aws_region }}b", "{{ cookiecutter.aws_region }}c"],
            "enable_deletion_protection": True,
            "enable_backup": True,
            "instance_types": {
                "small": "t3.medium",
                "medium": "t3.large",
                "large": "t3.xlarge"
            },
            "min_capacity": 2,
            "max_capacity": 6,
            "desired_capacity": 2,
        }
    }
    
    return environments.get(env_name, environments["dev"])


def main():
    """Main application entry point."""
    app = cdk.App()
    
    # Get environment from context or environment variable
    env_name = app.node.try_get_context("environment") or os.environ.get("CDK_ENVIRONMENT", "dev")
    env_config = get_environment_config(env_name)
    
    # Create CDK environment
    env = Environment(
        account=app.node.try_get_context("account") or os.environ.get("CDK_ACCOUNT", os.environ.get("CDK_DEFAULT_ACCOUNT")),
        region=app.node.try_get_context("region") or os.environ.get("CDK_REGION", "{{ cookiecutter.aws_region }}")
    )
    
    # Common tags for all resources
    common_tags = {
        "Project": "{{ cookiecutter.project_slug }}",
        "Environment": env_config["environment_name"],
        "Owner": "{{ cookiecutter.author_name }}",
        "ManagedBy": "CDK",
        "CreatedBy": "DevSecOps-Platform-CLI",
    }
    
    # Security Stack
    security_stack = SecurityStack(
        app,
        f"{{ cookiecutter.project_slug }}-security-{env_config['environment_name']}",
        env=env,
        env_config=env_config,
        description=f"Security infrastructure for {{ cookiecutter.project_name }} ({env_config['environment_name']})"
    )
    
    # Data Pipeline Stack
    data_pipeline_stack = DataPipelineStack(
        app,
        f"{{ cookiecutter.project_slug }}-pipeline-{env_config['environment_name']}",
        env=env,
        env_config=env_config,
        vpc=security_stack.vpc,
        security_groups=security_stack.security_groups,
        description=f"Data pipeline infrastructure for {{ cookiecutter.project_name }} ({env_config['environment_name']})"
    )
    
    # Monitoring Stack (optional)
    {% if cookiecutter.use_monitoring == 'y' %}
    monitoring_stack = MonitoringStack(
        app,
        f"{{ cookiecutter.project_slug }}-monitoring-{env_config['environment_name']}",
        env=env,
        env_config=env_config,
        vpc=security_stack.vpc,
        data_pipeline_stack=data_pipeline_stack,
        description=f"Monitoring infrastructure for {{ cookiecutter.project_name }} ({env_config['environment_name']})"
    )
    {% endif %}
    
    # Add dependencies
    data_pipeline_stack.add_dependency(security_stack)
    {% if cookiecutter.use_monitoring == 'y' %}
    monitoring_stack.add_dependency(data_pipeline_stack)
    {% endif %}
    
    # Apply common tags to all stacks
    for stack in [security_stack, data_pipeline_stack{% if cookiecutter.use_monitoring == 'y' %}, monitoring_stack{% endif %}]:
        for key, value in common_tags.items():
            cdk.Tags.of(stack).add(key, value)
    
    app.synth()


if __name__ == "__main__":
    main()
