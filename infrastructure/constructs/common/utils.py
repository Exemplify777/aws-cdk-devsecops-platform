"""
Utility classes and functions for DevSecOps Platform constructs.

This module provides common utility functions for naming, tagging,
resource management, and other cross-cutting concerns.
"""

from typing import Dict, Any, List, Optional, Union
import re
import hashlib
import json
from datetime import datetime

from aws_cdk import Tags
from constructs import Construct


class NamingUtils:
    """
    Utility class for standardized resource naming conventions.
    
    Provides consistent naming patterns across all constructs and environments
    following AWS best practices and organizational standards.
    """
    
    @staticmethod
    def generate_resource_name(
        project_name: str,
        environment: str,
        resource_type: str,
        suffix: str = "",
        max_length: int = 63
    ) -> str:
        """
        Generate standardized resource name.
        
        Args:
            project_name: Name of the project
            environment: Deployment environment
            resource_type: Type of resource (e.g., 'bucket', 'function')
            suffix: Optional suffix
            max_length: Maximum length for the name
            
        Returns:
            str: Standardized resource name
        """
        # Clean inputs
        project_name = NamingUtils._clean_name(project_name)
        environment = NamingUtils._clean_name(environment)
        resource_type = NamingUtils._clean_name(resource_type)
        suffix = NamingUtils._clean_name(suffix) if suffix else ""
        
        # Build name components
        components = [project_name, resource_type, environment]
        if suffix:
            components.append(suffix)
        
        # Join with hyphens
        name = "-".join(components)
        
        # Truncate if necessary
        if len(name) > max_length:
            # Keep the suffix and truncate the beginning
            if suffix:
                available_length = max_length - len(suffix) - 1  # -1 for hyphen
                truncated_base = "-".join(components[:-1])[:available_length]
                name = f"{truncated_base}-{suffix}"
            else:
                name = name[:max_length]
        
        return name
    
    @staticmethod
    def generate_unique_name(
        base_name: str,
        unique_id: str,
        max_length: int = 63
    ) -> str:
        """
        Generate unique resource name with hash suffix.
        
        Args:
            base_name: Base name for the resource
            unique_id: Unique identifier (e.g., stack ID)
            max_length: Maximum length for the name
            
        Returns:
            str: Unique resource name
        """
        # Generate short hash from unique_id
        hash_suffix = hashlib.md5(unique_id.encode()).hexdigest()[:8]
        
        # Calculate available length for base name
        available_length = max_length - len(hash_suffix) - 1  # -1 for hyphen
        
        # Truncate base name if necessary
        if len(base_name) > available_length:
            base_name = base_name[:available_length]
        
        return f"{base_name}-{hash_suffix}"
    
    @staticmethod
    def _clean_name(name: str) -> str:
        """
        Clean name to conform to AWS naming requirements.
        
        Args:
            name: Name to clean
            
        Returns:
            str: Cleaned name
        """
        # Convert to lowercase
        name = name.lower()
        
        # Replace invalid characters with hyphens
        name = re.sub(r'[^a-z0-9-]', '-', name)
        
        # Remove multiple consecutive hyphens
        name = re.sub(r'-+', '-', name)
        
        # Remove leading/trailing hyphens
        name = name.strip('-')
        
        return name
    
    @staticmethod
    def validate_name(name: str, resource_type: str = "general") -> bool:
        """
        Validate resource name against AWS requirements.
        
        Args:
            name: Name to validate
            resource_type: Type of resource for specific validation
            
        Returns:
            bool: True if name is valid
        """
        # General AWS naming rules
        if not name:
            return False
        
        if len(name) > 63:
            return False
        
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', name):
            return False
        
        # Resource-specific validation
        if resource_type == "s3":
            # S3 bucket naming rules
            if len(name) < 3 or len(name) > 63:
                return False
            if '..' in name or '.-' in name or '-.' in name:
                return False
            if name.startswith('xn--') or name.endswith('-s3alias'):
                return False
        
        elif resource_type == "lambda":
            # Lambda function naming rules
            if len(name) > 64:
                return False
            if not re.match(r'^[a-zA-Z0-9-_]+$', name):
                return False
        
        return True


class TaggingUtils:
    """
    Utility class for standardized resource tagging.
    
    Provides consistent tagging patterns across all constructs and environments
    for cost allocation, governance, and compliance.
    """
    
    @staticmethod
    def apply_tags(construct: Construct, tags: Dict[str, str]) -> None:
        """
        Apply tags to a construct and all its children.
        
        Args:
            construct: The construct to tag
            tags: Dictionary of tags to apply
        """
        for key, value in tags.items():
            Tags.of(construct).add(key, value)
    
    @staticmethod
    def get_standard_tags(
        project_name: str,
        environment: str,
        construct_name: str,
        additional_tags: Dict[str, str] = None
    ) -> Dict[str, str]:
        """
        Get standard tags for resources.
        
        Args:
            project_name: Name of the project
            environment: Deployment environment
            construct_name: Name of the construct
            additional_tags: Additional custom tags
            
        Returns:
            Dict[str, str]: Standard tags
        """
        tags = {
            "Project": project_name,
            "Environment": environment,
            "Construct": construct_name,
            "ManagedBy": "DevSecOpsPlatform",
            "CreatedBy": "CDKConstruct",
            "CreatedAt": datetime.utcnow().isoformat(),
            "Version": "1.0.0"
        }
        
        if additional_tags:
            tags.update(additional_tags)
        
        return tags
    
    @staticmethod
    def get_cost_allocation_tags(
        business_unit: str,
        cost_center: str,
        owner: str
    ) -> Dict[str, str]:
        """
        Get cost allocation tags.
        
        Args:
            business_unit: Business unit name
            cost_center: Cost center code
            owner: Resource owner
            
        Returns:
            Dict[str, str]: Cost allocation tags
        """
        return {
            "BusinessUnit": business_unit,
            "CostCenter": cost_center,
            "Owner": owner,
            "BillingCategory": "Infrastructure"
        }
    
    @staticmethod
    def get_compliance_tags(
        data_classification: str,
        compliance_frameworks: List[str]
    ) -> Dict[str, str]:
        """
        Get compliance-related tags.
        
        Args:
            data_classification: Data classification level
            compliance_frameworks: List of compliance frameworks
            
        Returns:
            Dict[str, str]: Compliance tags
        """
        return {
            "DataClassification": data_classification,
            "ComplianceFrameworks": ",".join(compliance_frameworks),
            "SecurityReview": "Required",
            "DataRetention": "Standard"
        }


