"""
Database Data Ingestion Construct for DevSecOps Platform.

This construct implements RDS/DynamoDB → Lambda → S3 pattern with CDC support,
data transformation, and comprehensive error handling.
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
    aws_rds as rds,
    aws_dynamodb as dynamodb,
    aws_dms as dms,
    aws_events as events,
    aws_events_targets as targets,
    aws_cloudwatch as cloudwatch,
    aws_sqs as sqs,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class DatabaseIngestionProps(ConstructProps):
    """Properties for Database Ingestion Construct."""
    
    # Database Configuration
    database_type: str = "rds"  # rds, dynamodb, documentdb
    database_engine: str = "mysql"  # mysql, postgresql, oracle, sqlserver
    enable_cdc: bool = True
    cdc_format: str = "json"  # json, avro, parquet
    
    # Source Database (for existing databases)
    source_database_arn: Optional[str] = None
    source_database_secret_arn: Optional[str] = None
    source_table_names: List[str] = None
    
    # DMS Configuration (for CDC)
    enable_dms: bool = True
    dms_instance_class: str = "dms.t3.micro"
    enable_full_load: bool = True
    enable_ongoing_replication: bool = True
    
    # Lambda Configuration
    lambda_memory_size: int = 1024
    lambda_timeout_minutes: int = 15
    lambda_runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9
    
    # S3 Configuration
    output_bucket_name: Optional[str] = None
    enable_data_partitioning: bool = True
    partition_keys: List[str] = None
    compression_type: str = "gzip"
    
    # Data Transformation
    enable_data_transformation: bool = True
    transformation_rules: Dict[str, Any] = None
    enable_schema_validation: bool = True
    
    # Error Handling
    enable_dlq: bool = True
    max_retry_attempts: int = 3
    
    # Monitoring
    enable_detailed_monitoring: bool = True


class DatabaseIngestionConstruct(BaseConstruct):
    """
    Database Data Ingestion Construct.
    
    Implements a comprehensive database ingestion pipeline with:
    - RDS/DynamoDB/DocumentDB source support
    - DMS for Change Data Capture (CDC)
    - Lambda for data transformation and validation
    - S3 for data storage with partitioning
    - Comprehensive error handling and monitoring
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: DatabaseIngestionProps,
        **kwargs
    ) -> None:
        """
        Initialize Database Ingestion Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Create resources
        self._create_s3_bucket()
        self._create_lambda_function()
        self._create_dms_resources()
        self._create_error_handling()
        self._setup_event_processing()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_s3_bucket(self) -> None:
        """Create S3 bucket for database data storage."""
        
        self.output_bucket = s3.Bucket(
            self,
            "DatabaseOutputBucket",
            bucket_name=self.props.output_bucket_name or self.get_resource_name("db-data"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy(),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DatabaseDataLifecycle",
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
        """Create Lambda function for database data processing."""
        
        # Create IAM role for Lambda
        self.lambda_role = self.create_service_role(
            "DatabaseProcessorLambda",
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
                                "s3:GetObject"
                            ],
                            resources=[
                                f"{self.output_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                ),
                "SecretsManagerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "secretsmanager:GetSecretValue"
                            ],
                            resources=[
                                self.props.source_database_secret_arn
                            ] if self.props.source_database_secret_arn else ["*"]
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
        self.database_processor = lambda_.Function(
            self,
            "DatabaseProcessor",
            function_name=self.get_resource_name("db-processor"),
            runtime=self.props.lambda_runtime,
            handler="database_processor.handler",
            code=lambda_.Code.from_asset("src/lambda/database_ingestion"),
            role=self.lambda_role,
            memory_size=self.props.lambda_memory_size,
            timeout=Duration.minutes(self.props.lambda_timeout_minutes),
            environment={
                "OUTPUT_BUCKET": self.output_bucket.bucket_name,
                "DATABASE_TYPE": self.props.database_type,
                "DATABASE_ENGINE": self.props.database_engine,
                "CDC_FORMAT": self.props.cdc_format,
                "ENABLE_TRANSFORMATION": str(self.props.enable_data_transformation),
                "TRANSFORMATION_RULES": json.dumps(self.props.transformation_rules or {}),
                "ENABLE_SCHEMA_VALIDATION": str(self.props.enable_schema_validation),
                "PARTITION_KEYS": json.dumps(self.props.partition_keys or ["year", "month", "day"]),
                "COMPRESSION_TYPE": self.props.compression_type,
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED
        )
    
    def _create_dms_resources(self) -> None:
        """Create DMS resources for Change Data Capture."""
        
        if not self.props.enable_dms:
            return
        
        # Create DMS subnet group
        self.dms_subnet_group = dms.CfnReplicationSubnetGroup(
            self,
            "DMSSubnetGroup",
            replication_subnet_group_description="DMS subnet group for database ingestion",
            subnet_ids=[
                # These would come from VPC construct
                # For now, using placeholder
                "subnet-12345678",
                "subnet-87654321"
            ],
            replication_subnet_group_identifier=self.get_resource_name("dms-subnet-group")
        )
        
        # Create DMS replication instance
        self.dms_replication_instance = dms.CfnReplicationInstance(
            self,
            "DMSReplicationInstance",
            replication_instance_class=self.props.dms_instance_class,
            replication_instance_identifier=self.get_resource_name("dms-instance"),
            allocated_storage=20,
            apply_immediately=True,
            auto_minor_version_upgrade=True,
            engine_version="3.4.7",
            multi_az=self.environment == "prod",
            publicly_accessible=False,
            replication_subnet_group_identifier=self.dms_subnet_group.ref,
            vpc_security_group_ids=[
                # This would come from security construct
                # For now, using placeholder
                "sg-12345678"
            ]
        )
        
        # Create source endpoint
        if self.props.source_database_arn:
            self.source_endpoint = dms.CfnEndpoint(
                self,
                "SourceEndpoint",
                endpoint_type="source",
                engine_name=self.props.database_engine,
                endpoint_identifier=self.get_resource_name("source-endpoint"),
                database_name="source_db",
                username="admin",
                password="{{resolve:secretsmanager:" + self.props.source_database_secret_arn + ":SecretString:password}}",
                server_name="{{resolve:secretsmanager:" + self.props.source_database_secret_arn + ":SecretString:host}}",
                port=3306 if self.props.database_engine == "mysql" else 5432,
                ssl_mode="require"
            )
        
        # Create target endpoint (S3)
        self.target_endpoint = dms.CfnEndpoint(
            self,
            "TargetEndpoint",
            endpoint_type="target",
            engine_name="s3",
            endpoint_identifier=self.get_resource_name("target-endpoint"),
            s3_settings=dms.CfnEndpoint.S3SettingsProperty(
                bucket_name=self.output_bucket.bucket_name,
                bucket_folder="cdc-data",
                compression_type=self.props.compression_type.upper(),
                data_format=self.props.cdc_format,
                date_partition_enabled=self.props.enable_data_partitioning,
                date_partition_sequence="YYYYMMDD",
                include_op_for_full_load=True,
                parquet_timestamp_in_millisecond=True if self.props.cdc_format == "parquet" else False,
                service_access_role_arn=self._create_dms_s3_role().role_arn
            )
        )
        
        # Create replication task
        if self.props.source_table_names:
            table_mappings = {
                "rules": [
                    {
                        "rule-type": "selection",
                        "rule-id": "1",
                        "rule-name": "1",
                        "object-locator": {
                            "schema-name": "%",
                            "table-name": table_name
                        },
                        "rule-action": "include"
                    }
                    for table_name in self.props.source_table_names
                ]
            }
            
            self.replication_task = dms.CfnReplicationTask(
                self,
                "ReplicationTask",
                migration_type="full-load-and-cdc" if self.props.enable_full_load and self.props.enable_ongoing_replication else "cdc",
                replication_instance_arn=self.dms_replication_instance.ref,
                source_endpoint_arn=self.source_endpoint.ref if hasattr(self, 'source_endpoint') else "",
                target_endpoint_arn=self.target_endpoint.ref,
                table_mappings=json.dumps(table_mappings),
                replication_task_identifier=self.get_resource_name("replication-task"),
                replication_task_settings=json.dumps({
                    "TargetMetadata": {
                        "TargetSchema": "",
                        "SupportLobs": True,
                        "FullLobMode": False,
                        "LobChunkSize": 0,
                        "LimitedSizeLobMode": True,
                        "LobMaxSize": 32,
                        "InlineLobMaxSize": 0,
                        "LoadMaxFileSize": 0,
                        "ParallelLoadThreads": 0,
                        "ParallelLoadBufferSize": 0,
                        "BatchApplyEnabled": False,
                        "TaskRecoveryTableEnabled": False,
                        "ParallelApplyThreads": 0,
                        "ParallelApplyBufferSize": 0,
                        "ParallelApplyQueuesPerThread": 0
                    },
                    "FullLoadSettings": {
                        "TargetTablePrepMode": "DROP_AND_CREATE",
                        "CreatePkAfterFullLoad": False,
                        "StopTaskCachedChangesApplied": False,
                        "StopTaskCachedChangesNotApplied": False,
                        "MaxFullLoadSubTasks": 8,
                        "TransactionConsistencyTimeout": 600,
                        "CommitRate": 10000
                    },
                    "Logging": {
                        "EnableLogging": True,
                        "LogComponents": [
                            {
                                "Id": "SOURCE_UNLOAD",
                                "Severity": "LOGGER_SEVERITY_DEFAULT"
                            },
                            {
                                "Id": "TARGET_LOAD",
                                "Severity": "LOGGER_SEVERITY_DEFAULT"
                            }
                        ]
                    }
                })
            )
    
    def _create_dms_s3_role(self) -> iam.Role:
        """Create IAM role for DMS to access S3."""
        return self.create_service_role(
            "DMSS3Access",
            "dms.amazonaws.com",
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:PutObject",
                                "s3:DeleteObject",
                                "s3:PutObjectTagging"
                            ],
                            resources=[
                                f"{self.output_bucket.bucket_arn}/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:ListBucket"
                            ],
                            resources=[
                                self.output_bucket.bucket_arn
                            ]
                        )
                    ]
                )
            }
        )
    
    def _create_error_handling(self) -> None:
        """Create error handling resources."""
        
        if self.props.enable_dlq:
            # Create dead letter queue
            self.dlq = sqs.Queue(
                self,
                "DatabaseDLQ",
                queue_name=self.get_resource_name("db-dlq"),
                encryption=sqs.QueueEncryption.KMS,
                encryption_master_key=self.encryption_key,
                retention_period=Duration.days(14),
                visibility_timeout=Duration.minutes(self.props.lambda_timeout_minutes * 6)
            )
            
            # Add DLQ to Lambda function
            self.database_processor.add_dead_letter_queue(
                dead_letter_queue=self.dlq
            )
    
    def _setup_event_processing(self) -> None:
        """Set up event processing for database changes."""
        
        # Create EventBridge rule for DMS task state changes
        if self.props.enable_dms and hasattr(self, 'replication_task'):
            events.Rule(
                self,
                "DMSTaskStateChangeRule",
                event_pattern=events.EventPattern(
                    source=["aws.dms"],
                    detail_type=["DMS Replication Task State Change"],
                    detail={
                        "sourceId": [self.replication_task.ref]
                    }
                ),
                targets=[
                    targets.LambdaFunction(self.database_processor)
                ]
            )
        
        # Create EventBridge rule for S3 object creation (from DMS)
        events.Rule(
            self,
            "S3ObjectCreatedRule",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {"name": [self.output_bucket.bucket_name]},
                    "object": {"key": [{"prefix": "cdc-data/"}]}
                }
            ),
            targets=[
                targets.LambdaFunction(self.database_processor)
            ]
        )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.records_processed_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/DatabaseIngestion",
            metric_name="RecordsProcessed",
            dimensions_map={
                "Environment": self.environment,
                "DatabaseType": self.props.database_type
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighDatabaseErrorRate",
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={"FunctionName": self.database_processor.function_name}
            ),
            threshold=5,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High error rate in database processing"
        )
        
        if self.props.enable_dms and hasattr(self, 'dms_replication_instance'):
            self.create_alarm(
                "DMSReplicationLag",
                cloudwatch.Metric(
                    namespace="AWS/DMS",
                    metric_name="CDCLatencySource",
                    dimensions_map={
                        "ReplicationInstanceIdentifier": self.dms_replication_instance.ref
                    }
                ),
                threshold=300,  # 5 minutes
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High DMS replication lag"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "OutputBucketName",
            self.output_bucket.bucket_name,
            "Name of the database output S3 bucket"
        )
        
        self.add_output(
            "DatabaseProcessorFunctionName",
            self.database_processor.function_name,
            "Name of the database processor Lambda function"
        )
        
        if self.props.enable_dms and hasattr(self, 'dms_replication_instance'):
            self.add_output(
                "DMSReplicationInstanceArn",
                self.dms_replication_instance.ref,
                "ARN of the DMS replication instance"
            )
        
        if hasattr(self, 'replication_task'):
            self.add_output(
                "DMSReplicationTaskArn",
                self.replication_task.ref,
                "ARN of the DMS replication task"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.records_processed_metric,
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions_map={"FunctionName": self.database_processor.function_name}
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Duration",
                dimensions_map={"FunctionName": self.database_processor.function_name}
            )
        ]
        
        if self.props.enable_dms and hasattr(self, 'dms_replication_instance'):
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/DMS",
                    metric_name="CDCLatencySource",
                    dimensions_map={
                        "ReplicationInstanceIdentifier": self.dms_replication_instance.ref
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/DMS",
                    metric_name="CDCLatencyTarget",
                    dimensions_map={
                        "ReplicationInstanceIdentifier": self.dms_replication_instance.ref
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
