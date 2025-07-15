"""
ECS Construct for DevSecOps Platform.

This construct implements ECS clusters and services with enterprise-grade
configurations, auto-scaling, service discovery, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aws_cdk import (
    Duration,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_servicediscovery as servicediscovery,
    aws_applicationautoscaling as autoscaling,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    aws_ecr as ecr,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class EcsConstructProps(ConstructProps):
    """Properties for ECS Construct."""
    
    # Cluster Configuration
    cluster_name: Optional[str] = None
    enable_fargate: bool = True
    enable_ec2: bool = False
    enable_container_insights: bool = True
    
    # Service Configuration
    service_name: Optional[str] = None
    task_definition_family: Optional[str] = None
    cpu: int = 256  # CPU units (256, 512, 1024, 2048, 4096)
    memory: int = 512  # Memory in MB
    
    # Container Configuration
    container_name: str = "app"
    container_image: str = "nginx:latest"
    container_port: int = 80
    environment_variables: Dict[str, str] = None
    secrets: Dict[str, str] = None  # Secret ARNs
    
    # Network Configuration
    vpc_id: Optional[str] = None
    subnet_ids: List[str] = None
    security_group_ids: List[str] = None
    assign_public_ip: bool = False
    
    # Load Balancer Configuration
    enable_load_balancer: bool = True
    load_balancer_type: str = "application"  # application, network
    health_check_path: str = "/health"
    health_check_grace_period: int = 60
    
    # Auto Scaling Configuration
    enable_auto_scaling: bool = True
    min_capacity: int = 1
    max_capacity: int = 10
    desired_count: int = 2
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 80.0
    
    # Service Discovery Configuration
    enable_service_discovery: bool = True
    namespace_name: Optional[str] = None
    service_discovery_name: Optional[str] = None
    
    # Logging Configuration
    enable_logging: bool = True
    log_retention_days: int = 30
    log_driver: str = "awslogs"
    
    # Storage Configuration
    enable_efs: bool = False
    efs_file_system_id: Optional[str] = None
    mount_points: List[Dict[str, Any]] = None
    
    # Deployment Configuration
    deployment_type: str = "rolling"  # rolling, blue_green
    deployment_minimum_healthy_percent: int = 50
    deployment_maximum_percent: int = 200
    
    # Task Role Configuration
    task_role_policies: List[str] = None
    execution_role_policies: List[str] = None


class EcsConstruct(BaseConstruct):
    """
    ECS Construct.
    
    Implements a comprehensive ECS infrastructure with:
    - Fargate and EC2 launch types
    - Application and Network Load Balancers
    - Auto-scaling based on CPU and memory
    - Service discovery with Route 53
    - CloudWatch logging and monitoring
    - EFS integration for persistent storage
    - Blue-green and rolling deployments
    - Security best practices
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: EcsConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize ECS Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.environment_variables is None:
            self.props.environment_variables = {}
        if self.props.secrets is None:
            self.props.secrets = {}
        if self.props.mount_points is None:
            self.props.mount_points = []
        if self.props.task_role_policies is None:
            self.props.task_role_policies = []
        if self.props.execution_role_policies is None:
            self.props.execution_role_policies = []
        
        # Create resources
        self._create_vpc_resources()
        self._create_ecs_cluster()
        self._create_service_discovery()
        self._create_iam_roles()
        self._create_task_definition()
        self._create_security_groups()
        self._create_load_balancer()
        self._create_ecs_service()
        self._create_auto_scaling()
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
            # Use default VPC
            self.vpc = ec2.Vpc.from_lookup(
                self,
                "DefaultVPC",
                is_default=True
            )
        
        # Get subnets
        if self.props.subnet_ids:
            self.subnets = [
                ec2.Subnet.from_subnet_id(self, f"Subnet{i}", subnet_id)
                for i, subnet_id in enumerate(self.props.subnet_ids)
            ]
        else:
            # Use private subnets if available, otherwise public
            self.subnets = self.vpc.private_subnets if self.vpc.private_subnets else self.vpc.public_subnets
    
    def _create_ecs_cluster(self) -> None:
        """Create ECS cluster."""
        
        self.cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=self.props.cluster_name or self.get_resource_name("cluster"),
            vpc=self.vpc,
            container_insights=self.props.enable_container_insights,
            enable_fargate_capacity_providers=self.props.enable_fargate,
            capacity_providers=["FARGATE", "FARGATE_SPOT"] if self.props.enable_fargate else None
        )
        
        # Add EC2 capacity if enabled
        if self.props.enable_ec2:
            self.cluster.add_capacity(
                "EC2Capacity",
                instance_type=ec2.InstanceType("t3.medium"),
                min_capacity=1,
                max_capacity=10,
                desired_capacity=2,
                vpc_subnets=ec2.SubnetSelection(subnets=self.subnets),
                auto_scaling_group_name=self.get_resource_name("ecs-asg")
            )
    
    def _create_service_discovery(self) -> None:
        """Create service discovery namespace."""
        
        if not self.props.enable_service_discovery:
            return
        
        # Create private DNS namespace
        self.namespace = servicediscovery.PrivateDnsNamespace(
            self,
            "ServiceDiscoveryNamespace",
            name=self.props.namespace_name or f"{self.project_name}.local",
            vpc=self.vpc,
            description=f"Service discovery namespace for {self.project_name}"
        )
    
    def _create_iam_roles(self) -> None:
        """Create IAM roles for ECS tasks."""
        
        # Task execution role
        self.execution_role = self.create_service_role(
            "EcsTaskExecutionRole",
            "ecs-tasks.amazonaws.com",
            managed_policies=[
                "service-role/AmazonECSTaskExecutionRolePolicy"
            ] + self.props.execution_role_policies,
            inline_policies={
                "SecretsManagerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "secretsmanager:GetSecretValue"
                            ],
                            resources=list(self.props.secrets.values()) if self.props.secrets else ["*"]
                        )
                    ]
                ) if self.props.secrets else None,
                "ECRAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ecr:GetAuthorizationToken",
                                "ecr:BatchCheckLayerAvailability",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage"
                            ],
                            resources=["*"]
                        )
                    ]
                ),
                "CloudWatchLogs": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/ecs/*"
                            ]
                        )
                    ]
                )
            }
        )
        
        # Task role
        self.task_role = self.create_service_role(
            "EcsTaskRole",
            "ecs-tasks.amazonaws.com",
            managed_policies=self.props.task_role_policies,
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject"
                            ],
                            resources=[
                                f"arn:aws:s3:::*/{self.project_name}/*"
                            ]
                        )
                    ]
                )
            }
        )
    
    def _create_task_definition(self) -> None:
        """Create ECS task definition."""
        
        # Create log group
        if self.props.enable_logging:
            self.log_group = logs.LogGroup(
                self,
                "EcsLogGroup",
                log_group_name=f"/ecs/{self.get_resource_name('service')}",
                retention=getattr(logs.RetentionDays, f"_{self.props.log_retention_days}_DAYS", logs.RetentionDays.ONE_MONTH),
                encryption_key=self.encryption_key,
                removal_policy=self._get_removal_policy()
            )
        
        # Create task definition
        self.task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            family=self.props.task_definition_family or self.get_resource_name("task"),
            cpu=self.props.cpu,
            memory_limit_mib=self.props.memory,
            execution_role=self.execution_role,
            task_role=self.task_role
        ) if self.props.enable_fargate else ecs.Ec2TaskDefinition(
            self,
            "TaskDefinition",
            family=self.props.task_definition_family or self.get_resource_name("task"),
            execution_role=self.execution_role,
            task_role=self.task_role
        )
        
        # Prepare environment variables
        environment = {
            "ENVIRONMENT": self.environment,
            "PROJECT_NAME": self.project_name,
            **self.props.environment_variables
        }
        
        # Prepare secrets
        secrets = {}
        for key, secret_arn in self.props.secrets.items():
            secrets[key] = ecs.Secret.from_secrets_manager(
                secretsmanager.Secret.from_secret_arn(self, f"Secret{key}", secret_arn)
            )
        
        # Create container
        self.container = self.task_definition.add_container(
            self.props.container_name,
            image=ecs.ContainerImage.from_registry(self.props.container_image),
            memory_limit_mib=self.props.memory if not self.props.enable_fargate else None,
            memory_reservation_mib=self.props.memory // 2 if not self.props.enable_fargate else None,
            cpu=self.props.cpu if not self.props.enable_fargate else None,
            environment=environment,
            secrets=secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ecs",
                log_group=self.log_group
            ) if self.props.enable_logging else None,
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", f"curl -f http://localhost:{self.props.container_port}{self.props.health_check_path} || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60)
            ),
            essential=True
        )
        
        # Add port mapping
        self.container.add_port_mappings(
            ecs.PortMapping(
                container_port=self.props.container_port,
                protocol=ecs.Protocol.TCP
            )
        )
        
        # Add mount points for EFS
        if self.props.enable_efs and self.props.efs_file_system_id:
            for mount_point in self.props.mount_points:
                self.task_definition.add_volume(
                    name=mount_point["name"],
                    efs_volume_configuration=ecs.EfsVolumeConfiguration(
                        file_system_id=self.props.efs_file_system_id,
                        transit_encryption="ENABLED",
                        authorization_config=ecs.AuthorizationConfig(
                            access_point_id=mount_point.get("access_point_id"),
                            iam="ENABLED"
                        )
                    )
                )
                
                self.container.add_mount_points(
                    ecs.MountPoint(
                        source_volume=mount_point["name"],
                        container_path=mount_point["container_path"],
                        read_only=mount_point.get("read_only", False)
                    )
                )
    
    def _create_security_groups(self) -> None:
        """Create security groups."""
        
        if self.props.security_group_ids:
            self.security_groups = [
                ec2.SecurityGroup.from_security_group_id(self, f"SG{i}", sg_id)
                for i, sg_id in enumerate(self.props.security_group_ids)
            ]
        else:
            # Create service security group
            self.service_security_group = ec2.SecurityGroup(
                self,
                "ServiceSecurityGroup",
                vpc=self.vpc,
                security_group_name=self.get_resource_name("service-sg"),
                description="Security group for ECS service",
                allow_all_outbound=True
            )
            
            # Add ingress rule for container port
            self.service_security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                connection=ec2.Port.tcp(self.props.container_port),
                description=f"Container port {self.props.container_port}"
            )
            
            self.security_groups = [self.service_security_group]
    
    def _create_load_balancer(self) -> None:
        """Create load balancer if enabled."""
        
        if not self.props.enable_load_balancer:
            return
        
        # Create load balancer security group
        self.lb_security_group = ec2.SecurityGroup(
            self,
            "LoadBalancerSecurityGroup",
            vpc=self.vpc,
            security_group_name=self.get_resource_name("lb-sg"),
            description="Security group for load balancer",
            allow_all_outbound=True
        )
        
        self.lb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="HTTP access"
        )
        
        self.lb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="HTTPS access"
        )
        
        # Allow load balancer to access service
        if hasattr(self, 'service_security_group'):
            self.service_security_group.add_ingress_rule(
                peer=self.lb_security_group,
                connection=ec2.Port.tcp(self.props.container_port),
                description="Load balancer access"
            )
        
        # Create load balancer
        if self.props.load_balancer_type == "application":
            self.load_balancer = elbv2.ApplicationLoadBalancer(
                self,
                "ApplicationLoadBalancer",
                vpc=self.vpc,
                internet_facing=self.props.assign_public_ip,
                security_group=self.lb_security_group,
                vpc_subnets=ec2.SubnetSelection(subnets=self.subnets),
                load_balancer_name=self.get_resource_name("alb")
            )
            
            # Create target group
            self.target_group = elbv2.ApplicationTargetGroup(
                self,
                "TargetGroup",
                vpc=self.vpc,
                port=self.props.container_port,
                protocol=elbv2.ApplicationProtocol.HTTP,
                target_group_name=self.get_resource_name("tg"),
                target_type=elbv2.TargetType.IP,
                health_check=elbv2.HealthCheck(
                    enabled=True,
                    healthy_http_codes="200",
                    path=self.props.health_check_path,
                    protocol=elbv2.Protocol.HTTP,
                    timeout=Duration.seconds(5),
                    interval=Duration.seconds(30),
                    healthy_threshold_count=2,
                    unhealthy_threshold_count=3
                )
            )
            
            # Create listener
            self.listener = self.load_balancer.add_listener(
                "Listener",
                port=80,
                protocol=elbv2.ApplicationProtocol.HTTP,
                default_target_groups=[self.target_group]
            )
        
        elif self.props.load_balancer_type == "network":
            self.load_balancer = elbv2.NetworkLoadBalancer(
                self,
                "NetworkLoadBalancer",
                vpc=self.vpc,
                internet_facing=self.props.assign_public_ip,
                vpc_subnets=ec2.SubnetSelection(subnets=self.subnets),
                load_balancer_name=self.get_resource_name("nlb")
            )
            
            # Create target group
            self.target_group = elbv2.NetworkTargetGroup(
                self,
                "TargetGroup",
                vpc=self.vpc,
                port=self.props.container_port,
                protocol=elbv2.Protocol.TCP,
                target_group_name=self.get_resource_name("tg"),
                target_type=elbv2.TargetType.IP,
                health_check=elbv2.HealthCheck(
                    enabled=True,
                    protocol=elbv2.Protocol.TCP,
                    timeout=Duration.seconds(10),
                    interval=Duration.seconds(30),
                    healthy_threshold_count=2,
                    unhealthy_threshold_count=3
                )
            )
            
            # Create listener
            self.listener = self.load_balancer.add_listener(
                "Listener",
                port=80,
                protocol=elbv2.Protocol.TCP,
                default_target_groups=[self.target_group]
            )
    
    def _create_ecs_service(self) -> None:
        """Create ECS service."""
        
        # Create service discovery service
        cloud_map_service = None
        if self.props.enable_service_discovery and hasattr(self, 'namespace'):
            cloud_map_service = self.namespace.create_service(
                "ServiceDiscovery",
                name=self.props.service_discovery_name or self.props.service_name or "app",
                dns_record_type=servicediscovery.DnsRecordType.A,
                dns_ttl=Duration.seconds(60),
                health_check_custom_config=servicediscovery.HealthCheckCustomConfig(
                    failure_threshold=1
                )
            )
        
        # Create ECS service
        self.service = ecs.FargateService(
            self,
            "EcsService",
            cluster=self.cluster,
            task_definition=self.task_definition,
            service_name=self.props.service_name or self.get_resource_name("service"),
            desired_count=self.props.desired_count,
            vpc_subnets=ec2.SubnetSelection(subnets=self.subnets),
            security_groups=self.security_groups,
            assign_public_ip=self.props.assign_public_ip,
            cloud_map_options=ecs.CloudMapOptions(
                cloud_map_service=cloud_map_service,
                container=self.container,
                container_port=self.props.container_port
            ) if cloud_map_service else None,
            health_check_grace_period=Duration.seconds(self.props.health_check_grace_period) if self.props.enable_load_balancer else None,
            deployment_configuration=ecs.DeploymentConfiguration(
                minimum_healthy_percent=self.props.deployment_minimum_healthy_percent,
                maximum_percent=self.props.deployment_maximum_percent
            ),
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE",
                    weight=1
                )
            ] if self.props.enable_fargate else None
        ) if self.props.enable_fargate else ecs.Ec2Service(
            self,
            "EcsService",
            cluster=self.cluster,
            task_definition=self.task_definition,
            service_name=self.props.service_name or self.get_resource_name("service"),
            desired_count=self.props.desired_count,
            vpc_subnets=ec2.SubnetSelection(subnets=self.subnets),
            security_groups=self.security_groups,
            cloud_map_options=ecs.CloudMapOptions(
                cloud_map_service=cloud_map_service,
                container=self.container,
                container_port=self.props.container_port
            ) if cloud_map_service else None,
            health_check_grace_period=Duration.seconds(self.props.health_check_grace_period) if self.props.enable_load_balancer else None,
            deployment_configuration=ecs.DeploymentConfiguration(
                minimum_healthy_percent=self.props.deployment_minimum_healthy_percent,
                maximum_percent=self.props.deployment_maximum_percent
            )
        )
        
        # Attach to load balancer
        if self.props.enable_load_balancer and hasattr(self, 'target_group'):
            self.service.attach_to_application_target_group(self.target_group)
    
    def _create_auto_scaling(self) -> None:
        """Create auto-scaling for ECS service."""
        
        if not self.props.enable_auto_scaling:
            return
        
        # Create scalable target
        self.scalable_target = self.service.auto_scale_task_count(
            min_capacity=self.props.min_capacity,
            max_capacity=self.props.max_capacity
        )
        
        # Scale on CPU utilization
        self.scalable_target.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=self.props.target_cpu_utilization,
            scale_in_cooldown=Duration.minutes(5),
            scale_out_cooldown=Duration.minutes(2)
        )
        
        # Scale on memory utilization
        self.scalable_target.scale_on_memory_utilization(
            "MemoryScaling",
            target_utilization_percent=self.props.target_memory_utilization,
            scale_in_cooldown=Duration.minutes(5),
            scale_out_cooldown=Duration.minutes(2)
        )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.cpu_utilization_metric = cloudwatch.Metric(
            namespace="AWS/ECS",
            metric_name="CPUUtilization",
            dimensions_map={
                "ServiceName": self.service.service_name,
                "ClusterName": self.cluster.cluster_name
            }
        )
        
        self.memory_utilization_metric = cloudwatch.Metric(
            namespace="AWS/ECS",
            metric_name="MemoryUtilization",
            dimensions_map={
                "ServiceName": self.service.service_name,
                "ClusterName": self.cluster.cluster_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighCPUUtilization",
            self.cpu_utilization_metric,
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High CPU utilization on ECS service"
        )
        
        self.create_alarm(
            "HighMemoryUtilization",
            self.memory_utilization_metric,
            threshold=80,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High memory utilization on ECS service"
        )
        
        self.create_alarm(
            "ServiceTaskCount",
            cloudwatch.Metric(
                namespace="AWS/ECS",
                metric_name="RunningTaskCount",
                dimensions_map={
                    "ServiceName": self.service.service_name,
                    "ClusterName": self.cluster.cluster_name
                }
            ),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            description="No running tasks in ECS service"
        )
        
        # Load balancer monitoring
        if self.props.enable_load_balancer and hasattr(self, 'target_group'):
            self.create_alarm(
                "UnhealthyTargets",
                cloudwatch.Metric(
                    namespace="AWS/ApplicationELB" if self.props.load_balancer_type == "application" else "AWS/NetworkELB",
                    metric_name="UnHealthyHostCount",
                    dimensions_map={
                        "LoadBalancer": self.load_balancer.load_balancer_full_name,
                        "TargetGroup": self.target_group.target_group_full_name
                    }
                ),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                description="Unhealthy targets in ECS service"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "ClusterName",
            self.cluster.cluster_name,
            "Name of the ECS cluster"
        )
        
        self.add_output(
            "ClusterArn",
            self.cluster.cluster_arn,
            "ARN of the ECS cluster"
        )
        
        self.add_output(
            "ServiceName",
            self.service.service_name,
            "Name of the ECS service"
        )
        
        self.add_output(
            "ServiceArn",
            self.service.service_arn,
            "ARN of the ECS service"
        )
        
        self.add_output(
            "TaskDefinitionArn",
            self.task_definition.task_definition_arn,
            "ARN of the task definition"
        )
        
        if self.props.enable_load_balancer and hasattr(self, 'load_balancer'):
            self.add_output(
                "LoadBalancerDnsName",
                self.load_balancer.load_balancer_dns_name,
                "DNS name of the load balancer"
            )
        
        if self.props.enable_service_discovery and hasattr(self, 'namespace'):
            self.add_output(
                "ServiceDiscoveryNamespace",
                self.namespace.namespace_name,
                "Service discovery namespace"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.cpu_utilization_metric,
            self.memory_utilization_metric,
            cloudwatch.Metric(
                namespace="AWS/ECS",
                metric_name="RunningTaskCount",
                dimensions_map={
                    "ServiceName": self.service.service_name,
                    "ClusterName": self.cluster.cluster_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/ECS",
                metric_name="PendingTaskCount",
                dimensions_map={
                    "ServiceName": self.service.service_name,
                    "ClusterName": self.cluster.cluster_name
                }
            )
        ]
        
        if self.props.enable_load_balancer and hasattr(self, 'target_group'):
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/ApplicationELB" if self.props.load_balancer_type == "application" else "AWS/NetworkELB",
                    metric_name="RequestCount",
                    dimensions_map={
                        "LoadBalancer": self.load_balancer.load_balancer_full_name
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/ApplicationELB" if self.props.load_balancer_type == "application" else "AWS/NetworkELB",
                    metric_name="TargetResponseTime",
                    dimensions_map={
                        "LoadBalancer": self.load_balancer.load_balancer_full_name
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
