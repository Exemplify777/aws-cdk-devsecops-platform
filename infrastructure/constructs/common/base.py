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
from .conventions import (
    ResourceNaming,
    ResourceTagging,
    ValidationReport,
    ValidationSeverity,
    validate_construct_props,
    SecurityValidator as ConventionSecurityValidator,
    ComplianceValidator,
    CostOptimizationValidator
)

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

        # Initialize convention utilities
        self._setup_conventions()

        # Validate inputs and conventions
        self._validate_inputs()
        self._validate_conventions()

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
    
    def _setup_conventions(self) -> None:
        """Setup convention utilities for naming and tagging."""
        # Determine service category based on construct type
        service_mapping = {
            "Data": "data",
            "ML": "ml",
            "Api": "api",
            "Infrastructure": "infra",
            "Messaging": "msg",
            "Security": "sec",
            "Monitoring": "mon"
        }

        # Extract service from construct class name
        service = "infra"  # default
        for key, value in service_mapping.items():
            if key in self.__class__.__name__:
                service = value
                break

        # Initialize naming utility
        self.naming = ResourceNaming(
            project=self.project_name.lower().replace("_", "-")[:8],
            environment=self.environment,
            service=service,
            region=self.region if hasattr(self, 'region') else None
        )

        # Initialize tagging utility
        self.tagging = ResourceTagging(
            environment=self.environment,
            project=self.project_name,
            owner=getattr(self.props, 'owner', 'platform-team'),
            cost_center=getattr(self.props, 'cost_center', 'CC-1234')
        )

    def _validate_conventions(self) -> None:
        """Validate construct properties against conventions."""
        # Get validators based on construct type
        validators = [
            self._validate_security_conventions,
            self._validate_compliance_conventions,
            self._validate_cost_conventions
        ]

        # Run validation
        validation_report = validate_construct_props(
            construct_name=self.__class__.__name__,
            props=self.props,
            validators=validators
        )

        # Handle validation results
        if not validation_report.overall_status:
            errors = validation_report.get_errors()
            error_messages = [f"{error.property_name}: {error.message}" for error in errors]
            raise ValueError(f"Convention validation failed for {self.__class__.__name__}: {error_messages}")

        # Log warnings
        warnings = validation_report.get_warnings()
        for warning in warnings:
            print(f"WARNING [{self.__class__.__name__}]: {warning.message}")

    def _validate_security_conventions(self, props: ConstructProps) -> List:
        """Validate security conventions."""
        results = []

        # Check encryption requirements
        if hasattr(props, 'enable_encryption'):
            result = ConventionSecurityValidator.validate_encryption_config(
                props.enable_encryption,
                self.environment
            )
            results.append(result)

        return results

    def _validate_compliance_conventions(self, props: ConstructProps) -> List:
        """Validate compliance conventions."""
        results = []

        # Check data retention if applicable
        if hasattr(props, 'retention_days'):
            compliance_framework = getattr(props, 'compliance_framework', None)
            result = ComplianceValidator.validate_data_retention(
                props.retention_days,
                compliance_framework
            )
            results.append(result)

        # Check backup requirements
        if hasattr(props, 'enable_backup'):
            compliance_framework = getattr(props, 'compliance_framework', None)
            result = ComplianceValidator.validate_backup_requirements(
                props.enable_backup,
                self.environment,
                compliance_framework
            )
            results.append(result)

        return results

    def _validate_cost_conventions(self, props: ConstructProps) -> List:
        """Validate cost optimization conventions."""
        results = []

        # Check instance sizing if applicable
        if hasattr(props, 'instance_type'):
            result = CostOptimizationValidator.validate_instance_sizing(
                props.instance_type,
                self.environment
            )
            results.append(result)

        # Check lifecycle policies if applicable
        if hasattr(props, 'enable_lifecycle'):
            storage_type = getattr(props, 'storage_type', 's3')
            result = CostOptimizationValidator.validate_storage_lifecycle(
                props.enable_lifecycle,
                storage_type
            )
            results.append(result)

        return results

    def get_resource_name(self, component: str, identifier: Optional[str] = None) -> str:
        """
        Generate standardized resource name using conventions.

        Args:
            component: Component type (e.g., 'processor', 'storage')
            identifier: Optional identifier for uniqueness

        Returns:
            str: Standardized resource name
        """
        # Use appropriate naming method based on component type
        if 'bucket' in component.lower():
            return self.naming.s3_bucket(component, identifier=identifier)
        elif 'function' in component.lower() or 'lambda' in component.lower():
            return self.naming.lambda_function(component, identifier=identifier)
        elif 'table' in component.lower():
            return self.naming.dynamodb_table(component, identifier=identifier)
        elif 'queue' in component.lower():
            is_fifo = getattr(self.props, 'fifo', False)
            return self.naming.sqs_queue(component, is_fifo=is_fifo, identifier=identifier)
        elif 'topic' in component.lower():
            is_fifo = getattr(self.props, 'fifo', False)
            return self.naming.sns_topic(component, is_fifo=is_fifo, identifier=identifier)
        elif 'stream' in component.lower():
            return self.naming.kinesis_stream(component, identifier=identifier)
        elif 'role' in component.lower():
            return self.naming.iam_role(component, identifier=identifier)
        elif 'key' in component.lower():
            return self.naming.kms_key_alias(component, identifier=identifier)
        else:
            # Generic naming
            return self.naming._generate_base_name(component, identifier)

    def get_resource_tags(self,
                         application: str,
                         component: str,
                         **additional_tags) -> Dict[str, str]:
        """
        Generate standardized resource tags using conventions.

        Args:
            application: Application name
            component: Component type
            **additional_tags: Additional custom tags

        Returns:
            Dict[str, str]: Complete tag set
        """
        # Add construct-specific tags
        tags = {
            "data_classification": getattr(self.props, 'data_classification', None),
            "pii_data": getattr(self.props, 'pii_data', None),
            "compliance_framework": getattr(self.props, 'compliance_framework', None),
            "backup_schedule": getattr(self.props, 'backup_schedule', None),
            "monitoring_level": getattr(self.props, 'monitoring_level', 'standard')
        }

        # Remove None values
        tags = {k: v for k, v in tags.items() if v is not None}

        # Add additional tags
        tags.update(additional_tags)

        return self.tagging.get_tags(
            application=application,
            component=component,
            **tags
        )

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
