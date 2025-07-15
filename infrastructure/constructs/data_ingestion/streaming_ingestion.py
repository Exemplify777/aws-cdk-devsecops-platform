"""
Streaming Data Ingestion Construct for DevSecOps Platform.

This construct implements Kinesis Data Streams → Lambda → S3 pattern with
dead letter queues, auto-scaling, and comprehensive error handling.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_kinesis as kinesis,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_s3 as s3,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_cloudwatch as cloudwatch,
    aws_applicationautoscaling as autoscaling,
    aws_kinesisfirehose as firehose,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class StreamingIngestionProps(ConstructProps):
    """Properties for Streaming Ingestion Construct."""
    
    # Kinesis Configuration
    stream_name: Optional[str] = None
    shard_count: int = 2
    retention_hours: int = 24
    enable_enhanced_fanout: bool = False
    
    # Lambda Configuration
    lambda_memory_size: int = 1024
    lambda_timeout_minutes: int = 5
    lambda_runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9
    batch_size: int = 100
    max_batching_window_seconds: int = 5
    parallelization_factor: int = 1
    
    # S3 Configuration
    output_bucket_name: Optional[str] = None
    enable_compression: bool = True
    output_format: str = "json"  # json, parquet, csv
    partitioning_keys: List[str] = None
    
    # Firehose Configuration (optional)
    enable_firehose: bool = False
    firehose_buffer_size_mb: int = 5
    firehose_buffer_interval_seconds: int = 300
    
    # Error Handling
    enable_dlq: bool = True
    max_retry_attempts: int = 3
    enable_bisect_on_error: bool = True
    
    # Auto Scaling
    enable_auto_scaling: bool = True
    min_shards: int = 1
    max_shards: int = 10
    target_utilization: float = 70.0
    
    # Monitoring
    enable_detailed_monitoring: bool = True
    enable_enhanced_monitoring: bool = False


class StreamingIngestionConstruct(BaseConstruct):
    """
    Streaming Data Ingestion Construct.
    
    Implements a comprehensive streaming data ingestion pipeline with:
    - Kinesis Data Streams for real-time data ingestion
    - Lambda functions for stream processing
    - S3 for data storage with partitioning
    - Optional Kinesis Data Firehose for simplified delivery
    - Auto-scaling based on stream utilization
    - Dead letter queues for error handling
    - Comprehensive monitoring and alerting
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: StreamingIngestionProps,
        **kwargs
    ) -> None:
        """
        Initialize Streaming Ingestion Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Create resources
        self._create_kinesis_stream()
        self._create_s3_bucket()
        self._create_lambda_function()
        self._create_error_handling()
        self._setup_stream_processing()
        self._setup_auto_scaling()
        self._create_firehose_delivery()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_kinesis_stream(self) -> None:
        """Create Kinesis Data Stream."""
        
        self.kinesis_stream = kinesis.Stream(
            self,
            "DataStream",
            stream_name=self.props.stream_name or self.get_resource_name("stream"),
            shard_count=self.props.shard_count,
            retention_period=Duration.hours(self.props.retention_hours),
            encryption=kinesis.StreamEncryption.KMS,
            encryption_key=self.encryption_key
        )
        
        # Enable enhanced fan-out if requested
        if self.props.enable_enhanced_fanout:
            kinesis.CfnStreamConsumer(
                self,
                "EnhancedConsumer",
                stream_arn=self.kinesis_stream.stream_arn,
                consumer_name=f"{self.get_resource_name('consumer')}"
            )
    
    def _create_s3_bucket(self) -> None:
        """Create S3 bucket for processed data."""
        
        self.output_bucket = s3.Bucket(
            self,
            "OutputBucket",
            bucket_name=self.props.output_bucket_name or self.get_resource_name("streaming-output"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy(),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="StreamingDataLifecycle",
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
    
    def _create_lambda_function(self) -> None:
        """Create Lambda function for stream processing."""
        
        # Create IAM role for Lambda
        self.lambda_role = self.create_service_role(
            "StreamProcessorLambda",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaVPCAccessExecutionRole"
            ],
            inline_policies={
                "KinesisAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kinesis:DescribeStream",
                                "kinesis:DescribeStreamSummary",
                                "kinesis:GetRecords",
                                "kinesis:GetShardIterator",
                                "kinesis:ListShards",
                                "kinesis:ListStreams",
                                "kinesis:SubscribeToShard"
                            ],
                            resources=[self.kinesis_stream.stream_arn]
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
                                f"{self.output_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                ),
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
        
        # Create Lambda function
        self.stream_processor = lambda_.Function(
            self,
            "StreamProcessor",
            function_name=self.get_resource_name("stream-processor"),
            runtime=self.props.lambda_runtime,
            handler="stream_processor.handler",
            code=lambda_.Code.from_asset("src/lambda/streaming_ingestion"),
            role=self.lambda_role,
            memory_size=self.props.lambda_memory_size,
            timeout=Duration.minutes(self.props.lambda_timeout_minutes),
            environment={
                "OUTPUT_BUCKET": self.output_bucket.bucket_name,
                "OUTPUT_FORMAT": self.props.output_format,
                "ENABLE_COMPRESSION": str(self.props.enable_compression),
                "PARTITIONING_KEYS": json.dumps(self.props.partitioning_keys or []),
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED,
            retry_attempts=self.props.max_retry_attempts,
            reserved_concurrent_executions=self.props.shard_count * 2  # 2x shard count
        )
    
    def _create_error_handling(self) -> None:
        """Create error handling resources."""
        
        if self.props.enable_dlq:
            # Create dead letter queue
            self.dlq = sqs.Queue(
                self,
                "StreamingDLQ",
                queue_name=self.get_resource_name("streaming-dlq"),
                encryption=sqs.QueueEncryption.KMS,
                encryption_master_key=self.encryption_key,
                retention_period=Duration.days(14),
                visibility_timeout=Duration.minutes(self.props.lambda_timeout_minutes * 6)
            )
            
            # Create error processing Lambda
            self.error_processor = lambda_.Function(
                self,
                "ErrorProcessor",
                function_name=self.get_resource_name("error-processor"),
                runtime=self.props.lambda_runtime,
                handler="error_processor.handler",
                code=lambda_.Code.from_asset("src/lambda/streaming_ingestion"),
                role=self.lambda_role,
                memory_size=512,
                timeout=Duration.minutes(5),
                environment={
                    "ERROR_BUCKET": self.output_bucket.bucket_name,
                    "ERROR_PREFIX": "errors/",
                    "LOG_LEVEL": "INFO"
                }
            )
            
            # Connect DLQ to error processor
            self.error_processor.add_event_source(
                lambda_event_sources.SqsEventSource(
                    queue=self.dlq,
                    batch_size=10
                )
            )
    
    def _setup_stream_processing(self) -> None:
        """Set up Kinesis stream processing."""
        
        # Add Kinesis event source to Lambda
        event_source_props = {
            "starting_position": lambda_.StartingPosition.LATEST,
            "batch_size": self.props.batch_size,
            "max_batching_window": Duration.seconds(self.props.max_batching_window_seconds),
            "retry_attempts": self.props.max_retry_attempts,
            "parallelization_factor": self.props.parallelization_factor,
            "bisect_batch_on_error": self.props.enable_bisect_on_error
        }
        
        if self.props.enable_dlq:
            event_source_props["on_failure"] = lambda_event_sources.SqsDlq(self.dlq)
        
        self.stream_processor.add_event_source(
            lambda_event_sources.KinesisEventSource(
                stream=self.kinesis_stream,
                **event_source_props
            )
        )
    
    def _setup_auto_scaling(self) -> None:
        """Set up auto-scaling for Kinesis stream."""
        
        if not self.props.enable_auto_scaling:
            return
        
        # Create auto-scaling target
        self.scaling_target = autoscaling.ScalableTarget(
            self,
            "StreamScalingTarget",
            service_namespace=autoscaling.ServiceNamespace.KINESIS,
            resource_id=f"stream/{self.kinesis_stream.stream_name}",
            scalable_dimension="kinesis:shard:count",
            min_capacity=self.props.min_shards,
            max_capacity=self.props.max_shards
        )
        
        # Create scaling policy
        self.scaling_target.scale_on_metric(
            "StreamUtilizationScaling",
            metric=cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="IncomingRecords",
                dimensions_map={
                    "StreamName": self.kinesis_stream.stream_name
                },
                statistic="Sum"
            ),
            scaling_steps=[
                autoscaling.ScalingInterval(
                    upper=1000,
                    change=0
                ),
                autoscaling.ScalingInterval(
                    lower=1000,
                    upper=5000,
                    change=1
                ),
                autoscaling.ScalingInterval(
                    lower=5000,
                    change=2
                )
            ],
            adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
            cooldown=Duration.minutes(5)
        )
    
    def _create_firehose_delivery(self) -> None:
        """Create Kinesis Data Firehose delivery stream (optional)."""
        
        if not self.props.enable_firehose:
            return
        
        # Create IAM role for Firehose
        self.firehose_role = self.create_service_role(
            "FirehoseDelivery",
            "firehose.amazonaws.com",
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:AbortMultipartUpload",
                                "s3:GetBucketLocation",
                                "s3:GetObject",
                                "s3:ListBucket",
                                "s3:ListBucketMultipartUploads",
                                "s3:PutObject"
                            ],
                            resources=[
                                self.output_bucket.bucket_arn,
                                f"{self.output_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                ),
                "KinesisAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kinesis:DescribeStream",
                                "kinesis:GetShardIterator",
                                "kinesis:GetRecords"
                            ],
                            resources=[self.kinesis_stream.stream_arn]
                        )
                    ]
                ),
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
        
        # Create Firehose delivery stream
        self.delivery_stream = firehose.CfnDeliveryStream(
            self,
            "FirehoseDeliveryStream",
            delivery_stream_name=self.get_resource_name("firehose"),
            delivery_stream_type="KinesisStreamAsSource",
            kinesis_stream_source_configuration=firehose.CfnDeliveryStream.KinesisStreamSourceConfigurationProperty(
                kinesis_stream_arn=self.kinesis_stream.stream_arn,
                role_arn=self.firehose_role.role_arn
            ),
            extended_s3_destination_configuration=firehose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                bucket_arn=self.output_bucket.bucket_arn,
                role_arn=self.firehose_role.role_arn,
                prefix="firehose-data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/",
                error_output_prefix="firehose-errors/",
                buffering_hints=firehose.CfnDeliveryStream.BufferingHintsProperty(
                    size_in_m_bs=self.props.firehose_buffer_size_mb,
                    interval_in_seconds=self.props.firehose_buffer_interval_seconds
                ),
                compression_format="GZIP" if self.props.enable_compression else "UNCOMPRESSED",
                encryption_configuration=firehose.CfnDeliveryStream.EncryptionConfigurationProperty(
                    kms_encryption_config=firehose.CfnDeliveryStream.KMSEncryptionConfigProperty(
                        awskms_key_arn=self.encryption_key.key_arn
                    )
                )
            )
        )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.records_processed_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/StreamingIngestion",
            metric_name="RecordsProcessed",
            dimensions_map={
                "Environment": self.environment,
                "StreamName": self.kinesis_stream.stream_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighStreamErrorRate",
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={"FunctionName": self.stream_processor.function_name}
            ),
            threshold=10,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High error rate in stream processing"
        )
        
        self.create_alarm(
            "StreamIteratorAge",
            cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="GetRecords.IteratorAgeMilliseconds",
                dimensions_map={"StreamName": self.kinesis_stream.stream_name}
            ),
            threshold=Duration.minutes(5).to_milliseconds(),
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="Stream processing lag detected"
        )
        
        if self.props.enable_dlq:
            self.create_alarm(
                "MessagesInStreamingDLQ",
                cloudwatch.Metric(
                    namespace="AWS/SQS",
                    metric_name="ApproximateNumberOfMessages",
                    dimensions_map={"QueueName": self.dlq.queue_name}
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="Messages in streaming dead letter queue"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "StreamName",
            self.kinesis_stream.stream_name,
            "Name of the Kinesis data stream"
        )
        
        self.add_output(
            "StreamArn",
            self.kinesis_stream.stream_arn,
            "ARN of the Kinesis data stream"
        )
        
        self.add_output(
            "OutputBucketName",
            self.output_bucket.bucket_name,
            "Name of the output S3 bucket"
        )
        
        self.add_output(
            "StreamProcessorFunctionName",
            self.stream_processor.function_name,
            "Name of the stream processor Lambda function"
        )
        
        if self.props.enable_firehose:
            self.add_output(
                "FirehoseDeliveryStreamName",
                self.delivery_stream.ref,
                "Name of the Firehose delivery stream"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        return [
            self.records_processed_metric,
            cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="IncomingRecords",
                dimensions_map={"StreamName": self.kinesis_stream.stream_name}
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions_map={"FunctionName": self.stream_processor.function_name}
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Duration",
                dimensions_map={"FunctionName": self.stream_processor.function_name}
            )
        ]
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
