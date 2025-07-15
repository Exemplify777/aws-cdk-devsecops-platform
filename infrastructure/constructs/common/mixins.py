"""
Mixin classes providing common functionality for DevSecOps Platform constructs.

This module implements mixin classes that provide reusable functionality
for validation, security, monitoring, and other cross-cutting concerns.
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import logging

from aws_cdk import (
    aws_iam as iam,
    aws_kms as kms,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_logs as logs,
    aws_guardduty as guardduty,
    aws_config as config,
    Duration,
    RemovalPolicy
)

from .types import ConstructProps, SecurityConfig, MonitoringConfig

logger = logging.getLogger(__name__)


class ValidationMixin(ABC):
    """
    Mixin providing input validation capabilities for constructs.
    
    This mixin provides common validation methods that can be used
    by any construct to validate inputs, configurations, and state.
    """
    
    def validate_construct_props(self, props: ConstructProps) -> None:
        """
        Validate construct properties.
        
        Args:
            props: The construct properties to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not props.project_name:
            raise ValueError("project_name is required")
        
        if not props.environment:
            raise ValueError("environment is required")
        
        # Validate project name format
        if not self._is_valid_project_name(props.project_name):
            raise ValueError("project_name must be alphanumeric with hyphens only")
        
        # Validate security configuration
        self._validate_security_config(props.security_config)
        
        # Validate monitoring configuration
        self._validate_monitoring_config(props.monitoring_config)
    
    def _is_valid_project_name(self, name: str) -> bool:
        """
        Validate project name format.
        
        Args:
            name: Project name to validate
            
        Returns:
            bool: True if valid
        """
        import re
        pattern = r'^[a-z0-9][a-z0-9-]*[a-z0-9]$'
        return bool(re.match(pattern, name)) and len(name) <= 63
    
    def _validate_security_config(self, config: SecurityConfig) -> None:
        """
        Validate security configuration.
        
        Args:
            config: Security configuration to validate
        """
        if config.level not in ['basic', 'standard', 'high', 'critical']:
            raise ValueError(f"Invalid security level: {config.level}")
        
        if config.data_classification not in ['public', 'internal', 'confidential', 'restricted']:
            raise ValueError(f"Invalid data classification: {config.data_classification}")
    
    def _validate_monitoring_config(self, config: MonitoringConfig) -> None:
        """
        Validate monitoring configuration.
        
        Args:
            config: Monitoring configuration to validate
        """
        if config.level not in ['basic', 'standard', 'detailed', 'comprehensive']:
            raise ValueError(f"Invalid monitoring level: {config.level}")
        
        if config.log_retention_days < 1 or config.log_retention_days > 3653:
            raise ValueError("log_retention_days must be between 1 and 3653")


