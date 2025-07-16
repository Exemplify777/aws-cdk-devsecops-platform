"""
DynamoDB Construct for DevSecOps Platform.

This construct implements DynamoDB tables with enterprise-grade configurations,
backup strategies, monitoring, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_applicationautoscaling as autoscaling,
    aws_backup as backup,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_kinesis as kinesis,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class DynamoDbConstructProps(ConstructProps):
    """Properties for DynamoDB Construct."""
    
    # Table Configuration
    table_name: Optional[str] = None
    partition_key: str = "id"
    partition_key_type: str = "STRING"  # STRING, NUMBER, BINARY
    sort_key: Optional[str] = None
    sort_key_type: str = "STRING"
    
    # Billing Configuration
    billing_mode: str = "PAY_PER_REQUEST"  # PAY_PER_REQUEST, PROVISIONED
    read_capacity: int = 5
    write_capacity: int = 5
    
    # Auto Scaling Configuration
    enable_auto_scaling: bool = True
    min_read_capacity: int = 1
    max_read_capacity: int = 100
    min_write_capacity: int = 1
    max_write_capacity: int = 100
    target_utilization_percent: float = 70.0
    
    # Global Secondary Indexes
    global_secondary_indexes: List[Dict[str, Any]] = None
    
    # Local Secondary Indexes
    local_secondary_indexes: List[Dict[str, Any]] = None
    
    # Streams Configuration
    enable_streams: bool = False
    stream_view_type: str = "NEW_AND_OLD_IMAGES"  # KEYS_ONLY, NEW_IMAGE, OLD_IMAGE, NEW_AND_OLD_IMAGES
    
    # Backup Configuration
    enable_point_in_time_recovery: bool = True
    enable_backup_plan: bool = True
    backup_retention_days: int = 35
    
    # Encryption Configuration
    enable_encryption: bool = True
    encryption_type: str = "AWS_MANAGED"  # AWS_MANAGED, CUSTOMER_MANAGED
    
    # TTL Configuration
    enable_ttl: bool = False
    ttl_attribute_name: str = "ttl"
    
    # Monitoring Configuration
    enable_contributor_insights: bool = True
    enable_detailed_monitoring: bool = True
    
    # Data Import/Export
    enable_export_to_s3: bool = False
    export_bucket_name: Optional[str] = None
    
    # Multi-Region Configuration
    enable_global_tables: bool = False
    replica_regions: List[str] = None


class DynamoDbConstruct(BaseConstruct):
    """
    DynamoDB Construct.
    
    Implements a comprehensive DynamoDB table with:
    - Flexible billing modes and auto-scaling
    - Global and local secondary indexes
    - DynamoDB Streams integration
    - Point-in-time recovery and backup plans
    - Encryption at rest and in transit
    - TTL for automatic data expiration
    - Contributor Insights for monitoring
    - Global Tables for multi-region replication
    - Comprehensive monitoring and alerting
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: DynamoDbConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize DynamoDB Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.global_secondary_indexes is None:
            self.props.global_secondary_indexes = []
        if self.props.local_secondary_indexes is None:
            self.props.local_secondary_indexes = []
        if self.props.replica_regions is None:
            self.props.replica_regions = []
        
        # Create resources
        self._create_dynamodb_table()
        self._configure_auto_scaling()
        self._configure_backup()
        self._configure_streams()
        self._configure_global_tables()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_dynamodb_table(self) -> None:
        """Create DynamoDB table with configuration."""
        
        # Define partition key
        partition_key = dynamodb.Attribute(
            name=self.props.partition_key,
            type=getattr(dynamodb.AttributeType, self.props.partition_key_type)
        )
        
        # Define sort key if provided
        sort_key = None
        if self.props.sort_key:
            sort_key = dynamodb.Attribute(
                name=self.props.sort_key,
                type=getattr(dynamodb.AttributeType, self.props.sort_key_type)
            )
        
        # Configure billing mode
        billing_mode = getattr(dynamodb.BillingMode, self.props.billing_mode)
        
        # Configure encryption
        encryption = None
        if self.props.enable_encryption:
            if self.props.encryption_type == "CUSTOMER_MANAGED":
                encryption = dynamodb.TableEncryption.customer_managed(self.encryption_key)
            else:
                encryption = dynamodb.TableEncryption.aws_managed()
        
        # Create table
        self.table = dynamodb.Table(
            self,
            "DynamoDBTable",
            table_name=self.props.table_name or self.get_resource_name("table"),
            partition_key=partition_key,
            sort_key=sort_key,
            billing_mode=billing_mode,
            read_capacity=self.props.read_capacity if billing_mode == dynamodb.BillingMode.PROVISIONED else None,
            write_capacity=self.props.write_capacity if billing_mode == dynamodb.BillingMode.PROVISIONED else None,
            encryption=encryption,
            point_in_time_recovery=self.props.enable_point_in_time_recovery,
            stream=getattr(dynamodb.StreamViewType, self.props.stream_view_type) if self.props.enable_streams else None,
            time_to_live_attribute=self.props.ttl_attribute_name if self.props.enable_ttl else None,
            contributor_insights_enabled=self.props.enable_contributor_insights,
            removal_policy=self._get_removal_policy()
        )

        # Apply standardized tags
        table_tags = self.get_resource_tags(
            application="database",
            component="dynamodb-table",
            data_classification=getattr(self.props, 'data_classification', 'internal'),
            backup_schedule="daily" if self.props.enable_point_in_time_recovery else "none"
        )
        for key, value in table_tags.items():
            if value:  # Only apply non-None values
                self.table.node.add_metadata(f"tag:{key}", value)

        # Add Global Secondary Indexes
        for gsi in self.props.global_secondary_indexes:
            self.table.add_global_secondary_index(
                index_name=gsi["index_name"],
                partition_key=dynamodb.Attribute(
                    name=gsi["partition_key"],
                    type=getattr(dynamodb.AttributeType, gsi.get("partition_key_type", "STRING"))
                ),
                sort_key=dynamodb.Attribute(
                    name=gsi["sort_key"],
                    type=getattr(dynamodb.AttributeType, gsi.get("sort_key_type", "STRING"))
                ) if gsi.get("sort_key") else None,
                projection_type=getattr(dynamodb.ProjectionType, gsi.get("projection_type", "ALL")),
                non_key_attributes=gsi.get("non_key_attributes"),
                read_capacity=gsi.get("read_capacity", self.props.read_capacity) if billing_mode == dynamodb.BillingMode.PROVISIONED else None,
                write_capacity=gsi.get("write_capacity", self.props.write_capacity) if billing_mode == dynamodb.BillingMode.PROVISIONED else None
            )
        
        # Add Local Secondary Indexes
        for lsi in self.props.local_secondary_indexes:
            self.table.add_local_secondary_index(
                index_name=lsi["index_name"],
                sort_key=dynamodb.Attribute(
                    name=lsi["sort_key"],
                    type=getattr(dynamodb.AttributeType, lsi.get("sort_key_type", "STRING"))
                ),
                projection_type=getattr(dynamodb.ProjectionType, lsi.get("projection_type", "ALL")),
                non_key_attributes=lsi.get("non_key_attributes")
            )
    
    def _configure_auto_scaling(self) -> None:
        """Configure auto-scaling for the table."""
        
        if not self.props.enable_auto_scaling or self.props.billing_mode != "PROVISIONED":
            return
        
        # Configure read capacity auto-scaling
        read_scaling = self.table.auto_scale_read_capacity(
            min_capacity=self.props.min_read_capacity,
            max_capacity=self.props.max_read_capacity
        )
        
        read_scaling.scale_on_utilization(
            target_utilization_percent=self.props.target_utilization_percent
        )
        
        # Configure write capacity auto-scaling
        write_scaling = self.table.auto_scale_write_capacity(
            min_capacity=self.props.min_write_capacity,
            max_capacity=self.props.max_write_capacity
        )
        
        write_scaling.scale_on_utilization(
            target_utilization_percent=self.props.target_utilization_percent
        )
        
        # Configure auto-scaling for Global Secondary Indexes
        for gsi in self.props.global_secondary_indexes:
            if gsi.get("enable_auto_scaling", True):
                gsi_read_scaling = self.table.auto_scale_global_secondary_index_read_capacity(
                    index_name=gsi["index_name"],
                    min_capacity=gsi.get("min_read_capacity", self.props.min_read_capacity),
                    max_capacity=gsi.get("max_read_capacity", self.props.max_read_capacity)
                )
                
                gsi_read_scaling.scale_on_utilization(
                    target_utilization_percent=gsi.get("target_utilization_percent", self.props.target_utilization_percent)
                )
                
                gsi_write_scaling = self.table.auto_scale_global_secondary_index_write_capacity(
                    index_name=gsi["index_name"],
                    min_capacity=gsi.get("min_write_capacity", self.props.min_write_capacity),
                    max_capacity=gsi.get("max_write_capacity", self.props.max_write_capacity)
                )
                
                gsi_write_scaling.scale_on_utilization(
                    target_utilization_percent=gsi.get("target_utilization_percent", self.props.target_utilization_percent)
                )
    
    def _configure_backup(self) -> None:
        """Configure backup for the table."""
        
        if not self.props.enable_backup_plan:
            return
        
        # Create backup vault
        self.backup_vault = backup.BackupVault(
            self,
            "DynamoDBBackupVault",
            backup_vault_name=self.get_resource_name("backup-vault"),
            encryption_key=self.encryption_key,
            removal_policy=self._get_removal_policy()
        )
        
        # Create backup plan
        self.backup_plan = backup.BackupPlan(
            self,
            "DynamoDBBackupPlan",
            backup_plan_name=self.get_resource_name("backup-plan"),
            backup_vault=self.backup_vault
        )
        
        # Add backup rule
        self.backup_plan.add_rule(
            backup.BackupPlanRule(
                backup_vault=self.backup_vault,
                rule_name="DailyBackup",
                schedule_expression=events.Schedule.cron(
                    hour="2",
                    minute="0"
                ),
                delete_after=Duration.days(self.props.backup_retention_days),
                enable_continuous_backup=True,
                recovery_point_tags={
                    "Environment": self.environment,
                    "Project": self.project_name,
                    "BackupType": "Automated"
                }
            )
        )
        
        # Add DynamoDB table to backup plan
        self.backup_plan.add_selection(
            "DynamoDBBackupSelection",
            resources=[
                backup.BackupResource.from_dynamo_db_table(self.table)
            ],
            backup_selection_name=self.get_resource_name("backup-selection")
        )
    
    def _configure_streams(self) -> None:
        """Configure DynamoDB Streams if enabled."""
        
        if not self.props.enable_streams:
            return
        
        # Create Lambda function to process stream records
        self.stream_processor = lambda_.Function(
            self,
            "StreamProcessor",
            function_name=self.get_resource_name("stream-processor"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="stream_processor.handler",
            code=lambda_.Code.from_asset("src/lambda/dynamodb_streams"),
            role=self.create_service_role(
                "StreamProcessorRole",
                "lambda.amazonaws.com",
                managed_policies=[
                    "service-role/AWSLambdaBasicExecutionRole"
                ],
                inline_policies={
                    "DynamoDBStreamAccess": iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                effect=iam.Effect.ALLOW,
                                actions=[
                                    "dynamodb:DescribeStream",
                                    "dynamodb:GetRecords",
                                    "dynamodb:GetShardIterator",
                                    "dynamodb:ListStreams"
                                ],
                                resources=[
                                    f"{self.table.table_arn}/stream/*"
                                ]
                            )
                        ]
                    )
                }
            ),
            environment={
                "TABLE_NAME": self.table.table_name,
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            }
        )
        
        # Add DynamoDB stream as event source
        from aws_cdk import aws_lambda_event_sources as lambda_event_sources
        
        self.stream_processor.add_event_source(
            lambda_event_sources.DynamoEventSource(
                table=self.table,
                starting_position=lambda_.StartingPosition.LATEST,
                batch_size=10,
                max_batching_window=Duration.seconds(5),
                retry_attempts=3
            )
        )
    
    def _configure_global_tables(self) -> None:
        """Configure Global Tables for multi-region replication."""
        
        if not self.props.enable_global_tables or not self.props.replica_regions:
            return
        
        # Note: Global Tables v2 (2019.11.21) is automatically enabled for new tables
        # Additional configuration would be done through AWS CLI or SDK
        # This is a placeholder for future CDK support
        pass
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.consumed_read_capacity_metric = cloudwatch.Metric(
            namespace="AWS/DynamoDB",
            metric_name="ConsumedReadCapacityUnits",
            dimensions_map={
                "TableName": self.table.table_name
            }
        )
        
        self.consumed_write_capacity_metric = cloudwatch.Metric(
            namespace="AWS/DynamoDB",
            metric_name="ConsumedWriteCapacityUnits",
            dimensions_map={
                "TableName": self.table.table_name
            }
        )
        
        self.throttled_requests_metric = cloudwatch.Metric(
            namespace="AWS/DynamoDB",
            metric_name="ThrottledRequests",
            dimensions_map={
                "TableName": self.table.table_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighReadThrottling",
            cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="ReadThrottledEvents",
                dimensions_map={
                    "TableName": self.table.table_name
                }
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            description="Read throttling detected"
        )
        
        self.create_alarm(
            "HighWriteThrottling",
            cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="WriteThrottledEvents",
                dimensions_map={
                    "TableName": self.table.table_name
                }
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            description="Write throttling detected"
        )
        
        self.create_alarm(
            "HighErrorRate",
            cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="SystemErrors",
                dimensions_map={
                    "TableName": self.table.table_name
                }
            ),
            threshold=5,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High system error rate"
        )
        
        # Monitor backup success
        if self.props.enable_backup_plan:
            self.create_alarm(
                "BackupJobFailures",
                cloudwatch.Metric(
                    namespace="AWS/Backup",
                    metric_name="NumberOfBackupJobsFailed",
                    dimensions_map={
                        "BackupVaultName": self.backup_vault.backup_vault_name
                    }
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="DynamoDB backup job failures"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "TableName",
            self.table.table_name,
            "Name of the DynamoDB table"
        )
        
        self.add_output(
            "TableArn",
            self.table.table_arn,
            "ARN of the DynamoDB table"
        )
        
        if self.props.enable_streams:
            self.add_output(
                "StreamArn",
                self.table.table_stream_arn,
                "ARN of the DynamoDB stream"
            )
            
            self.add_output(
                "StreamProcessorFunctionName",
                self.stream_processor.function_name,
                "Name of the stream processor Lambda function"
            )
        
        if self.props.enable_backup_plan:
            self.add_output(
                "BackupVaultName",
                self.backup_vault.backup_vault_name,
                "Name of the backup vault"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.consumed_read_capacity_metric,
            self.consumed_write_capacity_metric,
            self.throttled_requests_metric,
            cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="SuccessfulRequestLatency",
                dimensions_map={
                    "TableName": self.table.table_name,
                    "Operation": "GetItem"
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="SuccessfulRequestLatency",
                dimensions_map={
                    "TableName": self.table.table_name,
                    "Operation": "PutItem"
                }
            )
        ]
        
        # Add GSI metrics
        for gsi in self.props.global_secondary_indexes:
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="ConsumedReadCapacityUnits",
                    dimensions_map={
                        "TableName": self.table.table_name,
                        "GlobalSecondaryIndexName": gsi["index_name"]
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/DynamoDB",
                    metric_name="ConsumedWriteCapacityUnits",
                    dimensions_map={
                        "TableName": self.table.table_name,
                        "GlobalSecondaryIndexName": gsi["index_name"]
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
    
    def grant_read_data(self, grantee: iam.IGrantable) -> iam.Grant:
        """Grant read permissions to the table."""
        return self.table.grant_read_data(grantee)
    
    def grant_write_data(self, grantee: iam.IGrantable) -> iam.Grant:
        """Grant write permissions to the table."""
        return self.table.grant_write_data(grantee)
    
    def grant_read_write_data(self, grantee: iam.IGrantable) -> iam.Grant:
        """Grant read and write permissions to the table."""
        return self.table.grant_read_write_data(grantee)
