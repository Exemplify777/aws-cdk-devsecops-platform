"""
Validation classes for DevSecOps Platform constructs.

This module provides comprehensive validation functionality for inputs,
security configurations, compliance requirements, and operational parameters.
"""

from typing import Dict, Any, List, Optional, Union
import re
import ipaddress
from abc import ABC, abstractmethod

from .types import ConstructProps, SecurityConfig, MonitoringConfig, Environment


class BaseValidator(ABC):
    """
    Base validator class providing common validation functionality.
    
    All specific validators inherit from this class to ensure
    consistent validation patterns and error handling.
    """
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def add_error(self, message: str) -> None:
        """Add validation error."""
        self.errors.append(message)
    
    def add_warning(self, message: str) -> None:
        """Add validation warning."""
        self.warnings.append(message)
    
    def has_errors(self) -> bool:
        """Check if there are validation errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are validation warnings."""
        return len(self.warnings) > 0
    
    def get_errors(self) -> List[str]:
        """Get all validation errors."""
        return self.errors.copy()
    
    def get_warnings(self) -> List[str]:
        """Get all validation warnings."""
        return self.warnings.copy()
    
    def clear(self) -> None:
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()
    
    def validate_and_raise(self) -> None:
        """Validate and raise exception if errors exist."""
        if self.has_errors():
            error_message = "Validation failed:\n" + "\n".join(self.errors)
            raise ValueError(error_message)


class InputValidator(BaseValidator):
    """
    Validator for general input validation.
    
    Provides validation for common input types including names,
    identifiers, configurations, and data formats.
    """
    
    def validate_project_name(self, name: str) -> bool:
        """
        Validate project name format.
        
        Args:
            name: Project name to validate
            
        Returns:
            bool: True if valid
        """
        if not name:
            self.add_error("Project name cannot be empty")
            return False
        
        if len(name) < 3 or len(name) > 63:
            self.add_error("Project name must be between 3 and 63 characters")
            return False
        
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', name):
            self.add_error("Project name must start and end with alphanumeric characters and contain only lowercase letters, numbers, and hyphens")
            return False
        
        if '--' in name:
            self.add_error("Project name cannot contain consecutive hyphens")
            return False
        
        return True
    
    def validate_environment(self, environment: str) -> bool:
        """
        Validate environment name.
        
        Args:
            environment: Environment to validate
            
        Returns:
            bool: True if valid
        """
        valid_environments = [env.value for env in Environment]
        
        if environment not in valid_environments:
            self.add_error(f"Environment must be one of: {', '.join(valid_environments)}")
            return False
        
        return True
    
    def validate_aws_region(self, region: str) -> bool:
        """
        Validate AWS region format.
        
        Args:
            region: AWS region to validate
            
        Returns:
            bool: True if valid
        """
        if not region:
            self.add_error("AWS region cannot be empty")
            return False
        
        # AWS region pattern: us-east-1, eu-west-1, etc.
        if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', region):
            self.add_error("Invalid AWS region format")
            return False
        
        return True
    
    def validate_cidr(self, cidr: str, name: str = "CIDR") -> bool:
        """
        Validate CIDR notation.
        
        Args:
            cidr: CIDR to validate
            name: Name for error messages
            
        Returns:
            bool: True if valid
        """
        if not cidr:
            self.add_error(f"{name} cannot be empty")
            return False
        
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            
            # Check for reasonable subnet sizes
            if network.prefixlen < 8:
                self.add_warning(f"{name} has a very large subnet (/{network.prefixlen})")
            elif network.prefixlen > 28:
                self.add_warning(f"{name} has a very small subnet (/{network.prefixlen})")
            
            return True
        except ValueError as e:
            self.add_error(f"Invalid {name}: {str(e)}")
            return False
    
    def validate_email(self, email: str) -> bool:
        """
        Validate email address format.
        
        Args:
            email: Email to validate
            
        Returns:
            bool: True if valid
        """
        if not email:
            self.add_error("Email cannot be empty")
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            self.add_error("Invalid email format")
            return False
        
        return True
    
    def validate_tags(self, tags: Dict[str, str]) -> bool:
        """
        Validate AWS tags.
        
        Args:
            tags: Tags to validate
            
        Returns:
            bool: True if valid
        """
        if not isinstance(tags, dict):
            self.add_error("Tags must be a dictionary")
            return False
        
        for key, value in tags.items():
            if not isinstance(key, str) or not isinstance(value, str):
                self.add_error("Tag keys and values must be strings")
                return False
            
            if len(key) > 128:
                self.add_error(f"Tag key '{key}' exceeds 128 characters")
                return False
            
            if len(value) > 256:
                self.add_error(f"Tag value for key '{key}' exceeds 256 characters")
                return False
            
            # AWS tag key restrictions
            if not re.match(r'^[a-zA-Z0-9\s_.:/=+\-@]*$', key):
                self.add_error(f"Tag key '{key}' contains invalid characters")
                return False
        
        return True


