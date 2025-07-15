#!/usr/bin/env python3
"""
DevSecOps Platform for Data & AI Organization
Main CDK application entry point
"""

import os
from typing import Dict, Any

import aws_cdk as cdk
from aws_cdk import Environment

from infrastructure.config.settings import get_settings
from infrastructure.stacks.core_infrastructure_stack import CoreInfrastructureStack
from infrastructure.stacks.security_stack import SecurityStack
from infrastructure.stacks.data_pipeline_stack import DataPipelineStack
from infrastructure.stacks.monitoring_stack import MonitoringStack
from infrastructure.stacks.portal_stack import PortalStack
from infrastructure.stacks.ai_tools_stack import AIToolsStack


def get_environment_config(env_name: str) -> Dict[str, Any]:
    """Get environment-specific configuration."""
    settings = get_settings()

    # Set the environment in settings
    settings.environment = env_name

    # Get environment config from settings
    env_config = settings.get_environment_config()

    # Add account and environment name
    account_id = None
    if env_name == "dev":
        account_id = settings.dev_account_id
    elif env_name == "staging":
        account_id = settings.staging_account_id
    elif env_name == "prod":
        account_id = settings.prod_account_id

    env_config["account"] = account_id
    env_config["region"] = settings.aws_region
    env_config["environment_name"] = env_name

    return env_config


def main():
    """Main application entry point."""
    app = cdk.App()
    
    # Get environment from context or environment variable
    env_name = app.node.try_get_context("environment") or os.environ.get("CDK_ENVIRONMENT", "dev")
    env_config = get_environment_config(env_name)
    
    # Create CDK environment
    env = Environment(
        account=env_config["account"],
        region=env_config["region"]
    )
    
    # Common tags for all resources
    common_tags = {
        "Project": "DevSecOps-Platform",
        "Environment": env_config["environment_name"],
        "Owner": "Data-AI-Platform-Team",
        "CostCenter": "Engineering",
        "Compliance": "Required"
    }
    
    # Core Infrastructure Stack
    core_stack = CoreInfrastructureStack(
        app,
        f"CoreInfrastructure-{env_config['environment_name']}",
        env=env,
        env_config=env_config,
        description=f"Core infrastructure for DevSecOps platform ({env_config['environment_name']})"
    )
    
    # Security Stack
    security_stack = SecurityStack(
        app,
        f"Security-{env_config['environment_name']}",
        env=env,
        env_config=env_config,
        vpc=core_stack.vpc,
        description=f"Security infrastructure for DevSecOps platform ({env_config['environment_name']})"
    )
    
    # Data Pipeline Stack
    data_pipeline_stack = DataPipelineStack(
        app,
        f"DataPipeline-{env_config['environment_name']}",
        env=env,
        env_config=env_config,
        vpc=core_stack.vpc,
        security_groups=security_stack.security_groups,
        description=f"Data pipeline infrastructure ({env_config['environment_name']})"
    )
    
    # Monitoring Stack
    monitoring_stack = MonitoringStack(
        app,
        f"Monitoring-{env_config['environment_name']}",
        env=env,
        env_config=env_config,
        vpc=core_stack.vpc,
        description=f"Monitoring and observability infrastructure ({env_config['environment_name']})"
    )
    
    # Portal Stack
    portal_stack = PortalStack(
        app,
        f"Portal-{env_config['environment_name']}",
        env=env,
        env_config=env_config,
        vpc=core_stack.vpc,
        security_groups=security_stack.security_groups,
        description=f"Self-service portal infrastructure ({env_config['environment_name']})"
    )
    
    # AI Tools Stack
    ai_tools_stack = AIToolsStack(
        app,
        f"AITools-{env_config['environment_name']}",
        env=env,
        env_config=env_config,
        vpc=core_stack.vpc,
        description=f"AI-powered development tools ({env_config['environment_name']})"
    )
    
    # Add dependencies
    security_stack.add_dependency(core_stack)
    data_pipeline_stack.add_dependency(security_stack)
    monitoring_stack.add_dependency(core_stack)
    portal_stack.add_dependency(security_stack)
    ai_tools_stack.add_dependency(core_stack)
    
    # Apply common tags to all stacks
    for stack in [core_stack, security_stack, data_pipeline_stack, 
                  monitoring_stack, portal_stack, ai_tools_stack]:
        for key, value in common_tags.items():
            cdk.Tags.of(stack).add(key, value)
    
    app.synth()


if __name__ == "__main__":
    main()
