"""
SQS Construct for DevSecOps Platform.

This construct implements Amazon SQS queues with enterprise-grade configurations,
dead letter queues, FIFO support, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aws_cdk import (
    Duration,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_events as events,
    aws_events_targets as targets,
    aws_sns as sns,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class SqsConstructProps(ConstructProps):
    """Properties for SQS Construct."""
    
    # Queue Configuration
    queue_name: Optional[str] = None
    fifo: bool = False
    content_based_deduplication: bool = False
    deduplication_scope: str = "queue"  # queue, messageGroup
    fifo_throughput_limit: str = "perQueue"  # perQueue, perMessageGroupId
    
    # Message Configuration
    visibility_timeout_seconds: int = 30
    message_retention_period_days: int = 14
    max_message_size_bytes: int = 262144  # 256 KB
    receive_message_wait_time_seconds: int = 0  # Long polling
    
    # Dead Letter Queue Configuration
    enable_dlq: bool = True
    max_receive_count: int = 3
    dlq_message_retention_days: int = 14
    
    # Encryption Configuration
    enable_encryption: bool = True
    encryption_master_key: Optional[str] = None
    
    # Lambda Integration
    enable_lambda_trigger: bool = False
    lambda_function_arn: Optional[str] = None
    batch_size: int = 10
    maximum_batching_window_seconds: int = 5
    
    # Auto Scaling Configuration
    enable_auto_scaling: bool = False
    target_queue_depth: int = 100
    scale_up_threshold: int = 1000
    scale_down_threshold: int = 10
    
    # Monitoring Configuration
    enable_detailed_monitoring: bool = True
    alarm_thresholds: Dict[str, int] = None
    
    # Access Control
    allowed_principals: List[str] = None
    allowed_actions: List[str] = None
    
    # Redrive Configuration
    enable_redrive_allow_policy: bool = False
    redrive_permission: str = "byQueue"  # byQueue, denyAll, allowAll


class SqsConstruct(BaseConstruct):
    """
    SQS Construct.
    
    Implements a comprehensive SQS queue setup with:
    - Standard and FIFO queue support
    - Dead letter queue with configurable retry logic
    - Encryption at rest with KMS
    - Lambda integration with batch processing
    - Auto-scaling based on queue depth
    - Comprehensive monitoring and alerting
    - Access control and security policies
    - Redrive policies for message recovery
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: SqsConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize SQS Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.alarm_thresholds is None:
            self.props.alarm_thresholds = {
                "messages_visible": 1000,
                "messages_not_visible": 100,
                "age_of_oldest_message": 300  # 5 minutes
            }
        
        if self.props.allowed_actions is None:
            self.props.allowed_actions = [
                "sqs:SendMessage",
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage"
            ]
        
        # Create resources
        self._create_dead_letter_queue()
        self._create_main_queue()
        self._create_lambda_integration()
        self._create_access_policies()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_dead_letter_queue(self) -> None:
        """Create dead letter queue."""
        
        if not self.props.enable_dlq:
            return
        
        dlq_name = f"{self.props.queue_name or self.get_resource_name('queue')}-dlq"
        if self.props.fifo:
            dlq_name += ".fifo"
        
        self.dead_letter_queue = sqs.Queue(
            self,
            "DeadLetterQueue",
            queue_name=dlq_name,
            fifo=self.props.fifo,
            content_based_deduplication=self.props.content_based_deduplication if self.props.fifo else None,
            deduplication_scope=getattr(sqs.DeduplicationScope, self.props.deduplication_scope.upper()) if self.props.fifo else None,
            fifo_throughput_limit=getattr(sqs.FifoThroughputLimit, self.props.fifo_throughput_limit.upper()) if self.props.fifo else None,
            visibility_timeout=Duration.seconds(self.props.visibility_timeout_seconds),
            retention_period=Duration.days(self.props.dlq_message_retention_days),
            encryption=sqs.QueueEncryption.KMS if self.props.enable_encryption else sqs.QueueEncryption.UNENCRYPTED,
            encryption_master_key=self.encryption_key if self.props.enable_encryption else None,
            removal_policy=self._get_removal_policy()
        )
    
    def _create_main_queue(self) -> None:
        """Create main SQS queue."""
        
        queue_name = self.props.queue_name or self.get_resource_name("queue")
        if self.props.fifo:
            queue_name += ".fifo"
        
        # Configure dead letter queue
        dead_letter_queue_config = None
        if self.props.enable_dlq and hasattr(self, 'dead_letter_queue'):
            dead_letter_queue_config = sqs.DeadLetterQueue(
                max_receive_count=self.props.max_receive_count,
                queue=self.dead_letter_queue
            )
        
        self.queue = sqs.Queue(
            self,
            "Queue",
            queue_name=queue_name,
            fifo=self.props.fifo,
            content_based_deduplication=self.props.content_based_deduplication if self.props.fifo else None,
            deduplication_scope=getattr(sqs.DeduplicationScope, self.props.deduplication_scope.upper()) if self.props.fifo else None,
            fifo_throughput_limit=getattr(sqs.FifoThroughputLimit, self.props.fifo_throughput_limit.upper()) if self.props.fifo else None,
            visibility_timeout=Duration.seconds(self.props.visibility_timeout_seconds),
            retention_period=Duration.days(self.props.message_retention_period_days),
            max_message_size_bytes=self.props.max_message_size_bytes,
            receive_message_wait_time=Duration.seconds(self.props.receive_message_wait_time_seconds),
            dead_letter_queue=dead_letter_queue_config,
            encryption=sqs.QueueEncryption.KMS if self.props.enable_encryption else sqs.QueueEncryption.UNENCRYPTED,
            encryption_master_key=self.encryption_key if self.props.enable_encryption else None,
            removal_policy=self._get_removal_policy()
        )

        # Apply standardized tags
        queue_tags = self.get_resource_tags(
            application="messaging",
            component="sqs-queue",
            data_classification=getattr(self.props, 'data_classification', 'internal'),
            monitoring_level="enhanced" if self.props.enable_detailed_monitoring else "standard"
        )
        for key, value in queue_tags.items():
            if value:  # Only apply non-None values
                self.queue.node.add_metadata(f"tag:{key}", value)

        # Configure redrive allow policy
        if self.props.enable_redrive_allow_policy and hasattr(self, 'dead_letter_queue'):
            sqs.CfnQueue(
                self,
                "RedriveAllowPolicy",
                queue_url=self.dead_letter_queue.queue_url,
                redrive_allow_policy={
                    "redrivePermission": self.props.redrive_permission,
                    "sourceQueueArns": [self.queue.queue_arn] if self.props.redrive_permission == "byQueue" else None
                }
            )
    
    def _create_lambda_integration(self) -> None:
        """Create Lambda integration for queue processing."""
        
        if not self.props.enable_lambda_trigger or not self.props.lambda_function_arn:
            return
        
        # Get Lambda function
        lambda_function = lambda_.Function.from_function_arn(
            self,
            "LambdaFunction",
            self.props.lambda_function_arn
        )
        
        # Add SQS event source to Lambda
        from aws_cdk import aws_lambda_event_sources as lambda_event_sources
        
        lambda_function.add_event_source(
            lambda_event_sources.SqsEventSource(
                queue=self.queue,
                batch_size=self.props.batch_size,
                max_batching_window=Duration.seconds(self.props.maximum_batching_window_seconds),
                report_batch_item_failures=True
            )
        )
        
        # Grant Lambda permissions to access the queue
        self.queue.grant_consume_messages(lambda_function)
        if hasattr(self, 'dead_letter_queue'):
            self.dead_letter_queue.grant_consume_messages(lambda_function)
    
    def _create_access_policies(self) -> None:
        """Create access policies for the queue."""
        
        if not self.props.allowed_principals:
            return
        
        # Create policy statements
        policy_statements = []
        
        for principal in self.props.allowed_principals:
            policy_statements.append(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.ArnPrincipal(principal)],
                    actions=self.props.allowed_actions,
                    resources=[self.queue.queue_arn]
                )
            )
        
        # Add policy to queue
        for statement in policy_statements:
            self.queue.add_to_resource_policy(statement)
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.messages_visible_metric = cloudwatch.Metric(
            namespace="AWS/SQS",
            metric_name="ApproximateNumberOfMessages",
            dimensions_map={
                "QueueName": self.queue.queue_name
            }
        )
        
        self.messages_not_visible_metric = cloudwatch.Metric(
            namespace="AWS/SQS",
            metric_name="ApproximateNumberOfMessagesNotVisible",
            dimensions_map={
                "QueueName": self.queue.queue_name
            }
        )
        
        self.oldest_message_age_metric = cloudwatch.Metric(
            namespace="AWS/SQS",
            metric_name="ApproximateAgeOfOldestMessage",
            dimensions_map={
                "QueueName": self.queue.queue_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighMessageCount",
            self.messages_visible_metric,
            threshold=self.props.alarm_thresholds["messages_visible"],
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High number of visible messages in queue"
        )
        
        self.create_alarm(
            "HighInFlightMessages",
            self.messages_not_visible_metric,
            threshold=self.props.alarm_thresholds["messages_not_visible"],
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High number of in-flight messages"
        )
        
        self.create_alarm(
            "OldMessages",
            self.oldest_message_age_metric,
            threshold=self.props.alarm_thresholds["age_of_oldest_message"],
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="Old messages in queue"
        )
        
        # Dead letter queue monitoring
        if hasattr(self, 'dead_letter_queue'):
            self.create_alarm(
                "MessagesInDLQ",
                cloudwatch.Metric(
                    namespace="AWS/SQS",
                    metric_name="ApproximateNumberOfMessages",
                    dimensions_map={
                        "QueueName": self.dead_letter_queue.queue_name
                    }
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="Messages in dead letter queue"
            )
        
        # Lambda integration monitoring
        if self.props.enable_lambda_trigger and self.props.lambda_function_arn:
            lambda_function_name = self.props.lambda_function_arn.split(":")[-1]
            
            self.create_alarm(
                "LambdaProcessingErrors",
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={
                        "FunctionName": lambda_function_name
                    }
                ),
                threshold=5,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High error rate in SQS Lambda processor"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "QueueName",
            self.queue.queue_name,
            "Name of the SQS queue"
        )
        
        self.add_output(
            "QueueArn",
            self.queue.queue_arn,
            "ARN of the SQS queue"
        )
        
        self.add_output(
            "QueueUrl",
            self.queue.queue_url,
            "URL of the SQS queue"
        )
        
        if hasattr(self, 'dead_letter_queue'):
            self.add_output(
                "DeadLetterQueueName",
                self.dead_letter_queue.queue_name,
                "Name of the dead letter queue"
            )
            
            self.add_output(
                "DeadLetterQueueArn",
                self.dead_letter_queue.queue_arn,
                "ARN of the dead letter queue"
            )
            
            self.add_output(
                "DeadLetterQueueUrl",
                self.dead_letter_queue.queue_url,
                "URL of the dead letter queue"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.messages_visible_metric,
            self.messages_not_visible_metric,
            self.oldest_message_age_metric,
            cloudwatch.Metric(
                namespace="AWS/SQS",
                metric_name="NumberOfMessagesSent",
                dimensions_map={
                    "QueueName": self.queue.queue_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/SQS",
                metric_name="NumberOfMessagesReceived",
                dimensions_map={
                    "QueueName": self.queue.queue_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/SQS",
                metric_name="NumberOfMessagesDeleted",
                dimensions_map={
                    "QueueName": self.queue.queue_name
                }
            )
        ]
        
        if hasattr(self, 'dead_letter_queue'):
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/SQS",
                    metric_name="ApproximateNumberOfMessages",
                    dimensions_map={
                        "QueueName": self.dead_letter_queue.queue_name
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/SQS",
                    metric_name="NumberOfMessagesSent",
                    dimensions_map={
                        "QueueName": self.dead_letter_queue.queue_name
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
    
    def grant_send_messages(self, grantee: iam.IGrantable) -> iam.Grant:
        """Grant send message permissions to the queue."""
        return self.queue.grant_send_messages(grantee)
    
    def grant_consume_messages(self, grantee: iam.IGrantable) -> iam.Grant:
        """Grant consume message permissions to the queue."""
        return self.queue.grant_consume_messages(grantee)
    
    def grant_purge(self, grantee: iam.IGrantable) -> iam.Grant:
        """Grant purge permissions to the queue."""
        return self.queue.grant_purge(grantee)
    
    def add_to_resource_policy(self, statement: iam.PolicyStatement) -> None:
        """Add a statement to the queue's resource policy."""
        self.queue.add_to_resource_policy(statement)