class SecurityMixin(ABC):
    """
    Mixin providing security capabilities for constructs.
    
    This mixin provides common security functionality including
    encryption, IAM roles, security monitoring, and compliance.
    """
    
    def create_encryption_key(self, key_name: str, description: str = "") -> kms.Key:
        """
        Create a KMS encryption key with best practices.
        
        Args:
            key_name: Name for the KMS key
            description: Description for the key
            
        Returns:
            kms.Key: The created KMS key
        """
        return kms.Key(
            self,
            f"{key_name}Key",
            description=description or f"Encryption key for {key_name}",
            enable_key_rotation=True,
            removal_policy=self._get_removal_policy(),
            policy=self._create_key_policy()
        )
    
    def _create_key_policy(self) -> iam.PolicyDocument:
        """Create a secure KMS key policy."""
        return iam.PolicyDocument(
            statements=[
                # Allow root account full access
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AccountRootPrincipal()],
                    actions=["kms:*"],
                    resources=["*"]
                ),
                # Allow CloudWatch Logs to use the key
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.ServicePrincipal("logs.amazonaws.com")],
                    actions=[
                        "kms:Encrypt",
                        "kms:Decrypt",
                        "kms:ReEncrypt*",
                        "kms:GenerateDataKey*",
                        "kms:DescribeKey"
                    ],
                    resources=["*"]
                )
            ]
        )
    
    def create_service_role(
        self,
        role_name: str,
        service_principal: str,
        managed_policies: List[str] = None,
        inline_policies: Dict[str, iam.PolicyDocument] = None
    ) -> iam.Role:
        """
        Create an IAM service role with least privilege principles.
        
        Args:
            role_name: Name for the IAM role
            service_principal: AWS service principal
            managed_policies: List of managed policy ARNs
            inline_policies: Dictionary of inline policies
            
        Returns:
            iam.Role: The created IAM role
        """
        managed_policy_objects = []
        if managed_policies:
            for policy_arn in managed_policies:
                managed_policy_objects.append(
                    iam.ManagedPolicy.from_aws_managed_policy_name(policy_arn)
                )
        
        return iam.Role(
            self,
            f"{role_name}Role",
            role_name=f"{self.project_name}-{role_name}-{self.environment}",
            assumed_by=iam.ServicePrincipal(service_principal),
            managed_policies=managed_policy_objects,
            inline_policies=inline_policies or {},
            description=f"Service role for {role_name} in {self.environment}"
        )
    
    def setup_security_monitoring(self) -> None:
        """Set up security monitoring and alerting."""
        # This would be implemented by the concrete construct
        # to set up construct-specific security monitoring
        pass
    
    def _get_removal_policy(self) -> RemovalPolicy:
        """Get appropriate removal policy based on environment."""
        if hasattr(self, 'environment') and self.environment == 'prod':
            return RemovalPolicy.RETAIN
        return RemovalPolicy.DESTROY


