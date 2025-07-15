"""
RDS Construct for DevSecOps Platform.

This construct implements RDS databases with enterprise-grade configurations,
high availability, backup strategies, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_cloudwatch as cloudwatch,
    aws_backup as backup,
    aws_events as events,
    aws_lambda as lambda_,
    aws_logs as logs,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class RdsConstructProps(ConstructProps):
    """Properties for RDS Construct."""
    
    # Database Configuration
    database_name: str = "appdb"
    engine: str = "mysql"  # mysql, postgres, oracle, sqlserver
    engine_version: Optional[str] = None
    instance_class: str = "db.t3.micro"
    allocated_storage: int = 20
    max_allocated_storage: int = 100
    
    # Credentials Configuration
    master_username: str = "admin"
    manage_master_user_password: bool = True
    master_user_secret_kms_key: Optional[str] = None
    
    # Network Configuration
    vpc_id: Optional[str] = None
    subnet_group_name: Optional[str] = None
    security_group_ids: List[str] = None
    port: Optional[int] = None
    publicly_accessible: bool = False
    
    # High Availability Configuration
    multi_az: bool = True
    enable_read_replicas: bool = False
    read_replica_count: int = 1
    read_replica_instance_class: Optional[str] = None
    
    # Backup Configuration
    backup_retention_days: int = 7
    backup_window: str = "03:00-04:00"
    maintenance_window: str = "sun:04:00-sun:05:00"
    delete_automated_backups: bool = False
    enable_point_in_time_recovery: bool = True
    
    # Monitoring Configuration
    enable_performance_insights: bool = True
    performance_insights_retention: int = 7
    enable_enhanced_monitoring: bool = True
    monitoring_interval: int = 60
    enable_cloudwatch_logs_exports: List[str] = None
    
    # Security Configuration
    enable_encryption: bool = True
    storage_encrypted: bool = True
    enable_iam_database_authentication: bool = True
    enable_deletion_protection: bool = True
    
    # Parameter Groups
    parameter_group_parameters: Dict[str, str] = None
    
    # Snapshot Configuration
    final_snapshot_identifier: Optional[str] = None
    skip_final_snapshot: bool = False
    snapshot_identifier: Optional[str] = None
    
    # Auto Minor Version Upgrade
    auto_minor_version_upgrade: bool = True
    
    # Storage Configuration
    storage_type: str = "gp2"  # gp2, gp3, io1, io2
    iops: Optional[int] = None
    storage_throughput: Optional[int] = None


class RdsConstruct(BaseConstruct):
    """
    RDS Construct.
    
    Implements a comprehensive RDS database with:
    - Multi-AZ deployment for high availability
    - Read replicas for read scaling
    - Automated backups and point-in-time recovery
    - Performance Insights and Enhanced Monitoring
    - Encryption at rest and in transit
    - IAM database authentication
    - Parameter groups for optimization
    - Comprehensive monitoring and alerting
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: RdsConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize RDS Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults based on engine
        self._set_engine_defaults()
        
        # Create resources
        self._create_vpc_resources()
        self._create_security_resources()
        self._create_parameter_groups()
        self._create_subnet_group()
        self._create_database_instance()
        self._create_read_replicas()
        self._create_backup_plan()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _set_engine_defaults(self) -> None:
        """Set engine-specific defaults."""
        
        engine_defaults = {
            "mysql": {
                "engine_version": "8.0.35",
                "port": 3306,
                "logs_exports": ["error", "general", "slow-query"]
            },
            "postgres": {
                "engine_version": "15.4",
                "port": 5432,
                "logs_exports": ["postgresql"]
            },
            "oracle": {
                "engine_version": "19.0.0.0.ru-2023-07.rur-2023-07.r1",
                "port": 1521,
                "logs_exports": ["alert", "audit", "trace", "listener"]
            },
            "sqlserver": {
                "engine_version": "15.00.4236.7.v1",
                "port": 1433,
                "logs_exports": ["agent", "error"]
            }
        }
        
        defaults = engine_defaults.get(self.props.engine, {})
        
        if not self.props.engine_version:
            self.props.engine_version = defaults.get("engine_version")
        
        if not self.props.port:
            self.props.port = defaults.get("port")
        
        if not self.props.enable_cloudwatch_logs_exports:
            self.props.enable_cloudwatch_logs_exports = defaults.get("logs_exports", [])
    
    def _create_vpc_resources(self) -> None:
        """Create or reference VPC resources."""
        
        if self.props.vpc_id:
            self.vpc = ec2.Vpc.from_lookup(
                self,
                "VPC",
                vpc_id=self.props.vpc_id
            )
        else:
            # Use default VPC
            self.vpc = ec2.Vpc.from_lookup(
                self,
                "DefaultVPC",
                is_default=True
            )
    
    def _create_security_resources(self) -> None:
        """Create security groups and secrets."""
        
        # Create security group if not provided
        if self.props.security_group_ids:
            self.security_groups = [
                ec2.SecurityGroup.from_security_group_id(self, f"SG{i}", sg_id)
                for i, sg_id in enumerate(self.props.security_group_ids)
            ]
        else:
            self.security_group = ec2.SecurityGroup(
                self,
                "DatabaseSecurityGroup",
                vpc=self.vpc,
                security_group_name=self.get_resource_name("db-sg"),
                description="Security group for RDS database",
                allow_all_outbound=False
            )
            
            # Add ingress rule for database port
            self.security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                connection=ec2.Port.tcp(self.props.port),
                description=f"{self.props.engine.upper()} access from VPC"
            )
            
            self.security_groups = [self.security_group]
        
        # Create master user secret if not managing password
        if not self.props.manage_master_user_password:
            self.master_secret = secretsmanager.Secret(
                self,
                "MasterSecret",
                secret_name=self.get_resource_name("db-master"),
                description=f"Master credentials for {self.props.database_name}",
                generate_secret_string=secretsmanager.SecretStringGenerator(
                    secret_string_template=f'{{"username": "{self.props.master_username}"}}',
                    generate_string_key="password",
                    exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                    password_length=32
                ),
                encryption_key=self.encryption_key
            )
    
    def _create_parameter_groups(self) -> None:
        """Create parameter groups for database optimization."""
        
        if not self.props.parameter_group_parameters:
            # Set default parameters based on engine
            if self.props.engine == "mysql":
                self.props.parameter_group_parameters = {
                    "innodb_buffer_pool_size": "{DBInstanceClassMemory*3/4}",
                    "max_connections": "1000",
                    "slow_query_log": "1",
                    "long_query_time": "2",
                    "general_log": "1"
                }
            elif self.props.engine == "postgres":
                self.props.parameter_group_parameters = {
                    "shared_preload_libraries": "pg_stat_statements",
                    "log_statement": "all",
                    "log_min_duration_statement": "1000",
                    "max_connections": "1000"
                }
        
        if self.props.parameter_group_parameters:
            # Create DB parameter group
            self.parameter_group = rds.ParameterGroup(
                self,
                "ParameterGroup",
                engine=getattr(rds.DatabaseInstanceEngine, self.props.engine)(
                    version=getattr(rds.MysqlEngineVersion, f"VER_{self.props.engine_version.replace('.', '_')}")
                    if self.props.engine == "mysql" else
                    getattr(rds.PostgresEngineVersion, f"VER_{self.props.engine_version.replace('.', '_')}")
                    if self.props.engine == "postgres" else None
                ),
                parameters=self.props.parameter_group_parameters,
                description=f"Parameter group for {self.props.database_name}"
            )
    
    def _create_subnet_group(self) -> None:
        """Create DB subnet group."""
        
        if not self.props.subnet_group_name:
            # Use private subnets if available, otherwise isolated subnets
            subnets = self.vpc.private_subnets if self.vpc.private_subnets else self.vpc.isolated_subnets
            
            if not subnets:
                raise ValueError("No suitable subnets found for RDS. VPC must have private or isolated subnets.")
            
            self.subnet_group = rds.SubnetGroup(
                self,
                "SubnetGroup",
                description=f"Subnet group for {self.props.database_name}",
                vpc=self.vpc,
                vpc_subnets=ec2.SubnetSelection(subnets=subnets),
                subnet_group_name=self.get_resource_name("db-subnet-group")
            )
        else:
            self.subnet_group = rds.SubnetGroup.from_subnet_group_name(
                self,
                "ExistingSubnetGroup",
                self.props.subnet_group_name
            )
    
    def _create_database_instance(self) -> None:
        """Create RDS database instance."""
        
        # Create monitoring role for enhanced monitoring
        monitoring_role = None
        if self.props.enable_enhanced_monitoring:
            monitoring_role = self.create_service_role(
                "RdsMonitoringRole",
                "monitoring.rds.amazonaws.com",
                managed_policies=[
                    "service-role/AmazonRDSEnhancedMonitoringRole"
                ]
            )
        
        # Configure engine
        if self.props.engine == "mysql":
            engine = rds.DatabaseInstanceEngine.mysql(
                version=getattr(rds.MysqlEngineVersion, f"VER_{self.props.engine_version.replace('.', '_')}")
            )
        elif self.props.engine == "postgres":
            engine = rds.DatabaseInstanceEngine.postgres(
                version=getattr(rds.PostgresEngineVersion, f"VER_{self.props.engine_version.replace('.', '_')}")
            )
        elif self.props.engine == "oracle":
            engine = rds.DatabaseInstanceEngine.oracle_ee(
                version=getattr(rds.OracleEngineVersion, f"VER_{self.props.engine_version.replace('.', '_')}")
            )
        elif self.props.engine == "sqlserver":
            engine = rds.DatabaseInstanceEngine.sql_server_ex(
                version=getattr(rds.SqlServerEngineVersion, f"VER_{self.props.engine_version.replace('.', '_')}")
            )
        else:
            raise ValueError(f"Unsupported database engine: {self.props.engine}")
        
        # Create database instance
        self.database = rds.DatabaseInstance(
            self,
            "Database",
            instance_identifier=self.get_resource_name("db"),
            engine=engine,
            instance_type=ec2.InstanceType(self.props.instance_class),
            allocated_storage=self.props.allocated_storage,
            max_allocated_storage=self.props.max_allocated_storage,
            storage_type=getattr(rds.StorageType, self.props.storage_type.upper()),
            iops=self.props.iops,
            storage_throughput=self.props.storage_throughput,
            vpc=self.vpc,
            subnet_group=self.subnet_group,
            security_groups=self.security_groups,
            port=self.props.port,
            database_name=self.props.database_name,
            credentials=rds.Credentials.from_username(
                username=self.props.master_username,
                password=secretsmanager.Secret.from_secret_arn(
                    self, "MasterPassword", self.master_secret.secret_arn
                ).secret_value if hasattr(self, 'master_secret') else None,
                encryption_key=self.encryption_key if self.props.master_user_secret_kms_key else None
            ) if not self.props.manage_master_user_password else rds.Credentials.from_generated_secret(
                username=self.props.master_username,
                secret_name=self.get_resource_name("db-credentials"),
                encryption_key=self.encryption_key
            ),
            multi_az=self.props.multi_az,
            publicly_accessible=self.props.publicly_accessible,
            storage_encrypted=self.props.storage_encrypted,
            storage_encryption_key=self.encryption_key if self.props.enable_encryption else None,
            backup_retention=Duration.days(self.props.backup_retention_days),
            preferred_backup_window=self.props.backup_window,
            preferred_maintenance_window=self.props.maintenance_window,
            delete_automated_backups=self.props.delete_automated_backups,
            deletion_protection=self.props.enable_deletion_protection,
            enable_performance_insights=self.props.enable_performance_insights,
            performance_insight_retention=getattr(
                rds.PerformanceInsightRetention,
                f"MONTHS_{self.props.performance_insights_retention}"
                if self.props.performance_insights_retention <= 24 else "LONG_TERM"
            ) if self.props.enable_performance_insights else None,
            performance_insight_encryption_key=self.encryption_key if self.props.enable_performance_insights else None,
            monitoring_interval=Duration.seconds(self.props.monitoring_interval) if self.props.enable_enhanced_monitoring else None,
            monitoring_role=monitoring_role,
            cloudwatch_logs_exports=self.props.enable_cloudwatch_logs_exports,
            cloudwatch_logs_retention=logs.RetentionDays.ONE_MONTH,
            cloudwatch_logs_retention_role=self.create_service_role(
                "CloudWatchLogsRole",
                "logs.amazonaws.com"
            ) if self.props.enable_cloudwatch_logs_exports else None,
            parameter_group=self.parameter_group if hasattr(self, 'parameter_group') else None,
            auto_minor_version_upgrade=self.props.auto_minor_version_upgrade,
            iam_authentication=self.props.enable_iam_database_authentication,
            removal_policy=self._get_removal_policy(),
            snapshot_identifier=self.props.snapshot_identifier,
            copy_tags_to_snapshot=True
        )
        
        # Set final snapshot identifier
        if not self.props.skip_final_snapshot and not self.props.final_snapshot_identifier:
            self.props.final_snapshot_identifier = f"{self.get_resource_name('db')}-final-snapshot"
    
    def _create_read_replicas(self) -> None:
        """Create read replicas if enabled."""
        
        if not self.props.enable_read_replicas:
            return
        
        self.read_replicas = []
        
        for i in range(self.props.read_replica_count):
            read_replica = rds.DatabaseInstanceReadReplica(
                self,
                f"ReadReplica{i+1}",
                source_database_instance=self.database,
                instance_identifier=f"{self.get_resource_name('db')}-replica-{i+1}",
                instance_type=ec2.InstanceType(
                    self.props.read_replica_instance_class or self.props.instance_class
                ),
                vpc=self.vpc,
                subnet_group=self.subnet_group,
                security_groups=self.security_groups,
                publicly_accessible=self.props.publicly_accessible,
                enable_performance_insights=self.props.enable_performance_insights,
                performance_insight_retention=getattr(
                    rds.PerformanceInsightRetention,
                    f"MONTHS_{self.props.performance_insights_retention}"
                    if self.props.performance_insights_retention <= 24 else "LONG_TERM"
                ) if self.props.enable_performance_insights else None,
                performance_insight_encryption_key=self.encryption_key if self.props.enable_performance_insights else None,
                monitoring_interval=Duration.seconds(self.props.monitoring_interval) if self.props.enable_enhanced_monitoring else None,
                auto_minor_version_upgrade=self.props.auto_minor_version_upgrade,
                deletion_protection=self.props.enable_deletion_protection,
                removal_policy=self._get_removal_policy()
            )
            
            self.read_replicas.append(read_replica)
    
    def _create_backup_plan(self) -> None:
        """Create backup plan for RDS."""
        
        # Create backup vault
        self.backup_vault = backup.BackupVault(
            self,
            "RdsBackupVault",
            backup_vault_name=self.get_resource_name("backup-vault"),
            encryption_key=self.encryption_key,
            removal_policy=self._get_removal_policy()
        )
        
        # Create backup plan
        self.backup_plan = backup.BackupPlan(
            self,
            "RdsBackupPlan",
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
                delete_after=Duration.days(self.props.backup_retention_days * 2),  # Keep backups longer than automated
                recovery_point_tags={
                    "Environment": self.environment,
                    "Project": self.project_name,
                    "BackupType": "Manual"
                }
            )
        )
        
        # Add RDS instance to backup plan
        self.backup_plan.add_selection(
            "RdsBackupSelection",
            resources=[
                backup.BackupResource.from_rds_database_instance(self.database)
            ],
            backup_selection_name=self.get_resource_name("backup-selection")
        )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.cpu_utilization_metric = cloudwatch.Metric(
            namespace="AWS/RDS",
            metric_name="CPUUtilization",
            dimensions_map={
                "DBInstanceIdentifier": self.database.instance_identifier
            }
        )
        
        self.database_connections_metric = cloudwatch.Metric(
            namespace="AWS/RDS",
            metric_name="DatabaseConnections",
            dimensions_map={
                "DBInstanceIdentifier": self.database.instance_identifier
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighCPUUtilization",
            self.cpu_utilization_metric,
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High CPU utilization on RDS instance"
        )
        
        self.create_alarm(
            "HighDatabaseConnections",
            self.database_connections_metric,
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High number of database connections"
        )
        
        self.create_alarm(
            "LowFreeStorageSpace",
            cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="FreeStorageSpace",
                dimensions_map={
                    "DBInstanceIdentifier": self.database.instance_identifier
                }
            ),
            threshold=2 * 1024 * 1024 * 1024,  # 2 GB
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            description="Low free storage space on RDS instance"
        )
        
        self.create_alarm(
            "HighReadLatency",
            cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="ReadLatency",
                dimensions_map={
                    "DBInstanceIdentifier": self.database.instance_identifier
                }
            ),
            threshold=0.2,  # 200ms
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High read latency on RDS instance"
        )
        
        self.create_alarm(
            "HighWriteLatency",
            cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="WriteLatency",
                dimensions_map={
                    "DBInstanceIdentifier": self.database.instance_identifier
                }
            ),
            threshold=0.2,  # 200ms
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High write latency on RDS instance"
        )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "DatabaseEndpoint",
            self.database.instance_endpoint.hostname,
            "RDS database endpoint"
        )
        
        self.add_output(
            "DatabasePort",
            str(self.database.instance_endpoint.port),
            "RDS database port"
        )
        
        self.add_output(
            "DatabaseIdentifier",
            self.database.instance_identifier,
            "RDS database identifier"
        )
        
        self.add_output(
            "DatabaseArn",
            self.database.instance_arn,
            "RDS database ARN"
        )
        
        if hasattr(self, 'master_secret'):
            self.add_output(
                "MasterSecretArn",
                self.master_secret.secret_arn,
                "ARN of the master credentials secret"
            )
        
        if self.props.enable_read_replicas and self.read_replicas:
            for i, replica in enumerate(self.read_replicas):
                self.add_output(
                    f"ReadReplica{i+1}Endpoint",
                    replica.instance_endpoint.hostname,
                    f"Read replica {i+1} endpoint"
                )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.cpu_utilization_metric,
            self.database_connections_metric,
            cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="FreeStorageSpace",
                dimensions_map={
                    "DBInstanceIdentifier": self.database.instance_identifier
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="ReadLatency",
                dimensions_map={
                    "DBInstanceIdentifier": self.database.instance_identifier
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="WriteLatency",
                dimensions_map={
                    "DBInstanceIdentifier": self.database.instance_identifier
                }
            )
        ]
        
        # Add read replica metrics
        for i, replica in enumerate(self.read_replicas if hasattr(self, 'read_replicas') else []):
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/RDS",
                    metric_name="ReplicaLag",
                    dimensions_map={
                        "DBInstanceIdentifier": replica.instance_identifier
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/RDS",
                    metric_name="CPUUtilization",
                    dimensions_map={
                        "DBInstanceIdentifier": replica.instance_identifier
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
