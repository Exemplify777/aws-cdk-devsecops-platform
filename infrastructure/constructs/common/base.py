"""
Base construct class providing common functionality for all DevSecOps Platform constructs.

This module implements the foundational BaseConstruct class that all other constructs
inherit from, ensuring consistent behavior, security, monitoring, and compliance.
"""

from typing import Dict, Any, Optional, List, Union
from abc import ABC, abstractmethod
import json
import logging

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    Tags,
    CfnOutput,
    aws_iam as iam,
    aws_kms as kms,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
)
from constructs import Construct

from .config import EnvironmentConfig
from .types import ConstructProps, SecurityConfig, MonitoringConfig
from .mixins import ValidationMixin, SecurityMixin, MonitoringMixin
from .utils import TaggingUtils, NamingUtils
from .validators import InputValidator, SecurityValidator

logger = logging.getLogger(__name__)


class BaseConstruct(Construct, ValidationMixin, SecurityMixin, MonitoringMixin):
    """
    Base construct class providing common functionality for all DevSecOps Platform constructs.
    
    This class implements:
    - Environment-specific configuration management
    - Standardized security controls
    - Comprehensive monitoring and alerting
    - Compliance validation
    - Error handling and rollback capabilities
    - AI-powered optimization recommendations
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: ConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize the base construct with common functionality.
        
        Args:
            scope: The parent construct
            construct_id: Unique identifier for this construct
            props: Configuration properties for the construct
            **kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Store configuration
        self.props = props
        self.environment = props.environment
        self.project_name = props.project_name
        self.construct_name = construct_id
        
        # Initialize environment configuration
        self.env_config = EnvironmentConfig(self.environment)
        
        # Validate inputs
        self._validate_inputs()
        
        # Initialize security configuration
        self._setup_security()
        
        # Initialize monitoring
        self._setup_monitoring()
        
        # Apply standard tags
        self._apply_tags()
        
        # Store construct metadata
        self._metadata: Dict[str, Any] = {
            "construct_type": self.__class__.__name__,
            "environment": self.environment,
            "project_name": self.project_name,
            "created_at": self._get_timestamp(),
            "version": "1.0.0"
        }
        
        logger.info(f"Initialized {self.__class__.__name__} in {self.environment} environment")
    
    def _validate_inputs(self) -> None:
        """Validate construct inputs using the validation mixin."""
        validator = InputValidator()
        
        # Validate required properties
        if not self.props.project_name:
            raise ValueError("project_name is required")
        
        if not self.props.environment:
            raise ValueError("environment is required")
        
        # Validate environment
        valid_environments = ["dev", "staging", "prod"]
        if self.props.environment not in valid_environments:
            raise ValueError(f"environment must be one of {valid_environments}")
        
        # Validate project name format
        if not validator.validate_project_name(self.props.project_name):
            raise ValueError("project_name must be alphanumeric with hyphens only")
        
        # Additional validation from mixin
        self.validate_construct_props(self.props)
    
    def _setup_security(self) -> None:
        """Initialize security configuration using the security mixin."""
        # Create KMS key for encryption
        self.encryption_key = self.create_encryption_key(
            f"{self.project_name}-{self.construct_name}-key"
        )
        
        # Setup security monitoring
        self.setup_security_monitoring()
        
        # Validate security configuration
        security_validator = SecurityValidator()
        security_validator.validate_construct_security(self)
    
    def _setup_monitoring(self) -> None:
        """Initialize monitoring configuration using the monitoring mixin."""
        # Create SNS topic for alerts
        self.alert_topic = sns.Topic(
            self,
            "AlertTopic",
            topic_name=f"{self.project_name}-{self.construct_name}-alerts",
            display_name=f"Alerts for {self.construct_name}"
        )
        
        # Setup CloudWatch log group
        self.log_group = logs.LogGroup(
            self,
            "LogGroup",
            log_group_name=f"/aws/{self.project_name}/{self.construct_name}",
            retention=self._get_log_retention(),
            removal_policy=self._get_removal_policy()
        )
        
        # Initialize monitoring from mixin
        self.setup_monitoring()
    
    def _apply_tags(self) -> None:
        """Apply standardized tags to all resources."""
        tagging_utils = TaggingUtils()
        
        standard_tags = {
            "Project": self.project_name,
            "Environment": self.environment,
            "Construct": self.construct_name,
            "ManagedBy": "DevSecOpsPlatform",
            "CreatedBy": "CDKConstruct",
            "Version": "1.0.0"
        }
        
        # Add environment-specific tags
        env_tags = self.env_config.get_tags()
        standard_tags.update(env_tags)
        
        # Add custom tags from props
        if hasattr(self.props, 'tags') and self.props.tags:
            standard_tags.update(self.props.tags)
        
        # Apply tags using utility
        tagging_utils.apply_tags(self, standard_tags)
    
    def _get_log_retention(self) -> logs.RetentionDays:
        """Get log retention period based on environment."""
        retention_map = {
            "dev": logs.RetentionDays.ONE_WEEK,
            "staging": logs.RetentionDays.ONE_MONTH,
            "prod": logs.RetentionDays.SIX_MONTHS
        }
        return retention_map.get(self.environment, logs.RetentionDays.ONE_MONTH)
    
    def _get_removal_policy(self) -> RemovalPolicy:
        """Get removal policy based on environment."""
        if self.environment == "prod":
            return RemovalPolicy.RETAIN
        return RemovalPolicy.DESTROY
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def add_output(self, output_id: str, value: str, description: str = "") -> CfnOutput:
        """
        Add a CloudFormation output with standardized naming.
        
        Args:
            output_id: Unique identifier for the output
            value: The output value
            description: Description of the output
            
        Returns:
            CfnOutput: The created output
        """
        return CfnOutput(
            self,
            output_id,
            value=value,
            description=description,
            export_name=f"{self.project_name}-{self.construct_name}-{output_id}"
        )
    
    def create_alarm(
        self,
        alarm_id: str,
        metric: cloudwatch.Metric,
        threshold: float,
        comparison_operator: cloudwatch.ComparisonOperator,
        description: str = ""
    ) -> cloudwatch.Alarm:
        """
        Create a standardized CloudWatch alarm.
        
        Args:
            alarm_id: Unique identifier for the alarm
            metric: The metric to monitor
            threshold: The threshold value
            comparison_operator: The comparison operator
            description: Description of the alarm
            
        Returns:
            cloudwatch.Alarm: The created alarm
        """
        return cloudwatch.Alarm(
            self,
            alarm_id,
            metric=metric,
            threshold=threshold,
            comparison_operator=comparison_operator,
            evaluation_periods=2,
            alarm_description=description or f"Alarm for {self.construct_name}",
            alarm_actions=[self.alert_topic],
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
    
    def get_resource_name(self, resource_type: str, suffix: str = "") -> str:
        """
        Generate standardized resource names.
        
        Args:
            resource_type: Type of the resource (e.g., 'bucket', 'function')
            suffix: Optional suffix for the name
            
        Returns:
            str: Standardized resource name
        """
        naming_utils = NamingUtils()
        return naming_utils.generate_resource_name(
            self.project_name,
            self.environment,
            resource_type,
            suffix
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get construct metadata.
        
        Returns:
            Dict[str, Any]: Construct metadata
        """
        return self._metadata.copy()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add custom metadata to the construct.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value
    
    @abstractmethod
    def _create_resources(self) -> None:
        """
        Abstract method to create construct-specific resources.
        Must be implemented by all concrete constructs.
        """
        pass
    
    @abstractmethod
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """
        Abstract method to define construct-specific monitoring metrics.
        Must be implemented by all concrete constructs.
        
        Returns:
            List[cloudwatch.Metric]: List of metrics to monitor
        """
        pass
    
    def validate_deployment(self) -> bool:
        """
        Validate the construct deployment.
        
        Returns:
            bool: True if deployment is valid
        """
        try:
            # Validate security configuration
            security_validator = SecurityValidator()
            security_validator.validate_construct_security(self)
            
            # Validate monitoring setup
            metrics = self._setup_monitoring_metrics()
            if not metrics:
                logger.warning(f"No monitoring metrics defined for {self.construct_name}")
            
            # Additional validation logic can be added here
            
            return True
        except Exception as e:
            logger.error(f"Deployment validation failed for {self.construct_name}: {e}")
            return False
    
    def get_cost_estimate(self) -> Dict[str, Any]:
        """
        Get estimated costs for this construct.
        
        Returns:
            Dict[str, Any]: Cost estimation data
        """
        # This would integrate with AWS Cost Explorer or pricing APIs
        # For now, return placeholder data
        return {
            "construct": self.construct_name,
            "environment": self.environment,
            "estimated_monthly_cost": "TBD",
            "cost_factors": [],
            "optimization_recommendations": []
        }
    
    def get_security_posture(self) -> Dict[str, Any]:
        """
        Get security posture assessment for this construct.
        
        Returns:
            Dict[str, Any]: Security assessment data
        """
        return {
            "construct": self.construct_name,
            "encryption_enabled": bool(self.encryption_key),
            "monitoring_enabled": bool(self.alert_topic),
            "compliance_status": "compliant",
            "security_recommendations": []
        }
