"""
Real-time Data Ingestion Construct for DevSecOps Platform.

This construct implements Kinesis Data Firehose with transformation,
format conversion, and real-time analytics capabilities.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_kinesisfirehose as firehose,
    aws_kinesis as kinesis,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_iam as iam,
    aws_glue as glue,
    aws_cloudwatch as cloudwatch,
    aws_kinesisanalytics as analytics,
    aws_opensearchservice as opensearch,
    aws_logs as logs,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class RealtimeIngestionProps(ConstructProps):
    """Properties for Real-time Ingestion Construct."""
    
    # Kinesis Data Firehose Configuration
    delivery_stream_name: Optional[str] = None
    buffer_size_mb: int = 5
    buffer_interval_seconds: int = 300
    compression_format: str = "GZIP"  # GZIP, SNAPPY, ZIP, Hadoop_SNAPPY
    
    # Data Transformation
    enable_data_transformation: bool = True
    transformation_lambda_memory: int = 1024
    transformation_lambda_timeout: int = 3
    
    # Format Conversion
    enable_format_conversion: bool = True
    output_format: str = "PARQUET"  # PARQUET, ORC, JSON
    enable_schema_evolution: bool = True
    
    # Destinations
    s3_destination_bucket: Optional[str] = None
    enable_opensearch_destination: bool = False
    opensearch_domain_name: Optional[str] = None
    enable_redshift_destination: bool = False
    
    # Error Handling
    error_output_prefix: str = "errors/"
    enable_error_processing: bool = True
    
    # Real-time Analytics
    enable_kinesis_analytics: bool = False
    analytics_application_name: Optional[str] = None
    sql_queries: List[str] = None
    
    # Data Catalog Integration
    enable_glue_catalog: bool = True
    glue_database_name: Optional[str] = None
    glue_table_name: Optional[str] = None
    
    # Monitoring
    enable_detailed_monitoring: bool = True
    enable_cloudwatch_logs: bool = True
    
    # Performance
    enable_dynamic_partitioning: bool = True
    partition_keys: List[str] = None
    enable_multi_record_deaggregation: bool = True


class RealtimeIngestionConstruct(BaseConstruct):
    """
    Real-time Data Ingestion Construct.
    
    Implements a comprehensive real-time ingestion pipeline with:
    - Kinesis Data Firehose for reliable delivery
    - Lambda-based data transformation
    - Format conversion (JSON to Parquet/ORC)
    - Multiple destination support (S3, OpenSearch, Redshift)
    - Real-time analytics with Kinesis Analytics
    - Glue Data Catalog integration
    - Dynamic partitioning and schema evolution
    - Comprehensive monitoring and error handling
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: RealtimeIngestionProps,
        **kwargs
    ) -> None:
        """
        Initialize Real-time Ingestion Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.partition_keys is None:
            self.props.partition_keys = ["year", "month", "day", "hour"]
        
        # Create resources
        self._create_s3_destinations()
        self._create_glue_catalog()
        self._create_transformation_lambda()
        self._create_opensearch_destination()
        self._create_firehose_delivery_stream()
        self._create_kinesis_analytics()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_s3_destinations(self) -> None:
        """Create S3 destinations for Firehose delivery."""
        
        # Main S3 destination
        self.s3_destination = s3.Bucket(
            self,
            "RealtimeDestination",
            bucket_name=self.props.s3_destination_bucket or self.get_resource_name("realtime-data"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy(),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="RealtimeDataLifecycle",
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
    
    def _create_glue_catalog(self) -> None:
        """Create Glue Data Catalog resources."""
        
        if not self.props.enable_glue_catalog:
            return
        
        # Create Glue database
        self.glue_database = glue.CfnDatabase(
            self,
            "RealtimeGlueDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=self.props.glue_database_name or self.get_resource_name("realtime-db"),
                description=f"Real-time data catalog for {self.project_name}"
            )
        )
        
        # Create Glue table for schema definition
        if self.props.enable_format_conversion and self.props.output_format in ["PARQUET", "ORC"]:
            self.glue_table = glue.CfnTable(
                self,
                "RealtimeGlueTable",
                catalog_id=self.account,
                database_name=self.glue_database.ref,
                table_input=glue.CfnTable.TableInputProperty(
                    name=self.props.glue_table_name or self.get_resource_name("realtime-table"),
                    description="Real-time data table",
                    table_type="EXTERNAL_TABLE",
                    storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                        columns=[
                            glue.CfnTable.ColumnProperty(
                                name="timestamp",
                                type="timestamp"
                            ),
                            glue.CfnTable.ColumnProperty(
                                name="data",
                                type="string"
                            )
                        ],
                        location=f"s3://{self.s3_destination.bucket_name}/",
                        input_format="org.apache.hadoop.mapred.TextInputFormat",
                        output_format="org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                        serde_info=glue.CfnTable.SerdeInfoProperty(
                            serialization_library="org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
                        )
                    ),
                    partition_keys=[
                        glue.CfnTable.ColumnProperty(
                            name=key,
                            type="string"
                        ) for key in self.props.partition_keys
                    ]
                )
            )
    
    def _create_transformation_lambda(self) -> None:
        """Create Lambda function for data transformation."""
        
        if not self.props.enable_data_transformation:
            return
        
        # Create IAM role for transformation Lambda
        self.transformation_lambda_role = self.create_service_role(
            "TransformationLambda",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaBasicExecutionRole"
            ],
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
        
        # Create transformation Lambda
        self.transformation_lambda = lambda_.Function(
            self,
            "TransformationLambda",
            function_name=self.get_resource_name("realtime-transform"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="realtime_transformer.handler",
            code=lambda_.Code.from_asset("src/lambda/realtime_ingestion"),
            role=self.transformation_lambda_role,
            memory_size=self.props.transformation_lambda_memory,
            timeout=Duration.minutes(self.props.transformation_lambda_timeout),
            environment={
                "OUTPUT_FORMAT": self.props.output_format,
                "ENABLE_SCHEMA_EVOLUTION": str(self.props.enable_schema_evolution),
                "PARTITION_KEYS": json.dumps(self.props.partition_keys),
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_detailed_monitoring else lambda_.Tracing.DISABLED
        )
    
    def _create_opensearch_destination(self) -> None:
        """Create OpenSearch destination if enabled."""
        
        if not self.props.enable_opensearch_destination:
            return
        
        # Create OpenSearch domain
        self.opensearch_domain = opensearch.Domain(
            self,
            "RealtimeOpenSearch",
            domain_name=self.props.opensearch_domain_name or self.get_resource_name("realtime-search"),
            version=opensearch.EngineVersion.OPENSEARCH_1_3,
            capacity=opensearch.CapacityConfig(
                master_nodes=3 if self.environment == "prod" else 1,
                master_node_instance_type="m6g.medium.search",
                data_nodes=3 if self.environment == "prod" else 1,
                data_node_instance_type="m6g.large.search"
            ),
            ebs=opensearch.EbsOptions(
                volume_size=20,
                volume_type=ec2.EbsDeviceVolumeType.GP3
            ),
            zone_awareness=opensearch.ZoneAwarenessConfig(
                enabled=self.environment == "prod",
                availability_zone_count=3 if self.environment == "prod" else 1
            ),
            encryption_at_rest=opensearch.EncryptionAtRestOptions(
                enabled=True,
                kms_key=self.encryption_key
            ),
            node_to_node_encryption=True,
            enforce_https=True,
            removal_policy=self._get_removal_policy()
        )
    
    def _create_firehose_delivery_stream(self) -> None:
        """Create Kinesis Data Firehose delivery stream."""
        
        # Create IAM role for Firehose
        self.firehose_role = self.create_service_role(
            "FirehoseDeliveryRole",
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
                                self.s3_destination.bucket_arn,
                                f"{self.s3_destination.bucket_arn}/*"
                            ]
                        )
                    ]
                ),
                "LambdaAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "lambda:InvokeFunction"
                            ],
                            resources=[
                                self.transformation_lambda.function_arn
                            ] if self.props.enable_data_transformation and hasattr(self, 'transformation_lambda') else []
                        )
                    ]
                ) if self.props.enable_data_transformation else None,
                "GlueAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "glue:GetTable",
                                "glue:GetTableVersion",
                                "glue:GetTableVersions"
                            ],
                            resources=[
                                f"arn:aws:glue:{self.region}:{self.account}:catalog",
                                f"arn:aws:glue:{self.region}:{self.account}:database/{self.glue_database.ref}",
                                f"arn:aws:glue:{self.region}:{self.account}:table/{self.glue_database.ref}/*"
                            ] if self.props.enable_glue_catalog and hasattr(self, 'glue_database') else []
                        )
                    ]
                ) if self.props.enable_glue_catalog else None,
                "OpenSearchAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "es:DescribeElasticsearchDomain",
                                "es:DescribeElasticsearchDomains",
                                "es:DescribeElasticsearchDomainConfig",
                                "es:ESHttpPost",
                                "es:ESHttpPut"
                            ],
                            resources=[
                                self.opensearch_domain.domain_arn,
                                f"{self.opensearch_domain.domain_arn}/*"
                            ] if self.props.enable_opensearch_destination and hasattr(self, 'opensearch_domain') else []
                        )
                    ]
                ) if self.props.enable_opensearch_destination else None,
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
        
        # Configure S3 destination
        s3_destination_config = firehose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
            bucket_arn=self.s3_destination.bucket_arn,
            role_arn=self.firehose_role.role_arn,
            prefix="data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/",
            error_output_prefix=self.props.error_output_prefix,
            buffering_hints=firehose.CfnDeliveryStream.BufferingHintsProperty(
                size_in_m_bs=self.props.buffer_size_mb,
                interval_in_seconds=self.props.buffer_interval_seconds
            ),
            compression_format=self.props.compression_format,
            encryption_configuration=firehose.CfnDeliveryStream.EncryptionConfigurationProperty(
                kms_encryption_config=firehose.CfnDeliveryStream.KMSEncryptionConfigProperty(
                    awskms_key_arn=self.encryption_key.key_arn
                )
            ),
            cloud_watch_logging_options=firehose.CfnDeliveryStream.CloudWatchLoggingOptionsProperty(
                enabled=self.props.enable_cloudwatch_logs,
                log_group_name=f"/aws/kinesisfirehose/{self.get_resource_name('firehose')}"
            ) if self.props.enable_cloudwatch_logs else None,
            processing_configuration=firehose.CfnDeliveryStream.ProcessingConfigurationProperty(
                enabled=self.props.enable_data_transformation,
                processors=[
                    firehose.CfnDeliveryStream.ProcessorProperty(
                        type="Lambda",
                        parameters=[
                            firehose.CfnDeliveryStream.ProcessorParameterProperty(
                                parameter_name="LambdaArn",
                                parameter_value=self.transformation_lambda.function_arn
                            )
                        ]
                    )
                ] if self.props.enable_data_transformation and hasattr(self, 'transformation_lambda') else []
            ) if self.props.enable_data_transformation else None,
            data_format_conversion_configuration=firehose.CfnDeliveryStream.DataFormatConversionConfigurationProperty(
                enabled=self.props.enable_format_conversion,
                output_format_configuration=firehose.CfnDeliveryStream.OutputFormatConfigurationProperty(
                    serializer=firehose.CfnDeliveryStream.SerializerProperty(
                        parquet_ser_de=firehose.CfnDeliveryStream.ParquetSerDeProperty()
                        if self.props.output_format == "PARQUET" else None,
                        orc_ser_de=firehose.CfnDeliveryStream.OrcSerDeProperty()
                        if self.props.output_format == "ORC" else None
                    )
                ),
                schema_configuration=firehose.CfnDeliveryStream.SchemaConfigurationProperty(
                    catalog_id=self.account,
                    database_name=self.glue_database.ref,
                    table_name=self.glue_table.ref,
                    role_arn=self.firehose_role.role_arn,
                    version_id="LATEST"
                ) if self.props.enable_glue_catalog and hasattr(self, 'glue_table') else None
            ) if self.props.enable_format_conversion else None,
            dynamic_partitioning=firehose.CfnDeliveryStream.DynamicPartitioningProperty(
                enabled=self.props.enable_dynamic_partitioning
            ) if self.props.enable_dynamic_partitioning else None
        )
        
        # Create Firehose delivery stream
        self.delivery_stream = firehose.CfnDeliveryStream(
            self,
            "RealtimeDeliveryStream",
            delivery_stream_name=self.props.delivery_stream_name or self.get_resource_name("realtime-firehose"),
            delivery_stream_type="DirectPut",
            extended_s3_destination_configuration=s3_destination_config
        )
    
    def _create_kinesis_analytics(self) -> None:
        """Create Kinesis Analytics application for real-time processing."""
        
        if not self.props.enable_kinesis_analytics:
            return
        
        # Create CloudWatch log group for analytics
        analytics_log_group = logs.LogGroup(
            self,
            "AnalyticsLogGroup",
            log_group_name=f"/aws/kinesisanalytics/{self.get_resource_name('analytics')}",
            retention=logs.RetentionDays.ONE_MONTH,
            encryption_key=self.encryption_key,
            removal_policy=self._get_removal_policy()
        )
        
        # Create IAM role for Kinesis Analytics
        analytics_role = self.create_service_role(
            "KinesisAnalyticsRole",
            "kinesisanalytics.amazonaws.com",
            inline_policies={
                "FirehoseAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "firehose:DescribeDeliveryStream",
                                "firehose:PutRecord",
                                "firehose:PutRecordBatch"
                            ],
                            resources=[
                                f"arn:aws:firehose:{self.region}:{self.account}:deliverystream/{self.delivery_stream.ref}"
                            ]
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
                            resources=[
                                analytics_log_group.log_group_arn
                            ]
                        )
                    ]
                )
            }
        )
        
        # Create Kinesis Analytics application
        self.analytics_application = analytics.CfnApplication(
            self,
            "RealtimeAnalyticsApp",
            application_name=self.props.analytics_application_name or self.get_resource_name("analytics"),
            application_description=f"Real-time analytics for {self.project_name}",
            application_code=self._get_analytics_sql_code(),
            inputs=[
                analytics.CfnApplication.InputProperty(
                    name_prefix="SOURCE_SQL_STREAM",
                    kinesis_firehose_input=analytics.CfnApplication.KinesisFirehoseInputProperty(
                        resource_arn=f"arn:aws:firehose:{self.region}:{self.account}:deliverystream/{self.delivery_stream.ref}",
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
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.records_delivered_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/RealtimeIngestion",
            metric_name="RecordsDelivered",
            dimensions_map={
                "Environment": self.environment,
                "DeliveryStream": self.delivery_stream.ref
            }
        )
        
        # Create alarms
        self.create_alarm(
            "FirehoseDeliveryFailures",
            cloudwatch.Metric(
                namespace="AWS/KinesisFirehose",
                metric_name="DeliveryToS3.Records",
                dimensions_map={
                    "DeliveryStreamName": self.delivery_stream.ref
                }
            ),
            threshold=100,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            description="Low Firehose delivery rate"
        )
        
        if self.props.enable_data_transformation and hasattr(self, 'transformation_lambda'):
            self.create_alarm(
                "TransformationErrors",
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={
                        "FunctionName": self.transformation_lambda.function_name
                    }
                ),
                threshold=5,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High transformation error rate"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "DeliveryStreamName",
            self.delivery_stream.ref,
            "Name of the Kinesis Data Firehose delivery stream"
        )
        
        self.add_output(
            "DeliveryStreamArn",
            f"arn:aws:firehose:{self.region}:{self.account}:deliverystream/{self.delivery_stream.ref}",
            "ARN of the Kinesis Data Firehose delivery stream"
        )
        
        self.add_output(
            "S3DestinationBucket",
            self.s3_destination.bucket_name,
            "Name of the S3 destination bucket"
        )
        
        if self.props.enable_opensearch_destination and hasattr(self, 'opensearch_domain'):
            self.add_output(
                "OpenSearchDomainEndpoint",
                self.opensearch_domain.domain_endpoint,
                "Endpoint of the OpenSearch domain"
            )
        
        if self.props.enable_kinesis_analytics and hasattr(self, 'analytics_application'):
            self.add_output(
                "AnalyticsApplicationName",
                self.analytics_application.ref,
                "Name of the Kinesis Analytics application"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.records_delivered_metric,
            cloudwatch.Metric(
                namespace="AWS/KinesisFirehose",
                metric_name="DeliveryToS3.Success",
                dimensions_map={
                    "DeliveryStreamName": self.delivery_stream.ref
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/KinesisFirehose",
                metric_name="DeliveryToS3.DataFreshness",
                dimensions_map={
                    "DeliveryStreamName": self.delivery_stream.ref
                }
            )
        ]
        
        if self.props.enable_data_transformation and hasattr(self, 'transformation_lambda'):
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    dimensions_map={
                        "FunctionName": self.transformation_lambda.function_name
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    dimensions_map={
                        "FunctionName": self.transformation_lambda.function_name
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