class SecurityValidator(BaseValidator):
    """
    Validator for security configurations and requirements.
    
    Provides validation for security policies, encryption settings,
    access controls, and compliance requirements.
    """
    
    def validate_construct_security(self, construct) -> bool:
        """
        Validate security configuration of a construct.
        
        Args:
            construct: Construct to validate
            
        Returns:
            bool: True if valid
        """
        is_valid = True
        
        # Check if encryption is enabled
        if not hasattr(construct, 'encryption_key'):
            self.add_error("Encryption key not configured")
            is_valid = False
        
        # Check if monitoring is set up
        if not hasattr(construct, 'alert_topic'):
            self.add_error("Alert topic not configured")
            is_valid = False
        
        # Check if logging is configured
        if not hasattr(construct, 'log_group'):
            self.add_error("Log group not configured")
            is_valid = False
        
        return is_valid
    
    def validate_security_config(self, config: SecurityConfig) -> bool:
        """
        Validate security configuration.
        
        Args:
            config: Security configuration to validate
            
        Returns:
            bool: True if valid
        """
        is_valid = True
        
        # Validate security level
        valid_levels = ['basic', 'standard', 'high', 'critical']
        if config.level not in valid_levels:
            self.add_error(f"Invalid security level: {config.level}")
            is_valid = False
        
        # Validate data classification
        valid_classifications = ['public', 'internal', 'confidential', 'restricted']
        if config.data_classification not in valid_classifications:
            self.add_error(f"Invalid data classification: {config.data_classification}")
            is_valid = False
        
        # Validate compliance frameworks
        valid_frameworks = ['soc2', 'iso27001', 'gdpr', 'hipaa', 'pci_dss']
        for framework in config.compliance_frameworks:
            if framework not in valid_frameworks:
                self.add_error(f"Invalid compliance framework: {framework}")
                is_valid = False
        
        # Security level specific validations
        if config.level in ['high', 'critical']:
            if not config.encryption_enabled:
                self.add_error("Encryption must be enabled for high/critical security levels")
                is_valid = False
            
            if not config.audit_logging:
                self.add_error("Audit logging must be enabled for high/critical security levels")
                is_valid = False
            
            if not config.network_isolation:
                self.add_error("Network isolation must be enabled for high/critical security levels")
                is_valid = False
        
        return is_valid
    
    def validate_iam_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Validate IAM policy for security best practices.
        
        Args:
            policy: IAM policy document
            
        Returns:
            bool: True if valid
        """
        is_valid = True
        
        if 'Statement' not in policy:
            self.add_error("IAM policy must have Statement")
            return False
        
        statements = policy['Statement']
        if not isinstance(statements, list):
            statements = [statements]
        
        for i, statement in enumerate(statements):
            # Check for overly permissive policies
            if statement.get('Effect') == 'Allow':
                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                
                # Check for wildcard permissions
                if '*' in actions:
                    self.add_warning(f"Statement {i} uses wildcard action '*'")
                
                # Check for admin permissions
                admin_actions = ['*', 'iam:*', 'sts:AssumeRole']
                for action in actions:
                    if any(admin in action for admin in admin_actions):
                        self.add_warning(f"Statement {i} has potentially dangerous action: {action}")
                
                # Check for wildcard resources
                resources = statement.get('Resource', [])
                if isinstance(resources, str):
                    resources = [resources]
                
                if '*' in resources:
                    self.add_warning(f"Statement {i} uses wildcard resource '*'")
        
        return is_valid
    
    def validate_network_security(self, vpc_config: Dict[str, Any]) -> bool:
        """
        Validate network security configuration.
        
        Args:
            vpc_config: VPC configuration
            
        Returns:
            bool: True if valid
        """
        is_valid = True
        
        # Validate VPC CIDR
        if 'cidr' in vpc_config:
            if not self.validate_cidr(vpc_config['cidr'], "VPC CIDR"):
                is_valid = False
        
        # Check for security best practices
        if not vpc_config.get('enable_flow_logs', False):
            self.add_warning("VPC Flow Logs should be enabled for security monitoring")
        
        if not vpc_config.get('enable_dns_hostnames', False):
            self.add_warning("DNS hostnames should be enabled for proper service discovery")
        
        return is_valid


class ComplianceValidator(BaseValidator):
    """
    Validator for compliance requirements and frameworks.
    
    Provides validation for various compliance frameworks including
    SOC 2, ISO 27001, GDPR, HIPAA, and PCI DSS.
    """
    
    def validate_soc2_compliance(self, construct) -> bool:
        """
        Validate SOC 2 compliance requirements.
        
        Args:
            construct: Construct to validate
            
        Returns:
            bool: True if compliant
        """
        is_compliant = True
        
        # CC1.1 - Control Environment
        if not hasattr(construct, 'encryption_key'):
            self.add_error("SOC 2 CC1.1: Encryption key required")
            is_compliant = False
        
        # CC2.1 - Communication and Information
        if not hasattr(construct, 'log_group'):
            self.add_error("SOC 2 CC2.1: Logging required")
            is_compliant = False
        
        # CC6.1 - Logical and Physical Access Controls
        if not hasattr(construct, 'alert_topic'):
            self.add_error("SOC 2 CC6.1: Monitoring and alerting required")
            is_compliant = False
        
        return is_compliant
    
    def validate_gdpr_compliance(self, construct) -> bool:
        """
        Validate GDPR compliance requirements.
        
        Args:
            construct: Construct to validate
            
        Returns:
            bool: True if compliant
        """
        is_compliant = True
        
        # Article 32 - Security of processing
        if not hasattr(construct, 'encryption_key'):
            self.add_error("GDPR Article 32: Encryption required for personal data")
            is_compliant = False
        
        # Article 30 - Records of processing activities
        if not hasattr(construct, 'log_group'):
            self.add_error("GDPR Article 30: Audit logging required")
            is_compliant = False
        
        return is_compliant
    
    def validate_hipaa_compliance(self, construct) -> bool:
        """
        Validate HIPAA compliance requirements.
        
        Args:
            construct: Construct to validate
            
        Returns:
            bool: True if compliant
        """
        is_compliant = True
        
        # 164.312(a)(1) - Access control
        if not hasattr(construct, 'encryption_key'):
            self.add_error("HIPAA 164.312(a)(1): Encryption required for PHI")
            is_compliant = False
        
        # 164.312(b) - Audit controls
        if not hasattr(construct, 'log_group'):
            self.add_error("HIPAA 164.312(b): Audit logging required")
            is_compliant = False
        
        return is_compliant
    
    def validate_compliance_framework(self, framework: str, construct) -> bool:
        """
        Validate compliance for a specific framework.
        
        Args:
            framework: Compliance framework to validate
            construct: Construct to validate
            
        Returns:
            bool: True if compliant
        """
        framework_validators = {
            'soc2': self.validate_soc2_compliance,
            'gdpr': self.validate_gdpr_compliance,
            'hipaa': self.validate_hipaa_compliance,
        }
        
        validator = framework_validators.get(framework)
        if not validator:
            self.add_warning(f"No validator available for framework: {framework}")
            return True
        
        return validator(construct)


class OperationalValidator(BaseValidator):
    """
    Validator for operational requirements and best practices.
    
    Provides validation for monitoring, backup, disaster recovery,
    and operational excellence requirements.
    """
    
    def validate_monitoring_config(self, config: MonitoringConfig) -> bool:
        """
        Validate monitoring configuration.
        
        Args:
            config: Monitoring configuration to validate
            
        Returns:
            bool: True if valid
        """
        is_valid = True
        
        # Validate monitoring level
        valid_levels = ['basic', 'standard', 'detailed', 'comprehensive']
        if config.level not in valid_levels:
            self.add_error(f"Invalid monitoring level: {config.level}")
            is_valid = False
        
        # Validate retention periods
        if config.log_retention_days < 1 or config.log_retention_days > 3653:
            self.add_error("Log retention days must be between 1 and 3653")
            is_valid = False
        
        if config.metric_retention_days < 1 or config.metric_retention_days > 455:
            self.add_error("Metric retention days must be between 1 and 455")
            is_valid = False
        
        # Validate alert channels
        for channel in config.alert_channels:
            if channel not in ['email', 'slack', 'pagerduty', 'sns']:
                self.add_warning(f"Unknown alert channel: {channel}")
        
        return is_valid
    
    def validate_backup_config(self, backup_config: Dict[str, Any]) -> bool:
        """
        Validate backup configuration.
        
        Args:
            backup_config: Backup configuration to validate
            
        Returns:
            bool: True if valid
        """
        is_valid = True
        
        if backup_config.get('enabled', False):
            retention_days = backup_config.get('retention_days', 0)
            if retention_days < 1:
                self.add_error("Backup retention days must be at least 1")
                is_valid = False
            
            if retention_days > 35 and not backup_config.get('cross_region_backup', False):
                self.add_warning("Consider enabling cross-region backup for long retention periods")
        
        return is_valid
    
    def validate_disaster_recovery_config(self, dr_config: Dict[str, Any]) -> bool:
        """
        Validate disaster recovery configuration.
        
        Args:
            dr_config: Disaster recovery configuration to validate
            
        Returns:
            bool: True if valid
        """
        is_valid = True
        
        if dr_config.get('enabled', False):
            rto_minutes = dr_config.get('rto_minutes', 0)
            rpo_minutes = dr_config.get('rpo_minutes', 0)
            
            if rto_minutes <= 0:
                self.add_error("RTO (Recovery Time Objective) must be greater than 0")
                is_valid = False
            
            if rpo_minutes <= 0:
                self.add_error("RPO (Recovery Point Objective) must be greater than 0")
                is_valid = False
            
            if rpo_minutes > rto_minutes:
                self.add_warning("RPO should typically be less than or equal to RTO")
            
            if dr_config.get('multi_region', False) and not dr_config.get('failover_region'):
                self.add_error("Failover region must be specified for multi-region DR")
                is_valid = False
        
        return is_valid