class ConstructUtils:
    """
    General utility functions for construct operations.
    
    Provides common functionality for construct validation,
    resource management, and operational tasks.
    """
    
    @staticmethod
    def validate_environment(environment: str) -> bool:
        """
        Validate environment name.
        
        Args:
            environment: Environment name to validate
            
        Returns:
            bool: True if valid
        """
        valid_environments = ["dev", "staging", "prod"]
        return environment in valid_environments
    
    @staticmethod
    def get_account_id_for_environment(environment: str) -> Optional[str]:
        """
        Get AWS account ID for environment.
        
        Args:
            environment: Environment name
            
        Returns:
            Optional[str]: Account ID if found
        """
        # This would typically come from configuration
        account_mapping = {
            "dev": "123456789012",
            "staging": "123456789013", 
            "prod": "123456789014"
        }
        return account_mapping.get(environment)
    
    @staticmethod
    def get_region_for_environment(environment: str) -> str:
        """
        Get AWS region for environment.
        
        Args:
            environment: Environment name
            
        Returns:
            str: AWS region
        """
        # This would typically come from configuration
        region_mapping = {
            "dev": "us-east-1",
            "staging": "us-east-1",
            "prod": "us-east-1"
        }
        return region_mapping.get(environment, "us-east-1")
    
    @staticmethod
    def generate_description(
        construct_name: str,
        purpose: str,
        environment: str
    ) -> str:
        """
        Generate standardized description for resources.
        
        Args:
            construct_name: Name of the construct
            purpose: Purpose of the resource
            environment: Deployment environment
            
        Returns:
            str: Standardized description
        """
        return f"{construct_name} - {purpose} (Environment: {environment})"
    
    @staticmethod
    def merge_configs(
        base_config: Dict[str, Any],
        override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge configuration dictionaries with deep merge.
        
        Args:
            base_config: Base configuration
            override_config: Override configuration
            
        Returns:
            Dict[str, Any]: Merged configuration
        """
        result = base_config.copy()
        
        for key, value in override_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConstructUtils.merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def sanitize_json(data: Any) -> str:
        """
        Sanitize data for JSON serialization.
        
        Args:
            data: Data to sanitize
            
        Returns:
            str: JSON string
        """
        def json_serializer(obj):
            """JSON serializer for objects not serializable by default."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(data, default=json_serializer, indent=2)
    
    @staticmethod
    def calculate_resource_hash(resource_config: Dict[str, Any]) -> str:
        """
        Calculate hash for resource configuration.
        
        Args:
            resource_config: Resource configuration
            
        Returns:
            str: Configuration hash
        """
        config_str = json.dumps(resource_config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    @staticmethod
    def format_arn(
        service: str,
        region: str,
        account_id: str,
        resource_type: str,
        resource_name: str
    ) -> str:
        """
        Format AWS ARN.
        
        Args:
            service: AWS service name
            region: AWS region
            account_id: AWS account ID
            resource_type: Resource type
            resource_name: Resource name
            
        Returns:
            str: Formatted ARN
        """
        return f"arn:aws:{service}:{region}:{account_id}:{resource_type}/{resource_name}"
    
    @staticmethod
    def parse_arn(arn: str) -> Dict[str, str]:
        """
        Parse AWS ARN into components.
        
        Args:
            arn: AWS ARN to parse
            
        Returns:
            Dict[str, str]: ARN components
        """
        parts = arn.split(":")
        if len(parts) < 6:
            raise ValueError(f"Invalid ARN format: {arn}")
        
        resource_parts = parts[5].split("/", 1)
        
        return {
            "partition": parts[1],
            "service": parts[2],
            "region": parts[3],
            "account_id": parts[4],
            "resource_type": resource_parts[0],
            "resource_name": resource_parts[1] if len(resource_parts) > 1 else ""
        }


class SecurityUtils:
    """
    Security-related utility functions.
    
    Provides common security functionality for encryption,
    access control, and security validation.
    """
    
    @staticmethod
    def generate_secure_password(length: int = 32) -> str:
        """
        Generate secure random password.
        
        Args:
            length: Password length
            
        Returns:
            str: Secure password
        """
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def validate_cidr(cidr: str) -> bool:
        """
        Validate CIDR notation.
        
        Args:
            cidr: CIDR to validate
            
        Returns:
            bool: True if valid
        """
        import ipaddress
        
        try:
            ipaddress.ip_network(cidr, strict=False)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_private_ip(ip: str) -> bool:
        """
        Check if IP address is private.
        
        Args:
            ip: IP address to check
            
        Returns:
            bool: True if private
        """
        import ipaddress
        
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except ValueError:
            return False