class MonitoringMixin(ABC):
    """
    Mixin providing monitoring and observability capabilities for constructs.
    
    This mixin provides common monitoring functionality including
    metrics, alarms, dashboards, and logging.
    """
    
    def setup_monitoring(self) -> None:
        """Set up monitoring for the construct."""
        # Create custom metrics
        self._create_custom_metrics()
        
        # Create alarms
        self._create_alarms()
        
        # Set up logging
        self._setup_logging()
    
    def _create_custom_metrics(self) -> None:
        """Create construct-specific custom metrics."""
        # This should be implemented by concrete constructs
        pass
    
    def _create_alarms(self) -> None:
        """Create CloudWatch alarms for the construct."""
        # Get metrics from the concrete construct
        metrics = self._get_monitoring_metrics()
        
        for metric in metrics:
            self._create_metric_alarm(metric)
    
    def _create_metric_alarm(self, metric: cloudwatch.Metric) -> cloudwatch.Alarm:
        """
        Create a CloudWatch alarm for a metric.
        
        Args:
            metric: The metric to create an alarm for
            
        Returns:
            cloudwatch.Alarm: The created alarm
        """
        alarm_name = f"{metric.metric_name}Alarm"
        
        return cloudwatch.Alarm(
            self,
            alarm_name,
            metric=metric,
            threshold=self._get_metric_threshold(metric.metric_name),
            evaluation_periods=2,
            comparison_operator=self._get_comparison_operator(metric.metric_name),
            alarm_description=f"Alarm for {metric.metric_name}",
            alarm_actions=[self.alert_topic] if hasattr(self, 'alert_topic') else [],
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
    
    def _get_metric_threshold(self, metric_name: str) -> float:
        """
        Get threshold value for a metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            float: Threshold value
        """
        # Default thresholds - should be overridden by concrete constructs
        thresholds = {
            "Errors": 5,
            "Duration": 30000,  # 30 seconds in milliseconds
            "Throttles": 1,
            "CPUUtilization": 80,
            "MemoryUtilization": 80
        }
        return thresholds.get(metric_name, 100)
    
    def _get_comparison_operator(self, metric_name: str) -> cloudwatch.ComparisonOperator:
        """
        Get comparison operator for a metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            cloudwatch.ComparisonOperator: Comparison operator
        """
        # Most metrics use greater than threshold
        greater_than_metrics = ["Errors", "Duration", "Throttles", "CPUUtilization", "MemoryUtilization"]
        
        if metric_name in greater_than_metrics:
            return cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        
        return cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD
    
    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        if hasattr(self, 'log_group'):
            # Add log metric filters for common patterns
            self._add_error_metric_filter()
            self._add_warning_metric_filter()
    
    def _add_error_metric_filter(self) -> None:
        """Add metric filter for error logs."""
        if hasattr(self, 'log_group'):
            logs.MetricFilter(
                self,
                "ErrorMetricFilter",
                log_group=self.log_group,
                metric_namespace=f"{self.project_name}/Errors",
                metric_name="ErrorCount",
                filter_pattern=logs.FilterPattern.literal("[ERROR]"),
                metric_value="1"
            )
    
    def _add_warning_metric_filter(self) -> None:
        """Add metric filter for warning logs."""
        if hasattr(self, 'log_group'):
            logs.MetricFilter(
                self,
                "WarningMetricFilter",
                log_group=self.log_group,
                metric_namespace=f"{self.project_name}/Warnings",
                metric_name="WarningCount",
                filter_pattern=logs.FilterPattern.literal("[WARNING]"),
                metric_value="1"
            )
    
    @abstractmethod
    def _get_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """
        Get list of metrics to monitor for this construct.
        
        Returns:
            List[cloudwatch.Metric]: List of metrics
        """
        pass
    
    def create_dashboard_widget(self, title: str, metrics: List[cloudwatch.Metric]) -> cloudwatch.GraphWidget:
        """
        Create a dashboard widget for metrics.
        
        Args:
            title: Widget title
            metrics: List of metrics to display
            
        Returns:
            cloudwatch.GraphWidget: Dashboard widget
        """
        return cloudwatch.GraphWidget(
            title=title,
            left=metrics,
            width=12,
            height=6
        )


class CostOptimizationMixin(ABC):
    """
    Mixin providing cost optimization capabilities for constructs.
    
    This mixin provides common cost optimization functionality including
    resource right-sizing, lifecycle policies, and cost monitoring.
    """
    
    def setup_cost_optimization(self) -> None:
        """Set up cost optimization for the construct."""
        # Set up cost monitoring
        self._setup_cost_monitoring()
        
        # Apply cost optimization policies
        self._apply_cost_optimization_policies()
    
    def _setup_cost_monitoring(self) -> None:
        """Set up cost monitoring and budgets."""
        # This would integrate with AWS Cost Explorer and Budgets
        pass
    
    def _apply_cost_optimization_policies(self) -> None:
        """Apply cost optimization policies."""
        # This would apply environment-specific cost optimization
        pass
    
    def get_cost_estimate(self) -> Dict[str, Any]:
        """
        Get cost estimate for the construct.
        
        Returns:
            Dict[str, Any]: Cost estimate information
        """
        return {
            "construct": self.__class__.__name__,
            "estimated_monthly_cost": "TBD",
            "cost_factors": [],
            "optimization_recommendations": []
        }


class ComplianceMixin(ABC):
    """
    Mixin providing compliance capabilities for constructs.
    
    This mixin provides common compliance functionality including
    compliance validation, audit logging, and compliance reporting.
    """
    
    def validate_compliance(self, frameworks: List[str] = None) -> Dict[str, bool]:
        """
        Validate compliance against specified frameworks.
        
        Args:
            frameworks: List of compliance frameworks to validate against
            
        Returns:
            Dict[str, bool]: Compliance status for each framework
        """
        frameworks = frameworks or ['soc2']
        results = {}
        
        for framework in frameworks:
            results[framework] = self._validate_framework_compliance(framework)
        
        return results
    
    def _validate_framework_compliance(self, framework: str) -> bool:
        """
        Validate compliance for a specific framework.
        
        Args:
            framework: Compliance framework to validate
            
        Returns:
            bool: True if compliant
        """
        # This would implement framework-specific validation
        # For now, return True as placeholder
        return True
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """
        Generate compliance report for the construct.
        
        Returns:
            Dict[str, Any]: Compliance report
        """
        return {
            "construct": self.__class__.__name__,
            "compliance_status": self.validate_compliance(),
            "audit_trail": [],
            "recommendations": []
        }
