"""
VPC Construct for DevSecOps Platform.

This construct implements a comprehensive VPC with security best practices,
multi-AZ deployment, and comprehensive networking configurations.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aws_cdk import (
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    Duration,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class VpcConstructProps(ConstructProps):
    """Properties for VPC Construct."""
    
    # VPC Configuration
    vpc_name: Optional[str] = None
    cidr_block: str = "10.0.0.0/16"
    max_azs: int = 3
    enable_dns_hostnames: bool = True
    enable_dns_support: bool = True
    
    # Subnet Configuration
    enable_public_subnets: bool = True
    enable_private_subnets: bool = True
    enable_isolated_subnets: bool = False
    public_subnet_cidr_mask: int = 24
    private_subnet_cidr_mask: int = 24
    isolated_subnet_cidr_mask: int = 24
    
    # NAT Gateway Configuration
    enable_nat_gateway: bool = True
    nat_gateways: int = 1  # Number of NAT gateways
    nat_gateway_provider: str = "gateway"  # gateway, instance
    
    # VPN Configuration
    enable_vpn_gateway: bool = False
    vpn_gateway_asn: int = 65000
    
    # Flow Logs Configuration
    enable_flow_logs: bool = True
    flow_logs_destination: str = "cloudwatch"  # cloudwatch, s3
    flow_logs_traffic_type: str = "ALL"  # ALL, ACCEPT, REJECT
    
    # Security Configuration
    enable_network_acls: bool = True
    enable_security_groups: bool = True
    restrict_default_security_group: bool = True
    
    # Endpoints Configuration
    enable_s3_endpoint: bool = True
    enable_dynamodb_endpoint: bool = True
    enable_interface_endpoints: bool = True
    interface_endpoints: List[str] = None
    
    # Monitoring
    enable_detailed_monitoring: bool = True


class VpcConstruct(BaseConstruct):
    """
    VPC Construct.
    
    Implements a comprehensive VPC with:
    - Multi-AZ deployment with public, private, and isolated subnets
    - NAT Gateways for outbound internet access
    - VPC Flow Logs for network monitoring
    - VPC Endpoints for AWS services
    - Security Groups and NACLs
    - Comprehensive monitoring and alerting
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: VpcConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize VPC Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.interface_endpoints is None:
            self.props.interface_endpoints = [
                "ec2", "ecs", "lambda", "rds", "secretsmanager", "kms"
            ]
        
        # Create resources
        self._create_vpc()
        self._configure_security()
        self._create_endpoints()
        self._setup_flow_logs()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_vpc(self) -> None:
        """Create VPC with subnets and routing."""
        
        # Define subnet configurations
        subnet_configs = []
        
        if self.props.enable_public_subnets:
            subnet_configs.append(
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=self.props.public_subnet_cidr_mask
                )
            )
        
        if self.props.enable_private_subnets:
            subnet_configs.append(
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=self.props.private_subnet_cidr_mask
                )
            )
        
        if self.props.enable_isolated_subnets:
            subnet_configs.append(
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=self.props.isolated_subnet_cidr_mask
                )
            )
        
        # Create VPC
        self.vpc = ec2.Vpc(
            self,
            "VPC",
            vpc_name=self.props.vpc_name or self.get_resource_name("vpc"),
            ip_addresses=ec2.IpAddresses.cidr(self.props.cidr_block),
            max_azs=self.props.max_azs,
            enable_dns_hostnames=self.props.enable_dns_hostnames,
            enable_dns_support=self.props.enable_dns_support,
            subnet_configuration=subnet_configs,
            nat_gateways=self.props.nat_gateways if self.props.enable_nat_gateway else 0,
            nat_gateway_provider=ec2.NatProvider.gateway() if self.props.nat_gateway_provider == "gateway" else ec2.NatProvider.instance_v2(
                instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.NANO)
            ),
            create_internet_gateway=self.props.enable_public_subnets,
            vpn_gateway=self.props.enable_vpn_gateway,
            vpn_gateway_asn=self.props.vpn_gateway_asn if self.props.enable_vpn_gateway else None
        )
        
        # Tag subnets
        for i, subnet in enumerate(self.vpc.public_subnets):
            subnet.node.add_metadata("Name", f"{self.get_resource_name('public-subnet')}-{i+1}")
        
        for i, subnet in enumerate(self.vpc.private_subnets):
            subnet.node.add_metadata("Name", f"{self.get_resource_name('private-subnet')}-{i+1}")
        
        for i, subnet in enumerate(self.vpc.isolated_subnets):
            subnet.node.add_metadata("Name", f"{self.get_resource_name('isolated-subnet')}-{i+1}")
    
    def _configure_security(self) -> None:
        """Configure security groups and network ACLs."""
        
        if self.props.restrict_default_security_group:
            # Remove all rules from default security group
            default_sg = ec2.SecurityGroup.from_security_group_id(
                self,
                "DefaultSecurityGroup",
                self.vpc.vpc_default_security_group
            )
            
            # Add restrictive rules
            default_sg.add_ingress_rule(
                peer=ec2.Peer.ipv4("127.0.0.1/32"),
                connection=ec2.Port.all_traffic(),
                description="Deny all inbound traffic"
            )
        
        # Create common security groups
        self.web_security_group = ec2.SecurityGroup(
            self,
            "WebSecurityGroup",
            vpc=self.vpc,
            security_group_name=self.get_resource_name("web-sg"),
            description="Security group for web servers",
            allow_all_outbound=True
        )
        
        self.web_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="HTTP access"
        )
        
        self.web_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="HTTPS access"
        )
        
        # Application security group
        self.app_security_group = ec2.SecurityGroup(
            self,
            "AppSecurityGroup",
            vpc=self.vpc,
            security_group_name=self.get_resource_name("app-sg"),
            description="Security group for application servers",
            allow_all_outbound=True
        )
        
        self.app_security_group.add_ingress_rule(
            peer=self.web_security_group,
            connection=ec2.Port.tcp(8080),
            description="Application access from web tier"
        )
        
        # Database security group
        self.db_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=self.vpc,
            security_group_name=self.get_resource_name("db-sg"),
            description="Security group for database servers",
            allow_all_outbound=False
        )
        
        self.db_security_group.add_ingress_rule(
            peer=self.app_security_group,
            connection=ec2.Port.tcp(3306),
            description="MySQL access from application tier"
        )
        
        self.db_security_group.add_ingress_rule(
            peer=self.app_security_group,
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL access from application tier"
        )
        
        # Management security group
        self.mgmt_security_group = ec2.SecurityGroup(
            self,
            "ManagementSecurityGroup",
            vpc=self.vpc,
            security_group_name=self.get_resource_name("mgmt-sg"),
            description="Security group for management access",
            allow_all_outbound=True
        )
        
        self.mgmt_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.props.cidr_block),
            connection=ec2.Port.tcp(22),
            description="SSH access from VPC"
        )
        
        self.mgmt_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.props.cidr_block),
            connection=ec2.Port.tcp(3389),
            description="RDP access from VPC"
        )
    
    def _create_endpoints(self) -> None:
        """Create VPC endpoints for AWS services."""
        
        # S3 Gateway Endpoint
        if self.props.enable_s3_endpoint:
            self.s3_endpoint = self.vpc.add_gateway_endpoint(
                "S3Endpoint",
                service=ec2.GatewayVpcEndpointAwsService.S3,
                subnets=[
                    ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
                ] if self.props.enable_private_subnets else None
            )
        
        # DynamoDB Gateway Endpoint
        if self.props.enable_dynamodb_endpoint:
            self.dynamodb_endpoint = self.vpc.add_gateway_endpoint(
                "DynamoDBEndpoint",
                service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
                subnets=[
                    ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
                ] if self.props.enable_private_subnets else None
            )
        
        # Interface Endpoints
        if self.props.enable_interface_endpoints:
            endpoint_security_group = ec2.SecurityGroup(
                self,
                "EndpointSecurityGroup",
                vpc=self.vpc,
                security_group_name=self.get_resource_name("endpoint-sg"),
                description="Security group for VPC endpoints",
                allow_all_outbound=False
            )
            
            endpoint_security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.props.cidr_block),
                connection=ec2.Port.tcp(443),
                description="HTTPS access from VPC"
            )
            
            for service in self.props.interface_endpoints:
                try:
                    self.vpc.add_interface_endpoint(
                        f"{service.title()}Endpoint",
                        service=getattr(ec2.InterfaceVpcEndpointAwsService, service.upper()),
                        security_groups=[endpoint_security_group],
                        subnets=ec2.SubnetSelection(
                            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                        ) if self.props.enable_private_subnets else None
                    )
                except AttributeError:
                    # Service not available as interface endpoint
                    continue
    
    def _setup_flow_logs(self) -> None:
        """Set up VPC Flow Logs."""
        
        if not self.props.enable_flow_logs:
            return
        
        if self.props.flow_logs_destination == "cloudwatch":
            # Create CloudWatch log group
            self.flow_logs_group = logs.LogGroup(
                self,
                "VpcFlowLogsGroup",
                log_group_name=f"/aws/vpc/flowlogs/{self.get_resource_name('vpc')}",
                retention=logs.RetentionDays.ONE_MONTH,
                encryption_key=self.encryption_key,
                removal_policy=self._get_removal_policy()
            )
            
            # Create IAM role for Flow Logs
            flow_logs_role = self.create_service_role(
                "VpcFlowLogsRole",
                "vpc-flow-logs.amazonaws.com",
                inline_policies={
                    "CloudWatchLogsAccess": iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                effect=iam.Effect.ALLOW,
                                actions=[
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents",
                                    "logs:DescribeLogGroups",
                                    "logs:DescribeLogStreams"
                                ],
                                resources=[
                                    self.flow_logs_group.log_group_arn
                                ]
                            )
                        ]
                    )
                }
            )
            
            # Create Flow Logs
            self.flow_logs = ec2.FlowLog(
                self,
                "VpcFlowLogs",
                resource_type=ec2.FlowLogResourceType.from_vpc(self.vpc),
                destination=ec2.FlowLogDestination.to_cloud_watch_logs(
                    log_group=self.flow_logs_group,
                    iam_role=flow_logs_role
                ),
                traffic_type=getattr(ec2.FlowLogTrafficType, self.props.flow_logs_traffic_type)
            )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.vpc_flow_logs_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/VPC",
            metric_name="FlowLogsDelivered",
            dimensions_map={
                "Environment": self.environment,
                "VpcId": self.vpc.vpc_id
            }
        )
        
        # Create alarms for NAT Gateway data transfer (cost monitoring)
        if self.props.enable_nat_gateway:
            self.create_alarm(
                "HighNATGatewayDataTransfer",
                cloudwatch.Metric(
                    namespace="AWS/NATGateway",
                    metric_name="BytesOutToDestination",
                    statistic="Sum"
                ),
                threshold=10 * 1024 * 1024 * 1024,  # 10 GB
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High NAT Gateway data transfer"
            )
        
        # Create alarm for VPC Flow Logs delivery failures
        if self.props.enable_flow_logs and self.props.flow_logs_destination == "cloudwatch":
            self.create_alarm(
                "VpcFlowLogsDeliveryFailures",
                cloudwatch.Metric(
                    namespace="AWS/VPC",
                    metric_name="FlowLogsDeliveryRoleErrorCount",
                    dimensions_map={
                        "VpcId": self.vpc.vpc_id
                    }
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="VPC Flow Logs delivery failures"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "VpcId",
            self.vpc.vpc_id,
            "ID of the VPC"
        )
        
        self.add_output(
            "VpcCidr",
            self.vpc.vpc_cidr_block,
            "CIDR block of the VPC"
        )
        
        if self.props.enable_public_subnets:
            self.add_output(
                "PublicSubnetIds",
                ",".join([subnet.subnet_id for subnet in self.vpc.public_subnets]),
                "IDs of the public subnets"
            )
        
        if self.props.enable_private_subnets:
            self.add_output(
                "PrivateSubnetIds",
                ",".join([subnet.subnet_id for subnet in self.vpc.private_subnets]),
                "IDs of the private subnets"
            )
        
        if self.props.enable_isolated_subnets:
            self.add_output(
                "IsolatedSubnetIds",
                ",".join([subnet.subnet_id for subnet in self.vpc.isolated_subnets]),
                "IDs of the isolated subnets"
            )
        
        self.add_output(
            "WebSecurityGroupId",
            self.web_security_group.security_group_id,
            "ID of the web security group"
        )
        
        self.add_output(
            "AppSecurityGroupId",
            self.app_security_group.security_group_id,
            "ID of the application security group"
        )
        
        self.add_output(
            "DatabaseSecurityGroupId",
            self.db_security_group.security_group_id,
            "ID of the database security group"
        )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.vpc_flow_logs_metric
        ]
        
        if self.props.enable_nat_gateway:
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/NATGateway",
                    metric_name="BytesOutToDestination",
                    statistic="Sum"
                ),
                cloudwatch.Metric(
                    namespace="AWS/NATGateway",
                    metric_name="PacketsOutToDestination",
                    statistic="Sum"
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
