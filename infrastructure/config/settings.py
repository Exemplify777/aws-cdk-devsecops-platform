"""
Configuration settings for the DevSecOps platform
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings with environment-specific configurations."""
    
    # Environment Configuration
    environment: str = Field(default="dev", description="Deployment environment")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    
    # Account IDs
    dev_account_id: Optional[str] = Field(default=None, description="Development AWS account ID")
    staging_account_id: Optional[str] = Field(default=None, description="Staging AWS account ID")
    prod_account_id: Optional[str] = Field(default=None, description="Production AWS account ID")
    
    # Project Configuration
    project_name: str = Field(default="devsecops-platform", description="Project name")
    organization: str = Field(default="data-ai-org", description="Organization name")
    
    # VPC Configuration
    vpc_cidr: str = Field(default="10.0.0.0/16", description="VPC CIDR block")
    availability_zones: List[str] = Field(default=["us-east-1a", "us-east-1b"], description="Availability zones")
    
    # Security Configuration
    enable_vpc_flow_logs: bool = Field(default=True, description="Enable VPC flow logs")
    enable_cloudtrail: bool = Field(default=True, description="Enable CloudTrail")
    enable_config: bool = Field(default=True, description="Enable AWS Config")
    enable_guardduty: bool = Field(default=True, description="Enable GuardDuty")
    enable_security_hub: bool = Field(default=True, description="Enable Security Hub")
    
    # Monitoring Configuration
    enable_detailed_monitoring: bool = Field(default=True, description="Enable detailed monitoring")
    log_retention_days: int = Field(default=30, description="CloudWatch log retention in days")
    
    # Database Configuration
    db_instance_class: str = Field(default="db.t3.micro", description="RDS instance class")
    db_allocated_storage: int = Field(default=20, description="RDS allocated storage in GB")
    db_backup_retention: int = Field(default=7, description="RDS backup retention in days")
    
    # Container Configuration
    container_cpu: int = Field(default=256, description="ECS task CPU units")
    container_memory: int = Field(default=512, description="ECS task memory in MB")
    
    # Lambda Configuration
    lambda_timeout: int = Field(default=300, description="Lambda timeout in seconds")
    lambda_memory: int = Field(default=128, description="Lambda memory in MB")
    
    # API Configuration
    api_throttle_rate: int = Field(default=1000, description="API Gateway throttle rate")
    api_throttle_burst: int = Field(default=2000, description="API Gateway throttle burst")
    
    # Cost Management
    cost_alert_threshold: float = Field(default=100.0, description="Cost alert threshold in USD")
    
    # Notification Configuration
    notification_email: Optional[str] = Field(default=None, description="Notification email address")
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    
    # GitHub Configuration
    github_org: Optional[str] = Field(default=None, description="GitHub organization")
    github_token: Optional[str] = Field(default=None, description="GitHub token")
    
    # AI/ML Configuration
    enable_sagemaker: bool = Field(default=True, description="Enable SageMaker")
    enable_bedrock: bool = Field(default=True, description="Enable Amazon Bedrock")
    
    # Feature Flags
    enable_ai_tools: bool = Field(default=True, description="Enable AI-powered tools")
    enable_portal: bool = Field(default=True, description="Enable self-service portal")
    enable_advanced_monitoring: bool = Field(default=True, description="Enable advanced monitoring")
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed_envs = ["dev", "staging", "prod"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of {allowed_envs}")
        return v
    
    @validator("vpc_cidr")
    def validate_vpc_cidr(cls, v):
        """Validate VPC CIDR format."""
        import ipaddress
        try:
            ipaddress.IPv4Network(v)
        except ipaddress.AddressValueError:
            raise ValueError("Invalid VPC CIDR format")
        return v
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration."""
        base_config = {
            "project_name": self.project_name,
            "organization": self.organization,
            "aws_region": self.aws_region,
            "vpc_cidr": self.vpc_cidr,
            "availability_zones": self.availability_zones,
        }
        
        env_configs = {
            "dev": {
                **base_config,
                "enable_deletion_protection": False,
                "enable_backup": False,
                "instance_types": {
                    "small": "t3.micro",
                    "medium": "t3.small",
                    "large": "t3.medium"
                },
                "min_capacity": 1,
                "max_capacity": 3,
                "desired_capacity": 1,
            },
            "staging": {
                **base_config,
                "enable_deletion_protection": True,
                "enable_backup": True,
                "instance_types": {
                    "small": "t3.small",
                    "medium": "t3.medium",
                    "large": "t3.large"
                },
                "min_capacity": 2,
                "max_capacity": 6,
                "desired_capacity": 2,
            },
            "prod": {
                **base_config,
                "enable_deletion_protection": True,
                "enable_backup": True,
                "instance_types": {
                    "small": "t3.medium",
                    "medium": "t3.large",
                    "large": "t3.xlarge"
                },
                "min_capacity": 3,
                "max_capacity": 10,
                "desired_capacity": 3,
            }
        }
        
        return env_configs.get(self.environment, env_configs["dev"])
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings
