"""
Raw Data Ingestion Construct for DevSecOps Platform.

This construct implements S3 → Lambda → Glue Crawler pattern with automatic
schema detection, data validation, and error handling for raw data ingestion.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_glue as glue,
    aws_iam as iam,
    aws_s3_notifications as s3n,
    aws_sqs as sqs,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class RawDataIngestionProps(ConstructProps):
    """Properties for Raw Data Ingestion Construct."""
    
    # S3 Configuration
    raw_bucket_name: Optional[str] = None
    processed_bucket_name: Optional[str] = None
    enable_versioning: bool = True
    enable_lifecycle_policies: bool = True
    
    # Lambda Configuration
    lambda_memory_size: int = 1024
    lambda_timeout_minutes: int = 15
    lambda_runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9
    
    # Glue Configuration
    glue_database_name: Optional[str] = None
    crawler_schedule: Optional[str] = None  # Cron expression
    enable_schema_evolution: bool = True
    
    # Data Validation
    enable_data_validation: bool = True
    validation_rules: Optional[Dict[str, Any]] = None

    # Error Handling
    enable_dlq: bool = True
    max_retry_attempts: int = 3

    # Monitoring
    enable_detailed_monitoring: bool = True
    custom_metrics: Optional[List[str]] = None


class RawDataIngestionConstruct(BaseConstruct):
    """
    Raw Data Ingestion Construct.
    
    Implements a comprehensive raw data ingestion pipeline with:
    - S3 event-driven processing
    - Lambda-based data validation and transformation
    - Glue Crawler for automatic schema detection
    - Dead letter queue for error handling
    - Comprehensive monitoring and alerting
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: RawDataIngestionProps,
        **kwargs
    ) -> None:
        """
        Initialize Raw Data Ingestion Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Create resources
        self._create_s3_buckets()
        self._create_lambda_function()
        self._create_glue_resources()
        self._create_error_handling()
        self._setup_event_processing()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_s3_buckets(self) -> None:
        """Create S3 buckets for raw and processed data."""
        
        # Raw data bucket
        self.raw_bucket = s3.Bucket(
            self,
            "RawDataBucket",
            bucket_name=self.props.raw_bucket_name or self.get_resource_name("raw-data"),
            versioning=self.props.enable_versioning,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy(),
            lifecycle_rules=self._get_lifecycle_rules() if self.props.enable_lifecycle_policies else None,
            event_bridge_enabled=True
        )

        # Apply standardized tags
        raw_bucket_tags = self.get_resource_tags(
            application="data-ingestion",
            component="raw-storage",
            data_classification=getattr(self.props, 'data_classification', 'internal'),
            backup_schedule="daily" if self.environment == "prod" else "weekly"
        )
        for key, value in raw_bucket_tags.items():
            if value:  # Only apply non-None values
                self.raw_bucket.node.add_metadata(f"tag:{key}", value)
        
        # Processed data bucket
        self.processed_bucket = s3.Bucket(
            self,
            "ProcessedDataBucket",
            bucket_name=self.props.processed_bucket_name or self.get_resource_name("processed-data"),
            versioning=self.props.enable_versioning,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy(),
            lifecycle_rules=self._get_lifecycle_rules() if self.props.enable_lifecycle_policies else None
        )

        # Apply standardized tags
        processed_bucket_tags = self.get_resource_tags(
            application="data-ingestion",
            component="processed-storage",
            data_classification=getattr(self.props, 'data_classification', 'internal'),
            backup_schedule="daily" if self.environment == "prod" else "weekly"
        )
        for key, value in processed_bucket_tags.items():
            if value:  # Only apply non-None values
                self.processed_bucket.node.add_metadata(f"tag:{key}", value)
        
        # Error bucket for failed processing
        self.error_bucket = s3.Bucket(
            self,
            "ErrorDataBucket",
            bucket_name=self.get_resource_name("error-data"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # Always retain error data
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ErrorDataRetention",
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
    
    def _get_lifecycle_rules(self) -> List[s3.LifecycleRule]:
        """Get S3 lifecycle rules based on environment."""
        rules = []
        
        if self.environment == "prod":
            rules.append(
                s3.LifecycleRule(
                    id="ProductionDataLifecycle",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(365)
                        )
                    ],
                    noncurrent_version_expiration=Duration.days(90)
                )
            )
        else:
            rules.append(
                s3.LifecycleRule(
                    id="NonProductionDataLifecycle",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(7)
                        )
                    ],
                    expiration=Duration.days(30),
                    noncurrent_version_expiration=Duration.days(7)
                )
            )
        
        return rules
    
    def _create_lambda_function(self) -> None:
        """Create Lambda function for data processing."""
        
        # Create IAM role for Lambda
        self.lambda_role = self.create_service_role(
            "DataProcessorLambda",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaVPCAccessExecutionRole"
            ],
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                self.raw_bucket.bucket_arn,
                                f"{self.raw_bucket.bucket_arn}/*",
                                self.processed_bucket.bucket_arn,
                                f"{self.processed_bucket.bucket_arn}/*",
                                self.error_bucket.bucket_arn,
                                f"{self.error_bucket.bucket_arn}/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kms:Decrypt",
                                "kms:GenerateDataKey"
                            ],
                            resources=[self.encryption_key.key_arn]
                        )
                    ]
                ),
                "GlueAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "glue:StartCrawler",
                                "glue:GetCrawler",
                                "glue:GetCrawlerMetrics"
                            ],
                            resources=[
                                f"arn:aws:glue:{self.region}:{self.account}:crawler/{self.get_resource_name('data-crawler')}"
                            ]
                        )
                    ]
                )
            }
        )
        
        # Create Lambda function
        self.data_processor = lambda_.Function(
            self,
            "DataProcessor",
            function_name=self.get_resource_name("data-processor"),
            runtime=self.props.lambda_runtime,
            handler="data_processor.handler",
            code=lambda_.Code.from_asset("src/lambda/data_ingestion"),
            role=self.lambda_role,
            memory_size=self.props.lambda_memory_size,
            timeout=Duration.minutes(self.props.lambda_timeout_minutes),
            environment={
                "RAW_BUCKET": self.raw_bucket.bucket_name,
                "PROCESSED_BUCKET": self.processed_bucket.bucket_name,
                "ERROR_BUCKET": self.error_bucket.bucket_name,
                "GLUE_DATABASE": self.props.glue_database_name or self.get_resource_name("database"),
                "CRAWLER_NAME": self.get_resource_name("data-crawler"),
                "ENABLE_VALIDATION": str(self.props.enable_data_validation),
                "VALIDATION_RULES": str(self.props.validation_rules or {}),
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED,
            retry_attempts=self.props.max_retry_attempts
        )
    
    def _create_glue_resources(self) -> None:
        """Create Glue database and crawler."""
        
        # Create Glue database
        self.glue_database = glue.CfnDatabase(
            self,
            "GlueDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=self.props.glue_database_name or self.get_resource_name("database"),
                description=f"Data catalog for {self.project_name} raw data ingestion"
            )
        )
        
        # Create IAM role for Glue Crawler
        self.crawler_role = self.create_service_role(
            "GlueCrawler",
            "glue.amazonaws.com",
            managed_policies=[
                "service-role/AWSGlueServiceRole"
            ],
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                self.processed_bucket.bucket_arn,
                                f"{self.processed_bucket.bucket_arn}/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kms:Decrypt"
                            ],
                            resources=[self.encryption_key.key_arn]
                        )
                    ]
                )
            }
        )
        
        # Create Glue Crawler
        crawler_targets = glue.CfnCrawler.TargetsProperty(
            s3_targets=[
                glue.CfnCrawler.S3TargetProperty(
                    path=f"s3://{self.processed_bucket.bucket_name}/",
                    exclusions=["**/_SUCCESS", "**/_metadata", "**/.*"]
                )
            ]
        )
        
        self.data_crawler = glue.CfnCrawler(
            self,
            "DataCrawler",
            name=self.get_resource_name("data-crawler"),
            role=self.crawler_role.role_arn,
            database_name=self.glue_database.ref,
            targets=crawler_targets,
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                update_behavior="UPDATE_IN_DATABASE" if self.props.enable_schema_evolution else "LOG",
                delete_behavior="LOG"
            ),
            configuration=json.dumps({
                "Version": 1.0,
                "CrawlerOutput": {
                    "Partitions": {"AddOrUpdateBehavior": "InheritFromTable"},
                    "Tables": {"AddOrUpdateBehavior": "MergeNewColumns"}
                }
            }),
            schedule=glue.CfnCrawler.ScheduleProperty(
                schedule_expression=self.props.crawler_schedule
            ) if self.props.crawler_schedule else None
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
                visibility_timeout=Duration.minutes(self.props.lambda_timeout_minutes * 6)
            )
            
            # Add DLQ to Lambda function
            self.data_processor.add_dead_letter_queue(
                dead_letter_queue=self.dlq
            )
    
    def _setup_event_processing(self) -> None:
        """Set up S3 event processing."""
        
        # Add S3 event notification to Lambda
        self.raw_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.data_processor),
            s3.NotificationKeyFilter(prefix="incoming/")
        )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.processing_duration_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/DataIngestion",
            metric_name="ProcessingDuration",
            dimensions_map={
                "Environment": self.environment,
                "Construct": self.construct_name
            }
        )
        
        self.processed_files_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/DataIngestion",
            metric_name="ProcessedFiles",
            dimensions_map={
                "Environment": self.environment,
                "Construct": self.construct_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighErrorRate",
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={"FunctionName": self.data_processor.function_name}
            ),
            threshold=5,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High error rate in data processing"
        )
        
        self.create_alarm(
            "LongProcessingDuration",
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Duration",
                dimensions_map={"FunctionName": self.data_processor.function_name}
            ),
            threshold=Duration.minutes(10).to_milliseconds(),
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="Long processing duration detected"
        )
        
        if self.props.enable_dlq:
            self.create_alarm(
                "MessagesInDLQ",
                cloudwatch.Metric(
                    namespace="AWS/SQS",
                    metric_name="ApproximateNumberOfMessages",
                    dimensions_map={"QueueName": self.dlq.queue_name}
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="Messages in dead letter queue"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "RawBucketName",
            self.raw_bucket.bucket_name,
            "Name of the raw data S3 bucket"
        )
        
        self.add_output(
            "ProcessedBucketName", 
            self.processed_bucket.bucket_name,
            "Name of the processed data S3 bucket"
        )
        
        self.add_output(
            "DataProcessorFunctionName",
            self.data_processor.function_name,
            "Name of the data processor Lambda function"
        )
        
        self.add_output(
            "GlueDatabaseName",
            self.glue_database.ref,
            "Name of the Glue database"
        )
        
        self.add_output(
            "CrawlerName",
            self.data_crawler.ref,
            "Name of the Glue crawler"
        )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        return [
            self.processing_duration_metric,
            self.processed_files_metric,
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions_map={"FunctionName": self.data_processor.function_name}
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={"FunctionName": self.data_processor.function_name}
            )
        ]
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
