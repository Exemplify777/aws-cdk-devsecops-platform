"""
SNS Construct for DevSecOps Platform.

This construct implements Amazon SNS topics with enterprise-grade configurations,
multi-protocol delivery, filtering, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class SnsConstructProps(ConstructProps):
    """Properties for SNS Construct."""
    
    # Topic Configuration
    topic_name: Optional[str] = None
    display_name: Optional[str] = None
    fifo: bool = False
    content_based_deduplication: bool = False
    
    # Encryption Configuration
    enable_encryption: bool = True
    
    # Delivery Configuration
    delivery_retry_policy: Dict[str, Any] = None
    delivery_status_logging: bool = True
    
    # Subscription Configuration
    email_subscriptions: List[str] = None
    sms_subscriptions: List[str] = None
    sqs_subscriptions: List[Dict[str, Any]] = None
    lambda_subscriptions: List[Dict[str, Any]] = None
    http_subscriptions: List[Dict[str, Any]] = None
    
    # Message Filtering
    enable_message_filtering: bool = True
    filter_policies: Dict[str, Dict[str, Any]] = None
    
    # Dead Letter Queue Configuration
    enable_dlq: bool = True
    dlq_max_receive_count: int = 3
    
    # Access Control
    allowed_publishers: List[str] = None
    allowed_subscribers: List[str] = None
    
    # Monitoring Configuration
    enable_detailed_monitoring: bool = True
    alarm_thresholds: Dict[str, int] = None
    
    # Message Attributes
    default_message_attributes: Dict[str, str] = None
    
    # Cross-Region Configuration
    enable_cross_region_delivery: bool = False
    target_regions: List[str] = None


class SnsConstruct(BaseConstruct):
    """
    SNS Construct.
    
    Implements a comprehensive SNS topic setup with:
    - Standard and FIFO topic support
    - Multi-protocol subscriptions (email, SMS, SQS, Lambda, HTTP)
    - Message filtering and routing
    - Encryption at rest and in transit
    - Dead letter queues for failed deliveries
    - Delivery status logging and monitoring
    - Access control and security policies
    - Cross-region message delivery
    - Comprehensive monitoring and alerting
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: SnsConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize SNS Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.delivery_retry_policy is None:
            self.props.delivery_retry_policy = {
                "numRetries": 3,
                "numMaxDelayRetries": 2,
                "numMinDelayRetries": 1,
                "numNoDelayRetries": 0,
                "minDelayTarget": 20,
                "maxDelayTarget": 20,
                "backoffFunction": "linear"
            }
        
        if self.props.alarm_thresholds is None:
            self.props.alarm_thresholds = {
                "failed_notifications": 10,
                "high_publish_rate": 1000
            }
        
        if self.props.email_subscriptions is None:
            self.props.email_subscriptions = []
        if self.props.sms_subscriptions is None:
            self.props.sms_subscriptions = []
        if self.props.sqs_subscriptions is None:
            self.props.sqs_subscriptions = []
        if self.props.lambda_subscriptions is None:
            self.props.lambda_subscriptions = []
        if self.props.http_subscriptions is None:
            self.props.http_subscriptions = []
        
        # Create resources
        self._create_dead_letter_queue()
        self._create_sns_topic()
        self._create_subscriptions()
        self._create_access_policies()
        self._create_delivery_status_logging()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_dead_letter_queue(self) -> None:
        """Create dead letter queue for failed deliveries."""
        
        if not self.props.enable_dlq:
            return
        
        self.dlq = sqs.Queue(
            self,
            "SNSDeadLetterQueue",
            queue_name=self.get_resource_name("sns-dlq"),
            fifo=self.props.fifo,
            content_based_deduplication=self.props.content_based_deduplication if self.props.fifo else None,
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.encryption_key,
            retention_period=Duration.days(14),
            removal_policy=self._get_removal_policy()
        )
    
    def _create_sns_topic(self) -> None:
        """Create SNS topic."""
        
        topic_name = self.props.topic_name or self.get_resource_name("topic")
        if self.props.fifo:
            topic_name += ".fifo"
        
        self.topic = sns.Topic(
            self,
            "SNSTopic",
            topic_name=topic_name,
            display_name=self.props.display_name or f"{self.project_name} Notifications",
            fifo=self.props.fifo,
            content_based_deduplication=self.props.content_based_deduplication if self.props.fifo else None,
            master_key=self.encryption_key if self.props.enable_encryption else None
        )
        
        # Configure delivery policy
        if self.props.delivery_retry_policy:
            delivery_policy = {
                "http": {
                    "defaultHealthyRetryPolicy": self.props.delivery_retry_policy,
                    "disableSubscriptionOverrides": False
                }
            }
            
            sns.CfnTopic(
                self,
                "TopicDeliveryPolicy",
                topic_arn=self.topic.topic_arn,
                delivery_policy=json.dumps(delivery_policy)
            )
    
    def _create_subscriptions(self) -> None:
        """Create subscriptions for the topic."""
        
        # Email subscriptions
        for email in self.props.email_subscriptions:
            self.topic.add_subscription(
                subscriptions.EmailSubscription(
                    email_address=email,
                    dead_letter_queue=self.dlq if hasattr(self, 'dlq') else None
                )
            )
        
        # SMS subscriptions
        for phone_number in self.props.sms_subscriptions:
            self.topic.add_subscription(
                subscriptions.SmsSubscription(
                    phone_number=phone_number,
                    dead_letter_queue=self.dlq if hasattr(self, 'dlq') else None
                )
            )
        
        # SQS subscriptions
        for sqs_config in self.props.sqs_subscriptions:
            queue = sqs.Queue.from_queue_arn(
                self,
                f"SQSQueue{len(self.props.sqs_subscriptions)}",
                sqs_config["queue_arn"]
            )
            
            filter_policy = None
            if self.props.enable_message_filtering and sqs_config.get("filter_policy"):
                filter_policy = sqs_config["filter_policy"]
            
            self.topic.add_subscription(
                subscriptions.SqsSubscription(
                    queue=queue,
                    raw_message_delivery=sqs_config.get("raw_message_delivery", False),
                    filter_policy=filter_policy,
                    dead_letter_queue=self.dlq if hasattr(self, 'dlq') else None
                )
            )
        
        # Lambda subscriptions
        for lambda_config in self.props.lambda_subscriptions:
            lambda_function = lambda_.Function.from_function_arn(
                self,
                f"LambdaFunction{len(self.props.lambda_subscriptions)}",
                lambda_config["function_arn"]
            )
            
            filter_policy = None
            if self.props.enable_message_filtering and lambda_config.get("filter_policy"):
                filter_policy = lambda_config["filter_policy"]
            
            self.topic.add_subscription(
                subscriptions.LambdaSubscription(
                    fn=lambda_function,
                    filter_policy=filter_policy,
                    dead_letter_queue=self.dlq if hasattr(self, 'dlq') else None
                )
            )
        
        # HTTP/HTTPS subscriptions
        for http_config in self.props.http_subscriptions:
            filter_policy = None
            if self.props.enable_message_filtering and http_config.get("filter_policy"):
                filter_policy = http_config["filter_policy"]
            
            self.topic.add_subscription(
                subscriptions.UrlSubscription(
                    url=http_config["url"],
                    protocol=sns.SubscriptionProtocol.HTTPS if http_config["url"].startswith("https") else sns.SubscriptionProtocol.HTTP,
                    raw_message_delivery=http_config.get("raw_message_delivery", False),
                    filter_policy=filter_policy,
                    dead_letter_queue=self.dlq if hasattr(self, 'dlq') else None
                )
            )
    
    def _create_access_policies(self) -> None:
        """Create access policies for the topic."""
        
        # Publisher policy
        if self.props.allowed_publishers:
            publisher_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(arn) for arn in self.props.allowed_publishers],
                actions=[
                    "sns:Publish"
                ],
                resources=[self.topic.topic_arn]
            )
            self.topic.add_to_resource_policy(publisher_policy)
        
        # Subscriber policy
        if self.props.allowed_subscribers:
            subscriber_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(arn) for arn in self.props.allowed_subscribers],
                actions=[
                    "sns:Subscribe",
                    "sns:Unsubscribe",
                    "sns:ConfirmSubscription"
                ],
                resources=[self.topic.topic_arn]
            )
            self.topic.add_to_resource_policy(subscriber_policy)
        
        # Cross-region delivery policy
        if self.props.enable_cross_region_delivery and self.props.target_regions:
            cross_region_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("sns.amazonaws.com")],
                actions=[
                    "sns:Publish"
                ],
                resources=[
                    f"arn:aws:sns:{region}:{self.account}:*"
                    for region in self.props.target_regions
                ]
            )
            self.topic.add_to_resource_policy(cross_region_policy)
    
    def _create_delivery_status_logging(self) -> None:
        """Create delivery status logging configuration."""
        
        if not self.props.delivery_status_logging:
            return
        
        # Create CloudWatch log group for delivery status
        self.delivery_log_group = logs.LogGroup(
            self,
            "DeliveryStatusLogGroup",
            log_group_name=f"/aws/sns/{self.get_resource_name('delivery-status')}",
            retention=logs.RetentionDays.ONE_MONTH,
            encryption_key=self.encryption_key,
            removal_policy=self._get_removal_policy()
        )
        
        # Create IAM role for SNS logging
        sns_logging_role = self.create_service_role(
            "SNSLoggingRole",
            "sns.amazonaws.com",
            inline_policies={
                "CloudWatchLogsAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[self.delivery_log_group.log_group_arn]
                        )
                    ]
                )
            }
        )
        
        # Configure delivery status logging
        delivery_status_config = {
            "lambda": {
                "successFeedbackRoleArn": sns_logging_role.role_arn,
                "failureFeedbackRoleArn": sns_logging_role.role_arn,
                "successFeedbackSampleRate": "100"
            },
            "http": {
                "successFeedbackRoleArn": sns_logging_role.role_arn,
                "failureFeedbackRoleArn": sns_logging_role.role_arn,
                "successFeedbackSampleRate": "100"
            },
            "sqs": {
                "successFeedbackRoleArn": sns_logging_role.role_arn,
                "failureFeedbackRoleArn": sns_logging_role.role_arn,
                "successFeedbackSampleRate": "100"
            }
        }
        
        # Apply delivery status configuration
        for protocol, config in delivery_status_config.items():
            sns.CfnTopic(
                self,
                f"DeliveryStatus{protocol.title()}",
                topic_arn=self.topic.topic_arn,
                **{f"{protocol}SuccessFeedbackRoleArn": config["successFeedbackRoleArn"]},
                **{f"{protocol}FailureFeedbackRoleArn": config["failureFeedbackRoleArn"]},
                **{f"{protocol}SuccessFeedbackSampleRate": config["successFeedbackSampleRate"]}
            )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.published_messages_metric = cloudwatch.Metric(
            namespace="AWS/SNS",
            metric_name="NumberOfMessagesPublished",
            dimensions_map={
                "TopicName": self.topic.topic_name
            }
        )
        
        self.failed_notifications_metric = cloudwatch.Metric(
            namespace="AWS/SNS",
            metric_name="NumberOfNotificationsFailed",
            dimensions_map={
                "TopicName": self.topic.topic_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighFailedNotifications",
            self.failed_notifications_metric,
            threshold=self.props.alarm_thresholds["failed_notifications"],
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High number of failed notifications"
        )
        
        self.create_alarm(
            "HighPublishRate",
            self.published_messages_metric,
            threshold=self.props.alarm_thresholds["high_publish_rate"],
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High message publish rate"
        )
        
        # Dead letter queue monitoring
        if hasattr(self, 'dlq'):
            self.create_alarm(
                "MessagesInSNSDLQ",
                cloudwatch.Metric(
                    namespace="AWS/SQS",
                    metric_name="ApproximateNumberOfMessages",
                    dimensions_map={
                        "QueueName": self.dlq.queue_name
                    }
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="Messages in SNS dead letter queue"
            )
        
        # Subscription-specific monitoring
        for protocol in ["Email", "SMS", "SQS", "Lambda", "HTTP"]:
            self.create_alarm(
                f"High{protocol}DeliveryDelay",
                cloudwatch.Metric(
                    namespace="AWS/SNS",
                    metric_name=f"NumberOfNotificationsDeliveryDelayed",
                    dimensions_map={
                        "TopicName": self.topic.topic_name
                    }
                ),
                threshold=100,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description=f"High delivery delay for {protocol} notifications"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "TopicName",
            self.topic.topic_name,
            "Name of the SNS topic"
        )
        
        self.add_output(
            "TopicArn",
            self.topic.topic_arn,
            "ARN of the SNS topic"
        )
        
        if hasattr(self, 'dlq'):
            self.add_output(
                "DeadLetterQueueArn",
                self.dlq.queue_arn,
                "ARN of the SNS dead letter queue"
            )
        
        if hasattr(self, 'delivery_log_group'):
            self.add_output(
                "DeliveryLogGroupName",
                self.delivery_log_group.log_group_name,
                "Name of the delivery status log group"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.published_messages_metric,
            self.failed_notifications_metric,
            cloudwatch.Metric(
                namespace="AWS/SNS",
                metric_name="NumberOfNotificationsDelivered",
                dimensions_map={
                    "TopicName": self.topic.topic_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/SNS",
                metric_name="NumberOfNotificationsFilteredOut",
                dimensions_map={
                    "TopicName": self.topic.topic_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/SNS",
                metric_name="PublishSize",
                dimensions_map={
                    "TopicName": self.topic.topic_name
                }
            )
        ]
        
        if hasattr(self, 'dlq'):
            metrics.append(
                cloudwatch.Metric(
                    namespace="AWS/SQS",
                    metric_name="ApproximateNumberOfMessages",
                    dimensions_map={
                        "QueueName": self.dlq.queue_name
                    }
                )
            )
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
    
    def grant_publish(self, grantee: iam.IGrantable) -> iam.Grant:
        """Grant publish permissions to the topic."""
        return self.topic.grant_publish(grantee)
    
    def add_subscription(self, subscription: subscriptions.ITopicSubscription) -> sns.Subscription:
        """Add a subscription to the topic."""
        return self.topic.add_subscription(subscription)
    
    def add_to_resource_policy(self, statement: iam.PolicyStatement) -> None:
        """Add a statement to the topic's resource policy."""
        self.topic.add_to_resource_policy(statement)
