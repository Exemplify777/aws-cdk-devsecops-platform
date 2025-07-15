"""
Environment configuration management for DevSecOps Platform constructs.

This module provides comprehensive environment-specific configuration management
with support for multi-environment deployments and environment-specific overrides.
"""

from typing import Dict, Any, Optional, List
import os
import json
import yaml
from pathlib import Path

from .types import Environment, SecurityLevel, MonitoringLevel, DataClassification


class EnvironmentConfig:
    """
    Environment-specific configuration manager.
    
    Provides centralized configuration management for different deployment
    environments with support for overrides and validation.
    """
    
    def __init__(self, environment: Environment):
        """
        Initialize environment configuration.
        
        Args:
            environment: The deployment environment
        """
        self.environment = environment
        self._config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from multiple sources."""
        config = {}
        
        # Load base configuration
        config.update(self._get_base_config())
        
        # Load environment-specific configuration
        config.update(self._get_environment_config())
        
        # Load overrides from environment variables
        config.update(self._get_env_var_overrides())
        
        # Load overrides from config files
        config.update(self._get_file_overrides())
        
        return config
    
    def _get_base_config(self) -> Dict[str, Any]:
        """Get base configuration common to all environments."""
        return {
            "aws": {
                "region": "us-east-1",
                "availability_zones": 2,
                "enable_dns_hostnames": True,
                "enable_dns_support": True
            },
            "vpc": {
                "cidr": "10.0.0.0/16",
                "enable_nat_gateway": True,
                "enable_vpn_gateway": False,
                "enable_flow_logs": True
            },
            "security": {
                "level": SecurityLevel.STANDARD.value,
                "encryption_enabled": True,
                "mfa_required": True,
                "password_policy_enabled": True,
                "cloudtrail_enabled": True,
                "config_enabled": True,
                "guardduty_enabled": True
            },
            "monitoring": {
                "level": MonitoringLevel.STANDARD.value,
                "cloudwatch_enabled": True,
                "xray_enabled": True,
                "detailed_monitoring": False,
                "log_retention_days": 30
            },
            "backup": {
                "enabled": True,
                "retention_days": 30,
                "cross_region": False,
                "point_in_time_recovery": True
            },
            "cost": {
                "budget_enabled": True,
                "cost_alerts_enabled": True,
                "reserved_instances": False,
                "spot_instances": False
            },
            "compliance": {
                "frameworks": ["soc2"],
                "data_classification": DataClassification.INTERNAL.value,
                "audit_enabled": True
            }
        }
    
    def _get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration overrides."""
        env_configs = {
            Environment.DEV: {
                "vpc": {
                    "cidr": "10.0.0.0/16",
                    "enable_nat_gateway": False
                },
                "security": {
                    "level": SecurityLevel.BASIC.value,
                    "mfa_required": False
                },
                "monitoring": {
                    "level": MonitoringLevel.BASIC.value,
                    "detailed_monitoring": False,
                    "log_retention_days": 7
                },
                "backup": {
                    "enabled": False,
                    "retention_days": 7
                },
                "cost": {
                    "spot_instances": True,
                    "reserved_instances": False
                },
                "instance_types": {
                    "lambda_memory": 128,
                    "rds_instance": "db.t3.micro",
                    "ecs_cpu": 256,
                    "ecs_memory": 512
                }
            },
            Environment.STAGING: {
                "vpc": {
                    "cidr": "10.1.0.0/16",
                    "enable_nat_gateway": True
                },
                "security": {
                    "level": SecurityLevel.STANDARD.value,
                    "mfa_required": True
                },
                "monitoring": {
                    "level": MonitoringLevel.DETAILED.value,
                    "detailed_monitoring": True,
                    "log_retention_days": 30
                },
                "backup": {
                    "enabled": True,
                    "retention_days": 30,
                    "cross_region": False
                },
                "cost": {
                    "spot_instances": False,
                    "reserved_instances": False
                },
                "instance_types": {
                    "lambda_memory": 512,
                    "rds_instance": "db.t3.small",
                    "ecs_cpu": 512,
                    "ecs_memory": 1024
                }
            },
            Environment.PROD: {
                "vpc": {
                    "cidr": "10.2.0.0/16",
                    "enable_nat_gateway": True
                },
                "security": {
                    "level": SecurityLevel.HIGH.value,
                    "mfa_required": True,
                    "compliance_frameworks": ["soc2", "iso27001"]
                },
                "monitoring": {
                    "level": MonitoringLevel.COMPREHENSIVE.value,
                    "detailed_monitoring": True,
                    "log_retention_days": 90
                },
                "backup": {
                    "enabled": True,
                    "retention_days": 90,
                    "cross_region": True,
                    "point_in_time_recovery": True
                },
                "disaster_recovery": {
                    "enabled": True,
                    "rto_minutes": 240,
                    "rpo_minutes": 60,
                    "multi_region": True
                },
                "cost": {
                    "spot_instances": False,
                    "reserved_instances": True
                },
                "instance_types": {
                    "lambda_memory": 1024,
                    "rds_instance": "db.t3.medium",
                    "ecs_cpu": 1024,
                    "ecs_memory": 2048
                }
            }
        }
        
        return env_configs.get(self.environment, {})
    
    def _get_env_var_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables."""
        overrides = {}
        
        # AWS configuration
        if os.getenv('AWS_REGION'):
            overrides.setdefault('aws', {})['region'] = os.getenv('AWS_REGION')
        
        # VPC configuration
        if os.getenv('VPC_CIDR'):
            overrides.setdefault('vpc', {})['cidr'] = os.getenv('VPC_CIDR')
        
        # Security configuration
        if os.getenv('SECURITY_LEVEL'):
            overrides.setdefault('security', {})['level'] = os.getenv('SECURITY_LEVEL')
        
        # Monitoring configuration
        if os.getenv('LOG_RETENTION_DAYS'):
            overrides.setdefault('monitoring', {})['log_retention_days'] = int(os.getenv('LOG_RETENTION_DAYS'))
        
        # Cost configuration
        if os.getenv('ENABLE_SPOT_INSTANCES'):
            overrides.setdefault('cost', {})['spot_instances'] = os.getenv('ENABLE_SPOT_INSTANCES').lower() == 'true'
        
        return overrides
    
    def _get_file_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from config files."""
        overrides = {}
        
        # Look for environment-specific config files
        config_paths = [
            f"config/{self.environment.value}.yaml",
            f"config/{self.environment.value}.yml",
            f"config/{self.environment.value}.json",
            f".env.{self.environment.value}"
        ]
        
        for config_path in config_paths:
            if Path(config_path).exists():
                try:
                    if config_path.endswith(('.yaml', '.yml')):
                        with open(config_path, 'r') as f:
                            file_config = yaml.safe_load(f)
                    elif config_path.endswith('.json'):
                        with open(config_path, 'r') as f:
                            file_config = json.load(f)
                    else:
                        # Handle .env files
                        file_config = self._parse_env_file(config_path)
                    
                    if file_config:
                        overrides.update(file_config)
                        
                except Exception as e:
                    print(f"Warning: Could not load config file {config_path}: {e}")
        
        return overrides
    
    def _parse_env_file(self, file_path: str) -> Dict[str, Any]:
        """Parse .env file format."""
        config = {}
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Convert nested keys (e.g., AWS_REGION -> aws.region)
                    if '_' in key:
                        parts = key.lower().split('_')
                        nested_config = config
                        for part in parts[:-1]:
                            nested_config = nested_config.setdefault(part, {})
                        nested_config[parts[-1]] = value
                    else:
                        config[key.lower()] = value
        return config
    
    def _validate_config(self) -> None:
        """Validate the loaded configuration."""
        required_sections = ['aws', 'vpc', 'security', 'monitoring']
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate AWS region
        aws_region = self.get('aws.region')
        if not aws_region:
            raise ValueError("AWS region must be specified")
        
        # Validate VPC CIDR
        vpc_cidr = self.get('vpc.cidr')
        if not vpc_cidr:
            raise ValueError("VPC CIDR must be specified")
        
        # Validate security level
        security_level = self.get('security.level')
        if security_level not in [level.value for level in SecurityLevel]:
            raise ValueError(f"Invalid security level: {security_level}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'aws.region')
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        
        config[keys[-1]] = value
    
    def get_aws_config(self) -> Dict[str, Any]:
        """Get AWS-specific configuration."""
        return self.get('aws', {})
    
    def get_vpc_config(self) -> Dict[str, Any]:
        """Get VPC-specific configuration."""
        return self.get('vpc', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security-specific configuration."""
        return self.get('security', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring-specific configuration."""
        return self.get('monitoring', {})
    
    def get_backup_config(self) -> Dict[str, Any]:
        """Get backup-specific configuration."""
        return self.get('backup', {})
    
    def get_cost_config(self) -> Dict[str, Any]:
        """Get cost-specific configuration."""
        return self.get('cost', {})
    
    def get_instance_types(self) -> Dict[str, Any]:
        """Get environment-specific instance types."""
        return self.get('instance_types', {})
    
    def get_tags(self) -> Dict[str, str]:
        """Get environment-specific tags."""
        base_tags = {
            "Environment": self.environment.value,
            "ManagedBy": "DevSecOpsPlatform",
            "ConfigVersion": "1.0.0"
        }
        
        custom_tags = self.get('tags', {})
        base_tags.update(custom_tags)
        
        return base_tags
    
    def is_production(self) -> bool:
        """Check if this is a production environment."""
        return self.environment == Environment.PROD
    
    def is_development(self) -> bool:
        """Check if this is a development environment."""
        return self.environment == Environment.DEV
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get complete configuration."""
        return self._config.copy()
    
    def export_config(self, format: str = 'yaml') -> str:
        """
        Export configuration in specified format.
        
        Args:
            format: Export format ('yaml', 'json')
            
        Returns:
            Configuration as string
        """
        if format.lower() == 'json':
            return json.dumps(self._config, indent=2)
        elif format.lower() in ['yaml', 'yml']:
            return yaml.dump(self._config, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        return f"EnvironmentConfig(environment={self.environment.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"EnvironmentConfig(environment={self.environment.value}, config_keys={list(self._config.keys())})"
