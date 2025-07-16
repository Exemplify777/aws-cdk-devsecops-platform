"""
Lambda Construct for DevSecOps Platform.

This construct implements AWS Lambda functions with enterprise-grade configurations,
monitoring, security, and operational best practices.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    Size,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_events as events,
    aws_events_targets as targets,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_ec2 as ec2,
    aws_lambda_destinations as destinations,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class LambdaConstructProps(ConstructProps):
    """Properties for Lambda Construct."""
    
    # Function Configuration
    function_name: Optional[str] = None
    description: str = ""
    runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9
    handler: str = "index.handler"
    code_path: str = "src/lambda"
    
    # Performance Configuration
    memory_size: int = 128
    timeout_minutes: int = 3
    ephemeral_storage_size: int = 512  # MB
    reserved_concurrency: Optional[int] = None
    provisioned_concurrency: Optional[int] = None
    
    # Environment Configuration
    environment_variables: Dict[str, str] = None
    enable_environment_encryption: bool = True
    
    # VPC Configuration
    enable_vpc: bool = False
    vpc_id: Optional[str] = None
    subnet_ids: List[str] = None
    security_group_ids: List[str] = None
    
    # Layers Configuration
    enable_layers: bool = False
    layer_arns: List[str] = None
    create_custom_layer: bool = False
    layer_code_path: Optional[str] = None
    
    # Event Sources
    enable_api_gateway: bool = False
    enable_s3_trigger: bool = False
    s3_bucket_name: Optional[str] = None
    s3_event_type: str = "s3:ObjectCreated:*"
    s3_filter_prefix: Optional[str] = None
    s3_filter_suffix: Optional[str] = None
    
    enable_sqs_trigger: bool = False
    sqs_queue_arn: Optional[str] = None
    sqs_batch_size: int = 10
    
    enable_schedule: bool = False
    schedule_expression: Optional[str] = None
    
    # Destinations
    enable_destinations: bool = False
    success_destination_arn: Optional[str] = None
    failure_destination_arn: Optional[str] = None
    
    # Error Handling
    enable_dlq: bool = True
    max_retry_attempts: int = 2
    enable_async_config: bool = False
    
    # Monitoring
    enable_detailed_monitoring: bool = True
    enable_x_ray_tracing: bool = True
    enable_insights: bool = True
    log_retention_days: int = 30
    
    # Security
    enable_code_signing: bool = False
    code_signing_config_arn: Optional[str] = None


class LambdaConstruct(BaseConstruct):
    """
    Lambda Construct.
    
    Implements a comprehensive Lambda function with:
    - Enterprise-grade security and monitoring
    - VPC integration and networking
    - Multiple event source integrations
    - Custom layers and dependencies
    - Dead letter queues and error handling
    - Performance optimization and scaling
    - Comprehensive logging and tracing
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: LambdaConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize Lambda Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.environment_variables is None:
            self.props.environment_variables = {}
        
        # Create resources
        self._create_lambda_layers()
        self._create_lambda_function()
        self._configure_event_sources()
        self._configure_destinations()
        self._create_error_handling()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_lambda_layers(self) -> None:
        """Create Lambda layers if enabled."""
        
        self.layers = []
        
        # Add existing layer ARNs
        if self.props.enable_layers and self.props.layer_arns:
            for layer_arn in self.props.layer_arns:
                layer = lambda_.LayerVersion.from_layer_version_arn(
                    self,
                    f"Layer{len(self.layers)}",
                    layer_arn
                )
                self.layers.append(layer)
        
        # Create custom layer
        if self.props.create_custom_layer and self.props.layer_code_path:
            self.custom_layer = lambda_.LayerVersion(
                self,
                "CustomLayer",
                layer_version_name=self.get_resource_name("layer"),
                code=lambda_.Code.from_asset(self.props.layer_code_path),
                compatible_runtimes=[self.props.runtime],
                description=f"Custom layer for {self.project_name}",
                removal_policy=self._get_removal_policy()
            )
            self.layers.append(self.custom_layer)
    
    def _create_lambda_function(self) -> None:
        """Create the Lambda function."""
        
        # Create IAM role
        self.lambda_role = self.create_service_role(
            "LambdaExecutionRole",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaBasicExecutionRole"
            ] + (["service-role/AWSLambdaVPCAccessExecutionRole"] if self.props.enable_vpc else []),
            inline_policies={
                "KMSAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kms:Decrypt",
                                "kms:GenerateDataKey"
                            ],
                            resources=[self.encryption_key.key_arn]
                        )
                    ]
                )
            }
        )
        
        # Prepare environment variables
        env_vars = self.props.environment_variables.copy()
        env_vars.update({
            "ENVIRONMENT": self.environment,
            "PROJECT_NAME": self.project_name,
            "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
        })
        
        # VPC configuration
        vpc_config = None
        if self.props.enable_vpc:
            vpc = ec2.Vpc.from_lookup(
                self,
                "VPC",
                vpc_id=self.props.vpc_id
            ) if self.props.vpc_id else None
            
            subnets = [
                ec2.Subnet.from_subnet_id(self, f"Subnet{i}", subnet_id)
                for i, subnet_id in enumerate(self.props.subnet_ids or [])
            ]
            
            security_groups = [
                ec2.SecurityGroup.from_security_group_id(self, f"SG{i}", sg_id)
                for i, sg_id in enumerate(self.props.security_group_ids or [])
            ]
            
            if vpc and subnets:
                vpc_config = lambda_.VpcConfig(
                    vpc=vpc,
                    subnets=subnets,
                    security_groups=security_groups
                )
        
        # Create Lambda function
        self.lambda_function = lambda_.Function(
            self,
            "LambdaFunction",
            function_name=self.props.function_name or self.get_resource_name("function"),
            description=self.props.description or f"Lambda function for {self.project_name}",
            runtime=self.props.runtime,
            handler=self.props.handler,
            code=lambda_.Code.from_asset(self.props.code_path),
            role=self.lambda_role,
            memory_size=self.props.memory_size,
            timeout=Duration.minutes(self.props.timeout_minutes),
            ephemeral_storage_size=Size.mebibytes(self.props.ephemeral_storage_size),
            environment=env_vars,
            environment_encryption=self.encryption_key if self.props.enable_environment_encryption else None,
            layers=self.layers if self.layers else None,
            vpc=vpc_config.vpc if vpc_config else None,
            vpc_subnets=ec2.SubnetSelection(subnets=vpc_config.subnets) if vpc_config else None,
            security_groups=vpc_config.security_groups if vpc_config else None,
            reserved_concurrent_executions=self.props.reserved_concurrency,
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_x_ray_tracing else lambda_.Tracing.DISABLED,
            insights_version=lambda_.LambdaInsightsVersion.VERSION_1_0_119_0 if self.props.enable_insights else None,
            log_retention=getattr(logs.RetentionDays, f"_{self.props.log_retention_days}_DAYS", logs.RetentionDays.ONE_MONTH),
            retry_attempts=self.props.max_retry_attempts,
            code_signing_config=lambda_.CodeSigningConfig.from_code_signing_config_arn(
                self,
                "CodeSigningConfig",
                self.props.code_signing_config_arn
            ) if self.props.enable_code_signing and self.props.code_signing_config_arn else None
        )
        
        # Apply standardized tags
        lambda_tags = self.get_resource_tags(
            application="compute",
            component="lambda-function",
            data_classification=getattr(self.props, 'data_classification', 'internal'),
            monitoring_level="enhanced" if self.props.enable_insights else "standard"
        )
        for key, value in lambda_tags.items():
            if value:  # Only apply non-None values
                self.lambda_function.node.add_metadata(f"tag:{key}", value)

        # Configure provisioned concurrency
        if self.props.provisioned_concurrency:
            self.lambda_function.add_alias(
                "ProvisionedAlias",
                provisioned_concurrent_executions=self.props.provisioned_concurrency
            )
    
    def _configure_event_sources(self) -> None:
        """Configure event sources for the Lambda function."""
        
        # S3 trigger
        if self.props.enable_s3_trigger and self.props.s3_bucket_name:
            from aws_cdk import aws_s3 as s3
            from aws_cdk import aws_s3_notifications as s3n
            
            bucket = s3.Bucket.from_bucket_name(
                self,
                "S3Bucket",
                self.props.s3_bucket_name
            )
            
            notification_filter = s3.NotificationKeyFilter()
            if self.props.s3_filter_prefix:
                notification_filter = s3.NotificationKeyFilter(prefix=self.props.s3_filter_prefix)
            if self.props.s3_filter_suffix:
                notification_filter = s3.NotificationKeyFilter(suffix=self.props.s3_filter_suffix)
            
            bucket.add_event_notification(
                getattr(s3.EventType, self.props.s3_event_type.replace(":", "_").upper()),
                s3n.LambdaDestination(self.lambda_function),
                notification_filter
            )
        
        # SQS trigger
        if self.props.enable_sqs_trigger and self.props.sqs_queue_arn:
            from aws_cdk import aws_lambda_event_sources as lambda_event_sources
            
            queue = sqs.Queue.from_queue_arn(
                self,
                "SQSQueue",
                self.props.sqs_queue_arn
            )
            
            self.lambda_function.add_event_source(
                lambda_event_sources.SqsEventSource(
                    queue=queue,
                    batch_size=self.props.sqs_batch_size
                )
            )
        
        # Scheduled trigger
        if self.props.enable_schedule and self.props.schedule_expression:
            schedule_rule = events.Rule(
                self,
                "ScheduleRule",
                schedule=events.Schedule.expression(self.props.schedule_expression),
                description=f"Scheduled trigger for {self.lambda_function.function_name}"
            )
            
            schedule_rule.add_target(
                targets.LambdaFunction(self.lambda_function)
            )
    
    def _configure_destinations(self) -> None:
        """Configure Lambda destinations for async invocations."""
        
        if not self.props.enable_destinations:
            return
        
        success_destination = None
        failure_destination = None
        
        if self.props.success_destination_arn:
            if "sns" in self.props.success_destination_arn:
                success_topic = sns.Topic.from_topic_arn(
                    self,
                    "SuccessTopic",
                    self.props.success_destination_arn
                )
                success_destination = destinations.SnsDestination(success_topic)
            elif "sqs" in self.props.success_destination_arn:
                success_queue = sqs.Queue.from_queue_arn(
                    self,
                    "SuccessQueue",
                    self.props.success_destination_arn
                )
                success_destination = destinations.SqsDestination(success_queue)
        
        if self.props.failure_destination_arn:
            if "sns" in self.props.failure_destination_arn:
                failure_topic = sns.Topic.from_topic_arn(
                    self,
                    "FailureTopic",
                    self.props.failure_destination_arn
                )
                failure_destination = destinations.SnsDestination(failure_topic)
            elif "sqs" in self.props.failure_destination_arn:
                failure_queue = sqs.Queue.from_queue_arn(
                    self,
                    "FailureQueue",
                    self.props.failure_destination_arn
                )
                failure_destination = destinations.SqsDestination(failure_queue)
        
        if success_destination or failure_destination:
            self.lambda_function.configure_async_invoke(
                on_success=success_destination,
                on_failure=failure_destination,
                max_event_age=Duration.hours(6),
                retry_attempts=self.props.max_retry_attempts
            )
    
    def _create_error_handling(self) -> None:
        """Create error handling resources."""
        
        if self.props.enable_dlq:
            # Create dead letter queue
            self.dlq = sqs.Queue(
                self,
                "DeadLetterQueue",
                queue_name=self.get_resource_name("dlq"),
                encryption=sqs.QueueEncryption.KMS,
                encryption_master_key=self.encryption_key,
                retention_period=Duration.days(14),
                visibility_timeout=Duration.minutes(self.props.timeout_minutes * 6)
            )
            
            # Add DLQ to Lambda function
            self.lambda_function.add_dead_letter_queue(
                dead_letter_queue=self.dlq
            )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.invocations_metric = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Invocations",
            dimensions_map={
                "FunctionName": self.lambda_function.function_name
            }
        )
        
        self.errors_metric = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Errors",
            dimensions_map={
                "FunctionName": self.lambda_function.function_name
            }
        )
        
        self.duration_metric = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Duration",
            dimensions_map={
                "FunctionName": self.lambda_function.function_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighErrorRate",
            self.errors_metric,
            threshold=5,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High error rate in Lambda function"
        )
        
        self.create_alarm(
            "HighDuration",
            self.duration_metric,
            threshold=Duration.minutes(self.props.timeout_minutes * 0.8).to_milliseconds(),
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High duration in Lambda function"
        )
        
        self.create_alarm(
            "LowInvocations",
            self.invocations_metric,
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            description="Low invocation rate (potential issue)"
        )
        
        if self.props.enable_dlq:
            self.create_alarm(
                "MessagesInDLQ",
                cloudwatch.Metric(
                    namespace="AWS/SQS",
                    metric_name="ApproximateNumberOfMessages",
                    dimensions_map={
                        "QueueName": self.dlq.queue_name
                    }
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="Messages in Lambda dead letter queue"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "FunctionName",
            self.lambda_function.function_name,
            "Name of the Lambda function"
        )
        
        self.add_output(
            "FunctionArn",
            self.lambda_function.function_arn,
            "ARN of the Lambda function"
        )
        
        self.add_output(
            "FunctionRole",
            self.lambda_role.role_arn,
            "ARN of the Lambda execution role"
        )
        
        if self.props.enable_dlq:
            self.add_output(
                "DeadLetterQueueUrl",
                self.dlq.queue_url,
                "URL of the dead letter queue"
            )
        
        if hasattr(self, 'custom_layer'):
            self.add_output(
                "CustomLayerArn",
                self.custom_layer.layer_version_arn,
                "ARN of the custom Lambda layer"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        return [
            self.invocations_metric,
            self.errors_metric,
            self.duration_metric,
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Throttles",
                dimensions_map={
                    "FunctionName": self.lambda_function.function_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="ConcurrentExecutions",
                dimensions_map={
                    "FunctionName": self.lambda_function.function_name
                }
            )
        ]
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
    
    def add_permission(self, principal: str, action: str = "lambda:InvokeFunction") -> None:
        """Add permission to invoke the Lambda function."""
        self.lambda_function.add_permission(
            f"Permission{len(self.lambda_function.permissions)}",
            principal=iam.ServicePrincipal(principal),
            action=action
        )
    
    def add_environment_variable(self, key: str, value: str) -> None:
        """Add environment variable to the Lambda function."""
        self.lambda_function.add_environment(key, value)
