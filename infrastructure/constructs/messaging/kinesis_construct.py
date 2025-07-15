"""
Kinesis Construct for DevSecOps Platform.

This construct implements Amazon Kinesis Data Streams with enterprise-grade
configurations, auto-scaling, analytics, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aws_cdk import (
    Duration,
    aws_kinesis as kinesis,
    aws_kinesisanalytics as analytics,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    aws_applicationautoscaling as autoscaling,
    aws_s3 as s3,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class KinesisConstructProps(ConstructProps):
    """Properties for Kinesis Construct."""
    
    # Stream Configuration
    stream_name: Optional[str] = None
    shard_count: int = 1
    retention_period_hours: int = 24
    shard_level_metrics: List[str] = None
    
    # Auto Scaling Configuration
    enable_auto_scaling: bool = True
    min_capacity: int = 1
    max_capacity: int = 100
    target_utilization_percent: float = 70.0
    scale_in_cooldown_minutes: int = 5
    scale_out_cooldown_minutes: int = 1
    
    # Analytics Configuration
    enable_analytics: bool = False
    analytics_application_name: Optional[str] = None
    sql_queries: List[str] = None
    
    # Consumer Configuration
    enable_lambda_consumer: bool = False
    consumer_lambda_memory: int = 1024
    consumer_lambda_timeout: int = 5
    batch_size: int = 100
    starting_position: str = "LATEST"  # LATEST, TRIM_HORIZON
    
    # Enhanced Fan-Out Configuration
    enable_enhanced_fanout: bool = False
    consumer_names: List[str] = None
    
    # Encryption Configuration
    enable_encryption: bool = True
    
    # Monitoring Configuration
    enable_detailed_monitoring: bool = True
    enable_cloudwatch_logs: bool = True
    log_retention_days: int = 30
    
    # Backup Configuration
    enable_backup_to_s3: bool = False
    backup_bucket_name: Optional[str] = None
    backup_prefix: str = "kinesis-backup/"


class KinesisConstruct(BaseConstruct):
    """
    Kinesis Construct.
    
    Implements a comprehensive Kinesis Data Streams setup with:
    - Auto-scaling based on utilization metrics
    - Kinesis Analytics for real-time processing
    - Lambda consumers with error handling
    - Enhanced fan-out for high throughput
    - Comprehensive monitoring and alerting
    - Backup to S3 for data durability
    - Encryption at rest and in transit
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: KinesisConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize Kinesis Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.shard_level_metrics is None:
            self.props.shard_level_metrics = [
                "IncomingRecords", "OutgoingRecords", "WriteProvisionedThroughputExceeded",
                "ReadProvisionedThroughputExceeded", "IncomingBytes", "OutgoingBytes"
            ]
        if self.props.consumer_names is None:
            self.props.consumer_names = ["default-consumer"]
        
        # Create resources
        self._create_kinesis_stream()
        self._create_auto_scaling()
        self._create_lambda_consumer()
        self._create_enhanced_fanout()
        self._create_analytics_application()
        self._create_backup_configuration()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_kinesis_stream(self) -> None:
        """Create Kinesis Data Stream."""
        
        self.stream = kinesis.Stream(
            self,
            "KinesisStream",
            stream_name=self.props.stream_name or self.get_resource_name("stream"),
            shard_count=self.props.shard_count,
            retention_period=Duration.hours(self.props.retention_period_hours),
            stream_mode=kinesis.StreamMode.PROVISIONED,
            encryption=kinesis.StreamEncryption.KMS if self.props.enable_encryption else kinesis.StreamEncryption.UNENCRYPTED,
            encryption_key=self.encryption_key if self.props.enable_encryption else None
        )
        
        # Enable shard-level metrics
        for metric in self.props.shard_level_metrics:
            kinesis.CfnStream.StreamModeDetailsProperty(
                stream_mode_details=kinesis.CfnStream.StreamModeDetailsProperty(
                    stream_mode="PROVISIONED"
                )
            )
    
    def _create_auto_scaling(self) -> None:
        """Create auto-scaling for Kinesis stream."""
        
        if not self.props.enable_auto_scaling:
            return
        
        # Create scalable target for read capacity
        self.read_scalable_target = autoscaling.ScalableTarget(
            self,
            "ReadScalableTarget",
            service_namespace=autoscaling.ServiceNamespace.KINESIS,
            resource_id=f"stream/{self.stream.stream_name}",
            scalable_dimension="kinesis:shard:ReadCapacity",
            min_capacity=self.props.min_capacity,
            max_capacity=self.props.max_capacity
        )
        
        # Create scaling policy for read capacity
        self.read_scaling_policy = autoscaling.TargetTrackingScalingPolicy(
            self,
            "ReadScalingPolicy",
            scaling_target=self.read_scalable_target,
            target_value=self.props.target_utilization_percent,
            metric=cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="IncomingRecords",
                dimensions_map={
                    "StreamName": self.stream.stream_name
                }
            ),
            scale_in_cooldown=Duration.minutes(self.props.scale_in_cooldown_minutes),
            scale_out_cooldown=Duration.minutes(self.props.scale_out_cooldown_minutes)
        )
        
        # Create scalable target for write capacity
        self.write_scalable_target = autoscaling.ScalableTarget(
            self,
            "WriteScalableTarget",
            service_namespace=autoscaling.ServiceNamespace.KINESIS,
            resource_id=f"stream/{self.stream.stream_name}",
            scalable_dimension="kinesis:shard:WriteCapacity",
            min_capacity=self.props.min_capacity,
            max_capacity=self.props.max_capacity
        )
        
        # Create scaling policy for write capacity
        self.write_scaling_policy = autoscaling.TargetTrackingScalingPolicy(
            self,
            "WriteScalingPolicy",
            scaling_target=self.write_scalable_target,
            target_value=self.props.target_utilization_percent,
            metric=cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="IncomingBytes",
                dimensions_map={
                    "StreamName": self.stream.stream_name
                }
            ),
            scale_in_cooldown=Duration.minutes(self.props.scale_in_cooldown_minutes),
            scale_out_cooldown=Duration.minutes(self.props.scale_out_cooldown_minutes)
        )
    
    def _create_lambda_consumer(self) -> None:
        """Create Lambda consumer for Kinesis stream."""
        
        if not self.props.enable_lambda_consumer:
            return
        
        # Create IAM role for Lambda consumer
        self.consumer_role = self.create_service_role(
            "KinesisConsumerRole",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaBasicExecutionRole"
            ],
            inline_policies={
                "KinesisAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kinesis:DescribeStream",
                                "kinesis:GetShardIterator",
                                "kinesis:GetRecords",
                                "kinesis:ListShards"
                            ],
                            resources=[self.stream.stream_arn]
                        )
                    ]
                ),
                "KMSAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kms:Decrypt"
                            ],
                            resources=[self.encryption_key.key_arn]
                        )
                    ]
                ) if self.props.enable_encryption else None
            }
        )
        
        # Create Lambda consumer function
        self.consumer_lambda = lambda_.Function(
            self,
            "KinesisConsumer",
            function_name=self.get_resource_name("consumer"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="kinesis_consumer.handler",
            code=lambda_.Code.from_asset("src/lambda/kinesis"),
            role=self.consumer_role,
            memory_size=self.props.consumer_lambda_memory,
            timeout=Duration.minutes(self.props.consumer_lambda_timeout),
            environment={
                "STREAM_NAME": self.stream.stream_name,
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED
        )
        
        # Add Kinesis event source
        from aws_cdk import aws_lambda_event_sources as lambda_event_sources
        
        self.consumer_lambda.add_event_source(
            lambda_event_sources.KinesisEventSource(
                stream=self.stream,
                starting_position=getattr(lambda_.StartingPosition, self.props.starting_position),
                batch_size=self.props.batch_size,
                max_batching_window=Duration.seconds(5),
                retry_attempts=3,
                on_failure=lambda_event_sources.SqsDestination(
                    self._create_dlq()
                ) if self.props.enable_dlq else None
            )
        )
    
    def _create_dlq(self):
        """Create dead letter queue for failed records."""
        from aws_cdk import aws_sqs as sqs
        
        return sqs.Queue(
            self,
            "KinesisDLQ",
            queue_name=self.get_resource_name("kinesis-dlq"),
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.encryption_key,
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(self.props.consumer_lambda_timeout * 6)
        )
    
    def _create_enhanced_fanout(self) -> None:
        """Create enhanced fan-out consumers."""
        
        if not self.props.enable_enhanced_fanout:
            return
        
        self.fanout_consumers = []
        
        for consumer_name in self.props.consumer_names:
            consumer = kinesis.CfnStreamConsumer(
                self,
                f"Consumer{consumer_name.title()}",
                stream_arn=self.stream.stream_arn,
                consumer_name=f"{self.get_resource_name('consumer')}-{consumer_name}"
            )
            self.fanout_consumers.append(consumer)
    
    def _create_analytics_application(self) -> None:
        """Create Kinesis Analytics application."""
        
        if not self.props.enable_analytics:
            return
        
        # Create CloudWatch log group for analytics
        self.analytics_log_group = logs.LogGroup(
            self,
            "AnalyticsLogGroup",
            log_group_name=f"/aws/kinesisanalytics/{self.get_resource_name('analytics')}",
            retention=getattr(logs.RetentionDays, f"_{self.props.log_retention_days}_DAYS", logs.RetentionDays.ONE_MONTH),
            encryption_key=self.encryption_key,
            removal_policy=self._get_removal_policy()
        )
        
        # Create IAM role for Kinesis Analytics
        analytics_role = self.create_service_role(
            "KinesisAnalyticsRole",
            "kinesisanalytics.amazonaws.com",
            inline_policies={
                "KinesisAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kinesis:DescribeStream",
                                "kinesis:GetShardIterator",
                                "kinesis:GetRecords",
                                "kinesis:ListShards"
                            ],
                            resources=[self.stream.stream_arn]
                        )
                    ]
                ),
                "CloudWatchLogsAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:PutLogEvents"
                            ],
                            resources=[self.analytics_log_group.log_group_arn]
                        )
                    ]
                )
            }
        )
        
        # Create Kinesis Analytics application
        self.analytics_application = analytics.CfnApplication(
            self,
            "KinesisAnalyticsApp",
            application_name=self.props.analytics_application_name or self.get_resource_name("analytics"),
            application_description=f"Real-time analytics for {self.project_name}",
            application_code=self._get_analytics_sql_code(),
            inputs=[
                analytics.CfnApplication.InputProperty(
                    name_prefix="SOURCE_SQL_STREAM",
                    kinesis_stream_input=analytics.CfnApplication.KinesisStreamsInputProperty(
                        resource_arn=self.stream.stream_arn,
                        role_arn=analytics_role.role_arn
                    ),
                    input_schema=analytics.CfnApplication.InputSchemaProperty(
                        record_columns=[
                            analytics.CfnApplication.RecordColumnProperty(
                                name="timestamp",
                                sql_type="TIMESTAMP",
                                mapping="$.timestamp"
                            ),
                            analytics.CfnApplication.RecordColumnProperty(
                                name="data",
                                sql_type="VARCHAR(32)",
                                mapping="$.data"
                            )
                        ],
                        record_format=analytics.CfnApplication.RecordFormatProperty(
                            record_format_type="JSON",
                            mapping_parameters=analytics.CfnApplication.MappingParametersProperty(
                                json_mapping_parameters=analytics.CfnApplication.JSONMappingParametersProperty(
                                    record_row_path="$"
                                )
                            )
                        )
                    )
                )
            ]
        )
    
    def _get_analytics_sql_code(self) -> str:
        """Get SQL code for Kinesis Analytics application."""
        if self.props.sql_queries:
            return "\n".join(self.props.sql_queries)
        
        # Default SQL for basic analytics
        return """
        CREATE OR REPLACE STREAM "DESTINATION_SQL_STREAM" (
            timestamp TIMESTAMP,
            data VARCHAR(32),
            record_count INTEGER
        );
        
        CREATE OR REPLACE PUMP "STREAM_PUMP" AS INSERT INTO "DESTINATION_SQL_STREAM"
        SELECT STREAM
            ROWTIME_TO_TIMESTAMP(ROWTIME) as timestamp,
            data,
            COUNT(*) OVER (RANGE INTERVAL '1' MINUTE PRECEDING) as record_count
        FROM "SOURCE_SQL_STREAM_001";
        """
    
    def _create_backup_configuration(self) -> None:
        """Create backup configuration for Kinesis data."""
        
        if not self.props.enable_backup_to_s3:
            return
        
        # Create S3 bucket for backup
        self.backup_bucket = s3.Bucket(
            self,
            "KinesisBackupBucket",
            bucket_name=self.props.backup_bucket_name or self.get_resource_name("backup"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy(),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="KinesisBackupLifecycle",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )
        
        # Create Lambda function for backup
        backup_role = self.create_service_role(
            "KinesisBackupRole",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaBasicExecutionRole"
            ],
            inline_policies={
                "KinesisAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kinesis:DescribeStream",
                                "kinesis:GetShardIterator",
                                "kinesis:GetRecords",
                                "kinesis:ListShards"
                            ],
                            resources=[self.stream.stream_arn]
                        )
                    ]
                ),
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:PutObject",
                                "s3:PutObjectAcl"
                            ],
                            resources=[
                                f"{self.backup_bucket.bucket_arn}/{self.props.backup_prefix}*"
                            ]
                        )
                    ]
                )
            }
        )
        
        self.backup_lambda = lambda_.Function(
            self,
            "KinesisBackupLambda",
            function_name=self.get_resource_name("backup"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="kinesis_backup.handler",
            code=lambda_.Code.from_asset("src/lambda/kinesis"),
            role=backup_role,
            memory_size=1024,
            timeout=Duration.minutes(15),
            environment={
                "STREAM_NAME": self.stream.stream_name,
                "BACKUP_BUCKET": self.backup_bucket.bucket_name,
                "BACKUP_PREFIX": self.props.backup_prefix,
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            }
        )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.incoming_records_metric = cloudwatch.Metric(
            namespace="AWS/Kinesis",
            metric_name="IncomingRecords",
            dimensions_map={
                "StreamName": self.stream.stream_name
            }
        )
        
        self.incoming_bytes_metric = cloudwatch.Metric(
            namespace="AWS/Kinesis",
            metric_name="IncomingBytes",
            dimensions_map={
                "StreamName": self.stream.stream_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighIncomingRecords",
            self.incoming_records_metric,
            threshold=1000,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High incoming record rate"
        )
        
        self.create_alarm(
            "WriteProvisionedThroughputExceeded",
            cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="WriteProvisionedThroughputExceeded",
                dimensions_map={
                    "StreamName": self.stream.stream_name
                }
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            description="Write throughput exceeded"
        )
        
        self.create_alarm(
            "ReadProvisionedThroughputExceeded",
            cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="ReadProvisionedThroughputExceeded",
                dimensions_map={
                    "StreamName": self.stream.stream_name
                }
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            description="Read throughput exceeded"
        )
        
        # Consumer monitoring
        if self.props.enable_lambda_consumer and hasattr(self, 'consumer_lambda'):
            self.create_alarm(
                "ConsumerErrors",
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={
                        "FunctionName": self.consumer_lambda.function_name
                    }
                ),
                threshold=5,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High error rate in Kinesis consumer"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "StreamName",
            self.stream.stream_name,
            "Name of the Kinesis stream"
        )
        
        self.add_output(
            "StreamArn",
            self.stream.stream_arn,
            "ARN of the Kinesis stream"
        )
        
        if self.props.enable_lambda_consumer and hasattr(self, 'consumer_lambda'):
            self.add_output(
                "ConsumerLambdaArn",
                self.consumer_lambda.function_arn,
                "ARN of the consumer Lambda function"
            )
        
        if self.props.enable_analytics and hasattr(self, 'analytics_application'):
            self.add_output(
                "AnalyticsApplicationName",
                self.analytics_application.ref,
                "Name of the Kinesis Analytics application"
            )
        
        if self.props.enable_backup_to_s3 and hasattr(self, 'backup_bucket'):
            self.add_output(
                "BackupBucketName",
                self.backup_bucket.bucket_name,
                "Name of the backup S3 bucket"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.incoming_records_metric,
            self.incoming_bytes_metric,
            cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="OutgoingRecords",
                dimensions_map={
                    "StreamName": self.stream.stream_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="OutgoingBytes",
                dimensions_map={
                    "StreamName": self.stream.stream_name
                }
            )
        ]
        
        if self.props.enable_lambda_consumer and hasattr(self, 'consumer_lambda'):
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    dimensions_map={
                        "FunctionName": self.consumer_lambda.function_name
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    dimensions_map={
                        "FunctionName": self.consumer_lambda.function_name
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
