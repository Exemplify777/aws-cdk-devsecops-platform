"""
Batch Data Ingestion Construct for DevSecOps Platform.

This construct implements scheduled batch processing with EventBridge,
Lambda, and comprehensive retry mechanisms for reliable data ingestion.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
    aws_sqs as sqs,
    aws_cloudwatch as cloudwatch,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_batch as batch,
    aws_ec2 as ec2,
    aws_ecs as ecs,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class BatchIngestionProps(ConstructProps):
    """Properties for Batch Ingestion Construct."""
    
    # Scheduling Configuration
    schedule_expression: str = "cron(0 2 * * ? *)"  # Daily at 2 AM
    enable_scheduling: bool = True
    max_concurrent_executions: int = 5
    
    # Batch Processing Configuration
    enable_aws_batch: bool = False  # Use AWS Batch for large workloads
    batch_compute_type: str = "EC2"  # EC2, FARGATE, FARGATE_SPOT
    batch_instance_types: List[str] = None
    max_vcpus: int = 256
    
    # Lambda Configuration (for smaller workloads)
    lambda_memory_size: int = 3008  # Max for batch processing
    lambda_timeout_minutes: int = 15
    lambda_runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9
    enable_lambda_layers: bool = True
    
    # Data Source Configuration
    data_sources: List[Dict[str, Any]] = None
    source_systems: List[str] = None  # List of source system identifiers
    
    # Output Configuration
    output_bucket_name: Optional[str] = None
    enable_data_partitioning: bool = True
    partition_keys: List[str] = None
    output_format: str = "parquet"  # parquet, json, csv
    
    # Processing Configuration
    chunk_size: int = 1000  # Records per chunk
    enable_parallel_processing: bool = True
    max_parallel_chunks: int = 10
    enable_data_validation: bool = True
    
    # Retry Configuration
    max_retry_attempts: int = 3
    retry_backoff_multiplier: float = 2.0
    enable_exponential_backoff: bool = True
    
    # Error Handling
    enable_dlq: bool = True
    enable_error_notifications: bool = True
    
    # Monitoring
    enable_detailed_monitoring: bool = True
    enable_cost_monitoring: bool = True


class BatchIngestionConstruct(BaseConstruct):
    """
    Batch Data Ingestion Construct.
    
    Implements a comprehensive batch ingestion pipeline with:
    - EventBridge scheduled triggers
    - AWS Batch or Lambda for processing
    - Step Functions for workflow orchestration
    - Parallel processing with chunking
    - Comprehensive retry mechanisms
    - Error handling and notifications
    - Cost and performance monitoring
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: BatchIngestionProps,
        **kwargs
    ) -> None:
        """
        Initialize Batch Ingestion Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.batch_instance_types is None:
            self.props.batch_instance_types = ["m5.large", "m5.xlarge", "c5.large"]
        if self.props.partition_keys is None:
            self.props.partition_keys = ["year", "month", "day"]
        if self.props.data_sources is None:
            self.props.data_sources = []
        
        # Create resources
        self._create_s3_bucket()
        self._create_compute_environment()
        self._create_lambda_functions()
        self._create_step_functions()
        self._create_scheduling()
        self._create_error_handling()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_s3_bucket(self) -> None:
        """Create S3 bucket for batch processing output."""
        
        self.output_bucket = s3.Bucket(
            self,
            "BatchOutputBucket",
            bucket_name=self.props.output_bucket_name or self.get_resource_name("batch-output"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy(),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="BatchOutputLifecycle",
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
    
    def _create_compute_environment(self) -> None:
        """Create AWS Batch compute environment if enabled."""
        
        if not self.props.enable_aws_batch:
            return
        
        # Create VPC for Batch (simplified - would use VPC construct in practice)
        vpc = ec2.Vpc(
            self,
            "BatchVPC",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )
        
        # Create security group
        security_group = ec2.SecurityGroup(
            self,
            "BatchSecurityGroup",
            vpc=vpc,
            description="Security group for Batch compute environment",
            allow_all_outbound=True
        )
        
        # Create IAM role for Batch instances
        batch_instance_role = self.create_service_role(
            "BatchInstanceRole",
            "ec2.amazonaws.com",
            managed_policies=[
                "service-role/AmazonEC2ContainerServiceforEC2Role"
            ]
        )
        
        # Create instance profile
        batch_instance_profile = iam.CfnInstanceProfile(
            self,
            "BatchInstanceProfile",
            roles=[batch_instance_role.role_name]
        )
        
        # Create Batch service role
        batch_service_role = self.create_service_role(
            "BatchServiceRole",
            "batch.amazonaws.com",
            managed_policies=[
                "service-role/AWSBatchServiceRole"
            ]
        )
        
        # Create compute environment
        self.batch_compute_environment = batch.CfnComputeEnvironment(
            self,
            "BatchComputeEnvironment",
            type="MANAGED",
            state="ENABLED",
            compute_environment_name=self.get_resource_name("batch-compute"),
            service_role=batch_service_role.role_arn,
            compute_resources=batch.CfnComputeEnvironment.ComputeResourcesProperty(
                type=self.props.batch_compute_type,
                min_vcpus=0,
                max_vcpus=self.props.max_vcpus,
                desired_vcpus=0,
                instance_types=self.props.batch_instance_types,
                subnets=[subnet.subnet_id for subnet in vpc.private_subnets],
                security_group_ids=[security_group.security_group_id],
                instance_role=batch_instance_profile.attr_arn,
                tags={
                    "Name": self.get_resource_name("batch-instance"),
                    "Environment": self.environment,
                    "Project": self.project_name
                }
            )
        )
        
        # Create job queue
        self.batch_job_queue = batch.CfnJobQueue(
            self,
            "BatchJobQueue",
            job_queue_name=self.get_resource_name("batch-queue"),
            state="ENABLED",
            priority=1,
            compute_environment_order=[
                batch.CfnJobQueue.ComputeEnvironmentOrderProperty(
                    order=1,
                    compute_environment=self.batch_compute_environment.ref
                )
            ]
        )
        
        # Create job definition
        self.batch_job_definition = batch.CfnJobDefinition(
            self,
            "BatchJobDefinition",
            job_definition_name=self.get_resource_name("batch-job"),
            type="container",
            container_properties=batch.CfnJobDefinition.ContainerPropertiesProperty(
                image="python:3.9",
                vcpus=2,
                memory=4096,
                job_role_arn=self._create_batch_execution_role().role_arn,
                environment=[
                    batch.CfnJobDefinition.EnvironmentProperty(
                        name="OUTPUT_BUCKET",
                        value=self.output_bucket.bucket_name
                    ),
                    batch.CfnJobDefinition.EnvironmentProperty(
                        name="OUTPUT_FORMAT",
                        value=self.props.output_format
                    )
                ]
            ),
            retry_strategy=batch.CfnJobDefinition.RetryStrategyProperty(
                attempts=self.props.max_retry_attempts
            ),
            timeout=batch.CfnJobDefinition.TimeoutProperty(
                attempt_duration_seconds=3600  # 1 hour
            )
        )
    
    def _create_batch_execution_role(self) -> iam.Role:
        """Create IAM role for Batch job execution."""
        return self.create_service_role(
            "BatchExecutionRole",
            "ecs-tasks.amazonaws.com",
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:PutObject",
                                "s3:PutObjectAcl",
                                "s3:GetObject"
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
    
    def _create_lambda_functions(self) -> None:
        """Create Lambda functions for batch processing."""
        
        # Create IAM role for Lambda functions
        self.lambda_role = self.create_service_role(
            "BatchProcessorLambda",
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
                                "s3:PutObject",
                                "s3:PutObjectAcl",
                                "s3:GetObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                self.output_bucket.bucket_arn,
                                f"{self.output_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                ),
                "BatchAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "batch:SubmitJob",
                                "batch:DescribeJobs"
                            ],
                            resources=["*"]
                        )
                    ]
                ) if self.props.enable_aws_batch else None,
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
        
        # Batch coordinator Lambda
        self.batch_coordinator = lambda_.Function(
            self,
            "BatchCoordinator",
            function_name=self.get_resource_name("batch-coordinator"),
            runtime=self.props.lambda_runtime,
            handler="batch_coordinator.handler",
            code=lambda_.Code.from_asset("src/lambda/batch_ingestion"),
            role=self.lambda_role,
            memory_size=1024,
            timeout=Duration.minutes(15),
            environment={
                "OUTPUT_BUCKET": self.output_bucket.bucket_name,
                "DATA_SOURCES": json.dumps(self.props.data_sources),
                "SOURCE_SYSTEMS": json.dumps(self.props.source_systems or []),
                "CHUNK_SIZE": str(self.props.chunk_size),
                "MAX_PARALLEL_CHUNKS": str(self.props.max_parallel_chunks),
                "ENABLE_AWS_BATCH": str(self.props.enable_aws_batch),
                "BATCH_JOB_QUEUE": self.batch_job_queue.ref if self.props.enable_aws_batch and hasattr(self, 'batch_job_queue') else "",
                "BATCH_JOB_DEFINITION": self.batch_job_definition.ref if self.props.enable_aws_batch and hasattr(self, 'batch_job_definition') else "",
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED
        )
        
        # Batch processor Lambda (for Lambda-based processing)
        if not self.props.enable_aws_batch:
            self.batch_processor = lambda_.Function(
                self,
                "BatchProcessor",
                function_name=self.get_resource_name("batch-processor"),
                runtime=self.props.lambda_runtime,
                handler="batch_processor.handler",
                code=lambda_.Code.from_asset("src/lambda/batch_ingestion"),
                role=self.lambda_role,
                memory_size=self.props.lambda_memory_size,
                timeout=Duration.minutes(self.props.lambda_timeout_minutes),
                environment={
                    "OUTPUT_BUCKET": self.output_bucket.bucket_name,
                    "OUTPUT_FORMAT": self.props.output_format,
                    "ENABLE_PARTITIONING": str(self.props.enable_data_partitioning),
                    "PARTITION_KEYS": json.dumps(self.props.partition_keys),
                    "ENABLE_VALIDATION": str(self.props.enable_data_validation),
                    "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
                },
                tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED,
                reserved_concurrent_executions=self.props.max_parallel_chunks
            )
    
    def _create_step_functions(self) -> None:
        """Create Step Functions workflow for batch processing orchestration."""
        
        # Define Step Functions tasks
        coordinate_task = sfn_tasks.LambdaInvoke(
            self,
            "CoordinateBatchTask",
            lambda_function=self.batch_coordinator,
            output_path="$.Payload"
        )
        
        if self.props.enable_aws_batch and hasattr(self, 'batch_job_definition'):
            # AWS Batch processing
            process_batch_task = sfn_tasks.BatchSubmitJob(
                self,
                "ProcessBatchTask",
                job_definition_arn=self.batch_job_definition.ref,
                job_name="batch-processing-job",
                job_queue_arn=self.batch_job_queue.ref
            )
        else:
            # Lambda processing with parallel execution
            process_batch_task = sfn.Map(
                self,
                "ProcessBatchMap",
                items_path="$.chunks",
                max_concurrency=self.props.max_parallel_chunks
            ).iterator(
                sfn_tasks.LambdaInvoke(
                    self,
                    "ProcessChunkTask",
                    lambda_function=self.batch_processor,
                    output_path="$.Payload"
                )
            )
        
        # Success and failure states
        success_state = sfn.Succeed(self, "BatchProcessingSucceeded")
        failure_state = sfn.Fail(self, "BatchProcessingFailed")
        
        # Define the workflow with retry logic
        definition = coordinate_task.next(
            process_batch_task.add_retry(
                errors=["States.ALL"],
                interval_duration=Duration.seconds(30),
                max_attempts=self.props.max_retry_attempts,
                backoff_rate=self.props.retry_backoff_multiplier if self.props.enable_exponential_backoff else 1.0
            ).next(success_state)
        )
        
        # Add error handling
        definition.add_catch(
            failure_state,
            errors=["States.ALL"],
            result_path="$.error"
        )
        
        # Create Step Functions state machine
        self.batch_workflow = sfn.StateMachine(
            self,
            "BatchProcessingWorkflow",
            state_machine_name=self.get_resource_name("batch-workflow"),
            definition=definition,
            timeout=Duration.hours(4),  # 4 hour timeout for batch processing
            tracing_enabled=self.props.enable_detailed_monitoring
        )
    
    def _create_scheduling(self) -> None:
        """Create EventBridge scheduling for batch processing."""
        
        if not self.props.enable_scheduling:
            return
        
        # Create EventBridge rule for scheduled execution
        self.batch_schedule_rule = events.Rule(
            self,
            "BatchScheduleRule",
            schedule=events.Schedule.expression(self.props.schedule_expression),
            description=f"Scheduled batch processing for {self.project_name}",
            enabled=True
        )
        
        # Target Step Functions workflow
        self.batch_schedule_rule.add_target(
            targets.SfnStateMachine(
                self.batch_workflow,
                input=events.RuleTargetInput.from_object({
                    "source": "scheduled",
                    "timestamp": events.RuleTargetInput.from_text("$.time").value
                })
            )
        )
    
    def _create_error_handling(self) -> None:
        """Create error handling resources."""
        
        if self.props.enable_dlq:
            # Create dead letter queue
            self.dlq = sqs.Queue(
                self,
                "BatchDLQ",
                queue_name=self.get_resource_name("batch-dlq"),
                encryption=sqs.QueueEncryption.KMS,
                encryption_master_key=self.encryption_key,
                retention_period=Duration.days(14),
                visibility_timeout=Duration.minutes(self.props.lambda_timeout_minutes * 6)
            )
            
            # Add DLQ to Lambda functions
            self.batch_coordinator.add_dead_letter_queue(
                dead_letter_queue=self.dlq
            )
            
            if hasattr(self, 'batch_processor'):
                self.batch_processor.add_dead_letter_queue(
                    dead_letter_queue=self.dlq
                )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.batch_jobs_completed_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/BatchIngestion",
            metric_name="BatchJobsCompleted",
            dimensions_map={
                "Environment": self.environment,
                "Construct": self.construct_name
            }
        )
        
        self.batch_processing_duration_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/BatchIngestion",
            metric_name="BatchProcessingDuration",
            dimensions_map={
                "Environment": self.environment,
                "Construct": self.construct_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "BatchProcessingFailures",
            cloudwatch.Metric(
                namespace="AWS/States",
                metric_name="ExecutionsFailed",
                dimensions_map={
                    "StateMachineArn": self.batch_workflow.state_machine_arn
                }
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            description="Batch processing workflow failures"
        )
        
        self.create_alarm(
            "LongBatchProcessingDuration",
            cloudwatch.Metric(
                namespace="AWS/States",
                metric_name="ExecutionTime",
                dimensions_map={
                    "StateMachineArn": self.batch_workflow.state_machine_arn
                }
            ),
            threshold=Duration.hours(2).to_milliseconds(),
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="Long batch processing duration"
        )
        
        if self.props.enable_aws_batch and hasattr(self, 'batch_job_queue'):
            self.create_alarm(
                "BatchJobFailures",
                cloudwatch.Metric(
                    namespace="AWS/Batch",
                    metric_name="FailedJobs",
                    dimensions_map={
                        "JobQueue": self.batch_job_queue.ref
                    }
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="AWS Batch job failures"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "OutputBucketName",
            self.output_bucket.bucket_name,
            "Name of the batch output S3 bucket"
        )
        
        self.add_output(
            "BatchWorkflowArn",
            self.batch_workflow.state_machine_arn,
            "ARN of the batch processing Step Functions workflow"
        )
        
        self.add_output(
            "BatchCoordinatorFunctionName",
            self.batch_coordinator.function_name,
            "Name of the batch coordinator Lambda function"
        )
        
        if self.props.enable_aws_batch and hasattr(self, 'batch_job_queue'):
            self.add_output(
                "BatchJobQueueArn",
                self.batch_job_queue.ref,
                "ARN of the AWS Batch job queue"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.batch_jobs_completed_metric,
            self.batch_processing_duration_metric,
            cloudwatch.Metric(
                namespace="AWS/States",
                metric_name="ExecutionsStarted",
                dimensions_map={
                    "StateMachineArn": self.batch_workflow.state_machine_arn
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions_map={"FunctionName": self.batch_coordinator.function_name}
            )
        ]
        
        if self.props.enable_aws_batch and hasattr(self, 'batch_job_queue'):
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/Batch",
                    metric_name="SubmittedJobs",
                    dimensions_map={
                        "JobQueue": self.batch_job_queue.ref
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/Batch",
                    metric_name="RunnableJobs",
                    dimensions_map={
                        "JobQueue": self.batch_job_queue.ref
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
