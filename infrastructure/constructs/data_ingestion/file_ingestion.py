"""
File Data Ingestion Construct for DevSecOps Platform.

This construct implements S3 event-driven file processing with format validation,
metadata extraction, and comprehensive error handling.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_cloudwatch as cloudwatch,
    aws_events as events,
    aws_events_targets as targets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class FileIngestionProps(ConstructProps):
    """Properties for File Ingestion Construct."""
    
    # File Processing Configuration
    supported_file_formats: List[str] = None  # csv, json, parquet, avro, xml, txt
    max_file_size_mb: int = 1024  # 1GB default
    enable_format_validation: bool = True
    enable_metadata_extraction: bool = True
    enable_virus_scanning: bool = True
    
    # Input Configuration
    input_bucket_name: Optional[str] = None
    input_prefixes: List[str] = None  # Prefixes to monitor
    exclude_prefixes: List[str] = None  # Prefixes to exclude
    
    # Output Configuration
    processed_bucket_name: Optional[str] = None
    quarantine_bucket_name: Optional[str] = None
    enable_data_partitioning: bool = True
    partition_keys: List[str] = None
    
    # Lambda Configuration
    lambda_memory_size: int = 1024
    lambda_timeout_minutes: int = 15
    lambda_runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9
    
    # Step Functions Configuration
    enable_step_functions: bool = True
    enable_parallel_processing: bool = True
    max_parallel_executions: int = 10
    
    # Data Validation
    enable_schema_validation: bool = True
    schema_definitions: Dict[str, Any] = None
    enable_data_quality_checks: bool = True
    quality_rules: Dict[str, Any] = None
    
    # Error Handling
    enable_dlq: bool = True
    max_retry_attempts: int = 3
    quarantine_invalid_files: bool = True
    
    # Monitoring
    enable_detailed_monitoring: bool = True


class FileIngestionConstruct(BaseConstruct):
    """
    File Data Ingestion Construct.
    
    Implements a comprehensive file ingestion pipeline with:
    - S3 event-driven file processing
    - Format validation and metadata extraction
    - Virus scanning and security checks
    - Step Functions for complex workflows
    - Data quality validation
    - Quarantine for invalid files
    - Comprehensive monitoring and alerting
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: FileIngestionProps,
        **kwargs
    ) -> None:
        """
        Initialize File Ingestion Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.supported_file_formats is None:
            self.props.supported_file_formats = ["csv", "json", "parquet", "avro"]
        if self.props.input_prefixes is None:
            self.props.input_prefixes = ["incoming/"]
        if self.props.partition_keys is None:
            self.props.partition_keys = ["year", "month", "day"]
        
        # Create resources
        self._create_s3_buckets()
        self._create_lambda_functions()
        self._create_step_functions()
        self._create_error_handling()
        self._setup_event_processing()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_s3_buckets(self) -> None:
        """Create S3 buckets for file processing."""
        
        # Input bucket (if not provided)
        if not self.props.input_bucket_name:
            self.input_bucket = s3.Bucket(
                self,
                "InputBucket",
                bucket_name=self.get_resource_name("file-input"),
                versioning=True,
                encryption=s3.BucketEncryption.KMS,
                encryption_key=self.encryption_key,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                removal_policy=self._get_removal_policy(),
                event_bridge_enabled=True
            )
        
        # Processed data bucket
        self.processed_bucket = s3.Bucket(
            self,
            "ProcessedBucket",
            bucket_name=self.props.processed_bucket_name or self.get_resource_name("file-processed"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy(),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ProcessedFileLifecycle",
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
        
        # Quarantine bucket for invalid files
        self.quarantine_bucket = s3.Bucket(
            self,
            "QuarantineBucket",
            bucket_name=self.props.quarantine_bucket_name or self.get_resource_name("file-quarantine"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # Always retain quarantined files
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="QuarantineFileLifecycle",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(7)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(30)
                        )
                    ]
                )
            ]
        )
    
    def _create_lambda_functions(self) -> None:
        """Create Lambda functions for file processing."""
        
        # Create IAM role for Lambda functions
        self.lambda_role = self.create_service_role(
            "FileProcessorLambda",
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
                                "s3:ListBucket",
                                "s3:GetObjectTagging",
                                "s3:PutObjectTagging"
                            ],
                            resources=[
                                self.input_bucket.bucket_arn if hasattr(self, 'input_bucket') else f"arn:aws:s3:::{self.props.input_bucket_name}",
                                f"{self.input_bucket.bucket_arn}/*" if hasattr(self, 'input_bucket') else f"arn:aws:s3:::{self.props.input_bucket_name}/*",
                                self.processed_bucket.bucket_arn,
                                f"{self.processed_bucket.bucket_arn}/*",
                                self.quarantine_bucket.bucket_arn,
                                f"{self.quarantine_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                ),
                "StepFunctionsAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "states:StartExecution"
                            ],
                            resources=["*"]  # Will be restricted after Step Functions creation
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
        
        # File validator Lambda
        self.file_validator = lambda_.Function(
            self,
            "FileValidator",
            function_name=self.get_resource_name("file-validator"),
            runtime=self.props.lambda_runtime,
            handler="file_validator.handler",
            code=lambda_.Code.from_asset("src/lambda/file_ingestion"),
            role=self.lambda_role,
            memory_size=512,
            timeout=Duration.minutes(5),
            environment={
                "SUPPORTED_FORMATS": json.dumps(self.props.supported_file_formats),
                "MAX_FILE_SIZE_MB": str(self.props.max_file_size_mb),
                "ENABLE_FORMAT_VALIDATION": str(self.props.enable_format_validation),
                "ENABLE_VIRUS_SCANNING": str(self.props.enable_virus_scanning),
                "QUARANTINE_BUCKET": self.quarantine_bucket.bucket_name,
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED
        )
        
        # Metadata extractor Lambda
        self.metadata_extractor = lambda_.Function(
            self,
            "MetadataExtractor",
            function_name=self.get_resource_name("metadata-extractor"),
            runtime=self.props.lambda_runtime,
            handler="metadata_extractor.handler",
            code=lambda_.Code.from_asset("src/lambda/file_ingestion"),
            role=self.lambda_role,
            memory_size=1024,
            timeout=Duration.minutes(10),
            environment={
                "ENABLE_METADATA_EXTRACTION": str(self.props.enable_metadata_extraction),
                "ENABLE_SCHEMA_VALIDATION": str(self.props.enable_schema_validation),
                "SCHEMA_DEFINITIONS": json.dumps(self.props.schema_definitions or {}),
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED
        )
        
        # File processor Lambda
        self.file_processor = lambda_.Function(
            self,
            "FileProcessor",
            function_name=self.get_resource_name("file-processor"),
            runtime=self.props.lambda_runtime,
            handler="file_processor.handler",
            code=lambda_.Code.from_asset("src/lambda/file_ingestion"),
            role=self.lambda_role,
            memory_size=self.props.lambda_memory_size,
            timeout=Duration.minutes(self.props.lambda_timeout_minutes),
            environment={
                "PROCESSED_BUCKET": self.processed_bucket.bucket_name,
                "ENABLE_PARTITIONING": str(self.props.enable_data_partitioning),
                "PARTITION_KEYS": json.dumps(self.props.partition_keys),
                "ENABLE_QUALITY_CHECKS": str(self.props.enable_data_quality_checks),
                "QUALITY_RULES": json.dumps(self.props.quality_rules or {}),
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED
        )
        
        # Error handler Lambda
        self.error_handler = lambda_.Function(
            self,
            "ErrorHandler",
            function_name=self.get_resource_name("error-handler"),
            runtime=self.props.lambda_runtime,
            handler="error_handler.handler",
            code=lambda_.Code.from_asset("src/lambda/file_ingestion"),
            role=self.lambda_role,
            memory_size=512,
            timeout=Duration.minutes(5),
            environment={
                "QUARANTINE_BUCKET": self.quarantine_bucket.bucket_name,
                "QUARANTINE_INVALID_FILES": str(self.props.quarantine_invalid_files),
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            }
        )
    
    def _create_step_functions(self) -> None:
        """Create Step Functions workflow for file processing."""
        
        if not self.props.enable_step_functions:
            return
        
        # Define Step Functions tasks
        validate_task = sfn_tasks.LambdaInvoke(
            self,
            "ValidateFileTask",
            lambda_function=self.file_validator,
            output_path="$.Payload"
        )
        
        extract_metadata_task = sfn_tasks.LambdaInvoke(
            self,
            "ExtractMetadataTask",
            lambda_function=self.metadata_extractor,
            output_path="$.Payload"
        )
        
        process_file_task = sfn_tasks.LambdaInvoke(
            self,
            "ProcessFileTask",
            lambda_function=self.file_processor,
            output_path="$.Payload"
        )
        
        handle_error_task = sfn_tasks.LambdaInvoke(
            self,
            "HandleErrorTask",
            lambda_function=self.error_handler,
            output_path="$.Payload"
        )
        
        # Define success and failure states
        success_state = sfn.Succeed(self, "ProcessingSucceeded")
        failure_state = sfn.Fail(self, "ProcessingFailed")
        
        # Create choice state for validation result
        validation_choice = sfn.Choice(self, "ValidationChoice")
        validation_choice.when(
            sfn.Condition.boolean_equals("$.isValid", True),
            extract_metadata_task.next(process_file_task).next(success_state)
        ).otherwise(
            handle_error_task.next(failure_state)
        )
        
        # Define the workflow
        definition = validate_task.next(validation_choice)
        
        # Add error handling
        definition.add_catch(
            handle_error_task.next(failure_state),
            errors=["States.ALL"],
            result_path="$.error"
        )
        
        # Create Step Functions state machine
        self.file_processing_workflow = sfn.StateMachine(
            self,
            "FileProcessingWorkflow",
            state_machine_name=self.get_resource_name("file-workflow"),
            definition=definition,
            timeout=Duration.minutes(30),
            tracing_enabled=self.props.enable_detailed_monitoring
        )
        
        # Grant Step Functions permissions to invoke Lambda functions
        self.file_processing_workflow.grant_start_execution(self.lambda_role)
    
    def _create_error_handling(self) -> None:
        """Create error handling resources."""
        
        if self.props.enable_dlq:
            # Create dead letter queue
            self.dlq = sqs.Queue(
                self,
                "FileDLQ",
                queue_name=self.get_resource_name("file-dlq"),
                encryption=sqs.QueueEncryption.KMS,
                encryption_master_key=self.encryption_key,
                retention_period=Duration.days(14),
                visibility_timeout=Duration.minutes(self.props.lambda_timeout_minutes * 6)
            )
            
            # Add DLQ to Lambda functions
            for lambda_function in [self.file_validator, self.metadata_extractor, 
                                  self.file_processor, self.error_handler]:
                lambda_function.add_dead_letter_queue(
                    dead_letter_queue=self.dlq
                )
    
    def _setup_event_processing(self) -> None:
        """Set up S3 event processing."""
        
        # Create EventBridge rule for S3 object creation
        s3_object_created_rule = events.Rule(
            self,
            "S3ObjectCreatedRule",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {
                        "name": [
                            self.input_bucket.bucket_name if hasattr(self, 'input_bucket') 
                            else self.props.input_bucket_name
                        ]
                    },
                    "object": {
                        "key": [
                            {"prefix": prefix} for prefix in self.props.input_prefixes
                        ]
                    }
                }
            )
        )
        
        # Target Step Functions workflow or Lambda function
        if self.props.enable_step_functions and hasattr(self, 'file_processing_workflow'):
            s3_object_created_rule.add_target(
                targets.SfnStateMachine(
                    self.file_processing_workflow,
                    input=events.RuleTargetInput.from_event_path("$.detail")
                )
            )
        else:
            s3_object_created_rule.add_target(
                targets.LambdaFunction(self.file_validator)
            )
        
        # Add S3 notification if using own input bucket
        if hasattr(self, 'input_bucket'):
            for prefix in self.props.input_prefixes:
                self.input_bucket.add_event_notification(
                    s3.EventType.OBJECT_CREATED,
                    s3n.LambdaDestination(self.file_validator),
                    s3.NotificationKeyFilter(prefix=prefix)
                )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.files_processed_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/FileIngestion",
            metric_name="FilesProcessed",
            dimensions_map={
                "Environment": self.environment,
                "Construct": self.construct_name
            }
        )
        
        self.files_quarantined_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/FileIngestion",
            metric_name="FilesQuarantined",
            dimensions_map={
                "Environment": self.environment,
                "Construct": self.construct_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighFileErrorRate",
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={"FunctionName": self.file_processor.function_name}
            ),
            threshold=5,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High error rate in file processing"
        )
        
        self.create_alarm(
            "HighQuarantineRate",
            self.files_quarantined_metric,
            threshold=10,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High rate of files being quarantined"
        )
        
        if self.props.enable_step_functions and hasattr(self, 'file_processing_workflow'):
            self.create_alarm(
                "StepFunctionExecutionFailures",
                cloudwatch.Metric(
                    namespace="AWS/States",
                    metric_name="ExecutionsFailed",
                    dimensions_map={
                        "StateMachineArn": self.file_processing_workflow.state_machine_arn
                    }
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="Step Functions execution failures"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        if hasattr(self, 'input_bucket'):
            self.add_output(
                "InputBucketName",
                self.input_bucket.bucket_name,
                "Name of the input S3 bucket"
            )
        
        self.add_output(
            "ProcessedBucketName",
            self.processed_bucket.bucket_name,
            "Name of the processed files S3 bucket"
        )
        
        self.add_output(
            "QuarantineBucketName",
            self.quarantine_bucket.bucket_name,
            "Name of the quarantine S3 bucket"
        )
        
        self.add_output(
            "FileProcessorFunctionName",
            self.file_processor.function_name,
            "Name of the file processor Lambda function"
        )
        
        if self.props.enable_step_functions and hasattr(self, 'file_processing_workflow'):
            self.add_output(
                "FileProcessingWorkflowArn",
                self.file_processing_workflow.state_machine_arn,
                "ARN of the file processing Step Functions workflow"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.files_processed_metric,
            self.files_quarantined_metric,
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions_map={"FunctionName": self.file_processor.function_name}
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Duration",
                dimensions_map={"FunctionName": self.file_processor.function_name}
            )
        ]
        
        if self.props.enable_step_functions and hasattr(self, 'file_processing_workflow'):
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/States",
                    metric_name="ExecutionsStarted",
                    dimensions_map={
                        "StateMachineArn": self.file_processing_workflow.state_machine_arn
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/States",
                    metric_name="ExecutionTime",
                    dimensions_map={
                        "StateMachineArn": self.file_processing_workflow.state_machine_arn
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
