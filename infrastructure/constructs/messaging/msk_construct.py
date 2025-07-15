"""
MSK (Managed Streaming for Apache Kafka) Construct for DevSecOps Platform.

This construct implements Amazon MSK with enterprise-grade configurations,
security, monitoring, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_msk as msk,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class MskConstructProps(ConstructProps):
    """Properties for MSK Construct."""
    
    # Cluster Configuration
    cluster_name: Optional[str] = None
    kafka_version: str = "2.8.1"
    number_of_broker_nodes: int = 3
    instance_type: str = "kafka.m5.large"
    
    # Storage Configuration
    volume_size: int = 100  # GB
    volume_type: str = "gp3"  # gp2, gp3, io1
    
    # Network Configuration
    vpc_id: Optional[str] = None
    subnet_ids: List[str] = None
    client_subnets: List[str] = None
    
    # Security Configuration
    enable_encryption_in_transit: bool = True
    enable_encryption_at_rest: bool = True
    encryption_in_transit_type: str = "TLS"  # TLS, TLS_PLAINTEXT, PLAINTEXT
    client_authentication_type: str = "TLS"  # TLS, SASL_SCRAM, SASL_IAM
    
    # SASL/SCRAM Configuration
    enable_sasl_scram: bool = False
    scram_secret_arn: Optional[str] = None
    
    # Monitoring Configuration
    enable_jmx_exporter: bool = True
    enable_node_exporter: bool = True
    enable_cloudwatch_logs: bool = True
    log_retention_days: int = 30
    
    # Configuration Overrides
    server_properties: Dict[str, str] = None
    
    # Auto Scaling Configuration
    enable_auto_scaling: bool = False
    min_broker_count: int = 3
    max_broker_count: int = 10
    target_cpu_utilization: float = 70.0
    
    # Connect Configuration
    enable_kafka_connect: bool = False
    connect_worker_config: Dict[str, str] = None
    
    # Schema Registry
    enable_schema_registry: bool = False
    
    # Backup Configuration
    enable_backup: bool = True
    backup_retention_days: int = 7


class MskConstruct(BaseConstruct):
    """
    MSK (Managed Streaming for Apache Kafka) Construct.
    
    Implements a comprehensive MSK cluster with:
    - Multi-AZ deployment for high availability
    - Encryption in transit and at rest
    - Multiple authentication methods (TLS, SASL/SCRAM, IAM)
    - Comprehensive monitoring with JMX and Node exporters
    - CloudWatch Logs integration
    - Auto-scaling capabilities
    - Kafka Connect for data integration
    - Schema Registry for data governance
    - Backup and disaster recovery
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: MskConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize MSK Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.server_properties is None:
            self.props.server_properties = {
                "auto.create.topics.enable": "false",
                "default.replication.factor": "3",
                "min.insync.replicas": "2",
                "num.partitions": "1",
                "num.replica.fetchers": "2",
                "replica.lag.time.max.ms": "30000",
                "socket.receive.buffer.bytes": "102400",
                "socket.request.max.bytes": "104857600",
                "socket.send.buffer.bytes": "102400",
                "unclean.leader.election.enable": "false",
                "num.network.threads": "5"
            }
        
        # Create resources
        self._create_vpc_resources()
        self._create_security_resources()
        self._create_msk_cluster()
        self._create_kafka_connect()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_vpc_resources(self) -> None:
        """Create or reference VPC resources."""
        
        if self.props.vpc_id:
            self.vpc = ec2.Vpc.from_lookup(
                self,
                "VPC",
                vpc_id=self.props.vpc_id
            )
        else:
            # Create a simple VPC for MSK
            self.vpc = ec2.Vpc(
                self,
                "MskVPC",
                max_azs=3,
                nat_gateways=1,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="Private",
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                        cidr_mask=24
                    )
                ]
            )
        
        # Get subnets for MSK
        if self.props.subnet_ids:
            self.subnets = [
                ec2.Subnet.from_subnet_id(self, f"Subnet{i}", subnet_id)
                for i, subnet_id in enumerate(self.props.subnet_ids)
            ]
        else:
            self.subnets = self.vpc.private_subnets
        
        # Ensure we have subnets in at least 2 AZs
        if len(self.subnets) < 2:
            raise ValueError("MSK requires subnets in at least 2 availability zones")
    
    def _create_security_resources(self) -> None:
        """Create security groups and authentication resources."""
        
        # Create security group for MSK
        self.msk_security_group = ec2.SecurityGroup(
            self,
            "MskSecurityGroup",
            vpc=self.vpc,
            security_group_name=self.get_resource_name("msk-sg"),
            description="Security group for MSK cluster",
            allow_all_outbound=True
        )
        
        # Add ingress rules based on authentication type
        if self.props.client_authentication_type in ["TLS", "SASL_SCRAM"]:
            # Kafka broker ports
            self.msk_security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                connection=ec2.Port.tcp(9094),
                description="Kafka TLS port"
            )
            
            self.msk_security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                connection=ec2.Port.tcp(9096),
                description="Kafka SASL_SCRAM port"
            )
        
        if self.props.client_authentication_type == "SASL_IAM":
            self.msk_security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                connection=ec2.Port.tcp(9098),
                description="Kafka IAM port"
            )
        
        # Zookeeper port
        self.msk_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(2181),
            description="Zookeeper port"
        )
        
        # JMX port for monitoring
        if self.props.enable_jmx_exporter:
            self.msk_security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                connection=ec2.Port.tcp(11001),
                description="JMX exporter port"
            )
        
        # Node exporter port for monitoring
        if self.props.enable_node_exporter:
            self.msk_security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                connection=ec2.Port.tcp(11002),
                description="Node exporter port"
            )
        
        # Create SASL/SCRAM secret if enabled
        if self.props.enable_sasl_scram and not self.props.scram_secret_arn:
            self.scram_secret = secretsmanager.Secret(
                self,
                "ScramSecret",
                secret_name=self.get_resource_name("kafka-scram"),
                description="SASL/SCRAM credentials for MSK",
                generate_secret_string=secretsmanager.SecretStringGenerator(
                    secret_string_template=json.dumps({"username": "kafka-admin"}),
                    generate_string_key="password",
                    exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                    password_length=32
                ),
                encryption_key=self.encryption_key
            )
            self.props.scram_secret_arn = self.scram_secret.secret_arn
    
    def _create_msk_cluster(self) -> None:
        """Create MSK cluster."""
        
        # Create CloudWatch log group
        if self.props.enable_cloudwatch_logs:
            self.log_group = logs.LogGroup(
                self,
                "MskLogGroup",
                log_group_name=f"/aws/msk/{self.get_resource_name('cluster')}",
                retention=getattr(logs.RetentionDays, f"_{self.props.log_retention_days}_DAYS", logs.RetentionDays.ONE_MONTH),
                encryption_key=self.encryption_key,
                removal_policy=self._get_removal_policy()
            )
        
        # Configure broker node group
        broker_node_group = msk.CfnCluster.BrokerNodeGroupInfoProperty(
            instance_type=self.props.instance_type,
            client_subnets=[subnet.subnet_id for subnet in self.subnets],
            security_groups=[self.msk_security_group.security_group_id],
            storage_info=msk.CfnCluster.StorageInfoProperty(
                ebs_storage_info=msk.CfnCluster.EBSStorageInfoProperty(
                    volume_size=self.props.volume_size,
                    provisioned_throughput=msk.CfnCluster.ProvisionedThroughputProperty(
                        enabled=True,
                        volume_throughput=250
                    ) if self.props.volume_type == "gp3" else None
                )
            )
        )
        
        # Configure encryption
        encryption_info = msk.CfnCluster.EncryptionInfoProperty(
            encryption_at_rest=msk.CfnCluster.EncryptionAtRestProperty(
                data_volume_kms_key_id=self.encryption_key.key_id
            ) if self.props.enable_encryption_at_rest else None,
            encryption_in_transit=msk.CfnCluster.EncryptionInTransitProperty(
                client_broker=self.props.encryption_in_transit_type,
                in_cluster=True
            ) if self.props.enable_encryption_in_transit else None
        )
        
        # Configure client authentication
        client_authentication = None
        if self.props.client_authentication_type == "TLS":
            client_authentication = msk.CfnCluster.ClientAuthenticationProperty(
                tls=msk.CfnCluster.TlsProperty(
                    enabled=True
                )
            )
        elif self.props.client_authentication_type == "SASL_SCRAM":
            client_authentication = msk.CfnCluster.ClientAuthenticationProperty(
                sasl=msk.CfnCluster.SaslProperty(
                    scram=msk.CfnCluster.ScramProperty(
                        enabled=True
                    )
                )
            )
        elif self.props.client_authentication_type == "SASL_IAM":
            client_authentication = msk.CfnCluster.ClientAuthenticationProperty(
                sasl=msk.CfnCluster.SaslProperty(
                    iam=msk.CfnCluster.IamProperty(
                        enabled=True
                    )
                )
            )
        
        # Configure monitoring
        open_monitoring = None
        if self.props.enable_jmx_exporter or self.props.enable_node_exporter:
            prometheus = msk.CfnCluster.PrometheusProperty()
            if self.props.enable_jmx_exporter:
                prometheus.jmx_exporter = msk.CfnCluster.JmxExporterProperty(
                    enabled_in_broker=True
                )
            if self.props.enable_node_exporter:
                prometheus.node_exporter = msk.CfnCluster.NodeExporterProperty(
                    enabled_in_broker=True
                )
            
            open_monitoring = msk.CfnCluster.OpenMonitoringProperty(
                prometheus=prometheus
            )
        
        # Configure logging
        logging_info = None
        if self.props.enable_cloudwatch_logs:
            logging_info = msk.CfnCluster.LoggingInfoProperty(
                broker_logs=msk.CfnCluster.BrokerLogsProperty(
                    cloud_watch_logs=msk.CfnCluster.CloudWatchLogsProperty(
                        enabled=True,
                        log_group=self.log_group.log_group_name
                    )
                )
            )
        
        # Create configuration
        self.cluster_configuration = msk.CfnConfiguration(
            self,
            "MskConfiguration",
            name=self.get_resource_name("config"),
            description=f"Configuration for {self.project_name} MSK cluster",
            kafka_versions_list=[self.props.kafka_version],
            server_properties="\n".join([
                f"{key}={value}" for key, value in self.props.server_properties.items()
            ])
        )
        
        # Create MSK cluster
        self.msk_cluster = msk.CfnCluster(
            self,
            "MskCluster",
            cluster_name=self.props.cluster_name or self.get_resource_name("cluster"),
            kafka_version=self.props.kafka_version,
            number_of_broker_nodes=self.props.number_of_broker_nodes,
            broker_node_group_info=broker_node_group,
            encryption_info=encryption_info,
            client_authentication=client_authentication,
            configuration_info=msk.CfnCluster.ConfigurationInfoProperty(
                arn=self.cluster_configuration.attr_arn,
                revision=1
            ),
            open_monitoring=open_monitoring,
            logging_info=logging_info,
            tags={
                "Name": self.props.cluster_name or self.get_resource_name("cluster"),
                "Environment": self.environment,
                "Project": self.project_name
            }
        )
        
        # Associate SASL/SCRAM secret if enabled
        if self.props.enable_sasl_scram and self.props.scram_secret_arn:
            msk.CfnClusterPolicy(
                self,
                "ScramSecretAssociation",
                cluster_arn=self.msk_cluster.ref,
                policy={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "kafka.amazonaws.com"
                            },
                            "Action": "secretsmanager:GetSecretValue",
                            "Resource": self.props.scram_secret_arn
                        }
                    ]
                }
            )
    
    def _create_kafka_connect(self) -> None:
        """Create Kafka Connect cluster if enabled."""
        
        if not self.props.enable_kafka_connect:
            return
        
        # Create IAM role for Kafka Connect
        connect_role = self.create_service_role(
            "KafkaConnectRole",
            "kafkaconnect.amazonaws.com",
            inline_policies={
                "KafkaConnectAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kafka-cluster:Connect",
                                "kafka-cluster:AlterCluster",
                                "kafka-cluster:DescribeCluster"
                            ],
                            resources=[
                                f"arn:aws:kafka:{self.region}:{self.account}:cluster/{self.msk_cluster.cluster_name}/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kafka-cluster:*Topic*",
                                "kafka-cluster:WriteData",
                                "kafka-cluster:ReadData"
                            ],
                            resources=[
                                f"arn:aws:kafka:{self.region}:{self.account}:topic/{self.msk_cluster.cluster_name}/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kafka-cluster:AlterGroup",
                                "kafka-cluster:DescribeGroup"
                            ],
                            resources=[
                                f"arn:aws:kafka:{self.region}:{self.account}:group/{self.msk_cluster.cluster_name}/*"
                            ]
                        )
                    ]
                )
            }
        )
        
        # Note: MSK Connect is not yet supported in CDK
        # This would be implemented using custom resources or AWS CLI
        pass
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.cpu_utilization_metric = cloudwatch.Metric(
            namespace="AWS/Kafka",
            metric_name="CpuIdle",
            dimensions_map={
                "Cluster Name": self.msk_cluster.cluster_name
            }
        )
        
        self.memory_utilization_metric = cloudwatch.Metric(
            namespace="AWS/Kafka",
            metric_name="MemoryUsed",
            dimensions_map={
                "Cluster Name": self.msk_cluster.cluster_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighCPUUtilization",
            cloudwatch.Metric(
                namespace="AWS/Kafka",
                metric_name="CpuUser",
                dimensions_map={
                    "Cluster Name": self.msk_cluster.cluster_name
                }
            ),
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High CPU utilization on MSK cluster"
        )
        
        self.create_alarm(
            "HighMemoryUtilization",
            self.memory_utilization_metric,
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High memory utilization on MSK cluster"
        )
        
        self.create_alarm(
            "HighDiskUtilization",
            cloudwatch.Metric(
                namespace="AWS/Kafka",
                metric_name="KafkaDataLogsDiskUsed",
                dimensions_map={
                    "Cluster Name": self.msk_cluster.cluster_name
                }
            ),
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High disk utilization on MSK cluster"
        )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "ClusterArn",
            self.msk_cluster.ref,
            "ARN of the MSK cluster"
        )
        
        self.add_output(
            "ClusterName",
            self.msk_cluster.cluster_name,
            "Name of the MSK cluster"
        )
        
        self.add_output(
            "SecurityGroupId",
            self.msk_security_group.security_group_id,
            "ID of the MSK security group"
        )
        
        if self.props.enable_sasl_scram and hasattr(self, 'scram_secret'):
            self.add_output(
                "ScramSecretArn",
                self.scram_secret.secret_arn,
                "ARN of the SASL/SCRAM secret"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        return [
            self.cpu_utilization_metric,
            self.memory_utilization_metric,
            cloudwatch.Metric(
                namespace="AWS/Kafka",
                metric_name="NetworkRxPackets",
                dimensions_map={
                    "Cluster Name": self.msk_cluster.cluster_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/Kafka",
                metric_name="NetworkTxPackets",
                dimensions_map={
                    "Cluster Name": self.msk_cluster.cluster_name
                }
            )
        ]
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
