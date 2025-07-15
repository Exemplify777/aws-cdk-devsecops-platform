"""
EC2 Construct for DevSecOps Platform.

This construct implements EC2 instances and Auto Scaling Groups with enterprise-grade
configurations, security, monitoring, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aws_cdk import (
    Duration,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ssm as ssm,
    aws_logs as logs,
    aws_backup as backup,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class Ec2ConstructProps(ConstructProps):
    """Properties for EC2 Construct."""
    
    # Instance Configuration
    instance_name: Optional[str] = None
    instance_type: str = "t3.medium"
    ami_id: Optional[str] = None
    key_pair_name: Optional[str] = None
    
    # Auto Scaling Configuration
    enable_auto_scaling: bool = True
    min_capacity: int = 1
    max_capacity: int = 10
    desired_capacity: int = 2
    
    # Network Configuration
    vpc_id: Optional[str] = None
    subnet_ids: List[str] = None
    security_group_ids: List[str] = None
    associate_public_ip: bool = False
    
    # Storage Configuration
    root_volume_size: int = 20
    root_volume_type: str = "gp3"
    enable_encryption: bool = True
    additional_volumes: List[Dict[str, Any]] = None
    
    # Load Balancer Configuration
    enable_load_balancer: bool = False
    load_balancer_type: str = "application"  # application, network
    target_port: int = 80
    health_check_path: str = "/health"
    
    # User Data Configuration
    user_data_script: Optional[str] = None
    install_cloudwatch_agent: bool = True
    install_ssm_agent: bool = True
    
    # Monitoring Configuration
    enable_detailed_monitoring: bool = True
    enable_cloudwatch_logs: bool = True
    log_retention_days: int = 30
    
    # Backup Configuration
    enable_backup: bool = True
    backup_retention_days: int = 7
    
    # Spot Instance Configuration
    enable_spot_instances: bool = False
    spot_price: Optional[str] = None
    spot_allocation_strategy: str = "diversified"  # diversified, lowest-price
    
    # Placement Configuration
    placement_group_strategy: Optional[str] = None  # cluster, partition, spread
    tenancy: str = "default"  # default, dedicated, host


class Ec2Construct(BaseConstruct):
    """
    EC2 Construct.
    
    Implements comprehensive EC2 infrastructure with:
    - Auto Scaling Groups with multiple instance types
    - Application/Network Load Balancers
    - CloudWatch monitoring and logging
    - Systems Manager integration
    - Backup strategies
    - Spot instance support
    - Security best practices
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: Ec2ConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize EC2 Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.additional_volumes is None:
            self.props.additional_volumes = []
        
        # Create resources
        self._create_vpc_resources()
        self._create_iam_resources()
        self._create_security_groups()
        self._create_launch_template()
        self._create_auto_scaling_group()
        self._create_load_balancer()
        self._create_backup_plan()
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
    
    def _create_iam_resources(self) -> None:
        """Create IAM role and instance profile."""
        
        self.instance_role = self.create_service_role(
            "Ec2InstanceRole",
            "ec2.amazonaws.com",
            managed_policies=[
                "AmazonSSMManagedInstanceCore",
                "CloudWatchAgentServerPolicy"
            ],
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
                                f"arn:aws:s3:::aws-codedeploy-{self.region}/*",
                                f"arn:aws:s3:::aws-ssm-{self.region}/*"
                            ]
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
                                "logs:PutLogEvents",
                                "logs:DescribeLogStreams"
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/ec2/*"
                            ]
                        )
                    ]
                )
            }
        )
        
        # Create instance profile
        self.instance_profile = iam.CfnInstanceProfile(
            self,
            "InstanceProfile",
            roles=[self.instance_role.role_name],
            instance_profile_name=self.get_resource_name("instance-profile")
        )
    
    def _create_security_groups(self) -> None:
        """Create security groups."""
        
        if self.props.security_group_ids:
            self.security_groups = [
                ec2.SecurityGroup.from_security_group_id(self, f"SG{i}", sg_id)
                for i, sg_id in enumerate(self.props.security_group_ids)
            ]
        else:
            # Create default security group
            self.security_group = ec2.SecurityGroup(
                self,
                "InstanceSecurityGroup",
                vpc=self.vpc,
                security_group_name=self.get_resource_name("instance-sg"),
                description="Security group for EC2 instances",
                allow_all_outbound=True
            )
            
            # Add common ingress rules
            self.security_group.add_ingress_rule(
                peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                connection=ec2.Port.tcp(22),
                description="SSH access from VPC"
            )
            
            if self.props.enable_load_balancer:
                self.security_group.add_ingress_rule(
                    peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                    connection=ec2.Port.tcp(self.props.target_port),
                    description=f"Application access on port {self.props.target_port}"
                )
            
            self.security_groups = [self.security_group]
    
    def _create_launch_template(self) -> None:
        """Create launch template."""
        
        # Get AMI
        if self.props.ami_id:
            ami = ec2.MachineImage.generic_linux({
                self.region: self.props.ami_id
            })
        else:
            # Use latest Amazon Linux 2
            ami = ec2.MachineImage.latest_amazon_linux(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
                edition=ec2.AmazonLinuxEdition.STANDARD,
                virtualization=ec2.AmazonLinuxVirt.HVM,
                storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
            )
        
        # Create user data
        user_data = ec2.UserData.for_linux()
        
        # Install CloudWatch agent
        if self.props.install_cloudwatch_agent:
            user_data.add_commands(
                "yum update -y",
                "yum install -y amazon-cloudwatch-agent",
                "systemctl enable amazon-cloudwatch-agent",
                "systemctl start amazon-cloudwatch-agent"
            )
        
        # Install SSM agent
        if self.props.install_ssm_agent:
            user_data.add_commands(
                "yum install -y amazon-ssm-agent",
                "systemctl enable amazon-ssm-agent",
                "systemctl start amazon-ssm-agent"
            )
        
        # Add custom user data
        if self.props.user_data_script:
            user_data.add_commands(self.props.user_data_script)
        
        # Create block device mappings
        block_devices = [
            ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size=self.props.root_volume_size,
                    volume_type=getattr(ec2.EbsDeviceVolumeType, self.props.root_volume_type.upper()),
                    encrypted=self.props.enable_encryption,
                    kms_key=self.encryption_key if self.props.enable_encryption else None,
                    delete_on_termination=True
                )
            )
        ]
        
        # Add additional volumes
        for i, volume in enumerate(self.props.additional_volumes):
            block_devices.append(
                ec2.BlockDevice(
                    device_name=volume.get("device_name", f"/dev/xvd{chr(98+i)}"),  # /dev/xvdb, /dev/xvdc, etc.
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=volume.get("size", 10),
                        volume_type=getattr(ec2.EbsDeviceVolumeType, volume.get("type", "gp3").upper()),
                        encrypted=volume.get("encrypted", True),
                        kms_key=self.encryption_key if volume.get("encrypted", True) else None,
                        delete_on_termination=volume.get("delete_on_termination", True)
                    )
                )
            )
        
        # Create launch template
        self.launch_template = ec2.LaunchTemplate(
            self,
            "LaunchTemplate",
            launch_template_name=self.get_resource_name("launch-template"),
            machine_image=ami,
            instance_type=ec2.InstanceType(self.props.instance_type),
            key_name=self.props.key_pair_name,
            security_group=self.security_groups[0] if len(self.security_groups) == 1 else None,
            user_data=user_data,
            role=self.instance_role,
            block_devices=block_devices,
            detailed_monitoring=self.props.enable_detailed_monitoring,
            associate_public_ip_address=self.props.associate_public_ip,
            require_imdsv2=True,  # Security best practice
            nitro_enclave_enabled=False
        )
    
    def _create_auto_scaling_group(self) -> None:
        """Create Auto Scaling Group."""
        
        if not self.props.enable_auto_scaling:
            return
        
        # Create placement group if specified
        placement_group = None
        if self.props.placement_group_strategy:
            placement_group = ec2.PlacementGroup(
                self,
                "PlacementGroup",
                strategy=getattr(ec2.PlacementGroupStrategy, self.props.placement_group_strategy.upper())
            )
        
        # Create Auto Scaling Group
        self.auto_scaling_group = autoscaling.AutoScalingGroup(
            self,
            "AutoScalingGroup",
            auto_scaling_group_name=self.get_resource_name("asg"),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=self.subnets),
            launch_template=self.launch_template,
            min_capacity=self.props.min_capacity,
            max_capacity=self.props.max_capacity,
            desired_capacity=self.props.desired_capacity,
            health_check=autoscaling.HealthCheck.elb(grace=Duration.minutes(5)) if self.props.enable_load_balancer else autoscaling.HealthCheck.ec2(),
            update_policy=autoscaling.UpdatePolicy.rolling_update(
                min_instances_in_service=1,
                max_batch_size=1,
                wait_on_resource_signals=True,
                signal_timeout=Duration.minutes(10)
            ),
            signals=autoscaling.Signals.wait_for_capacity_timeout(Duration.minutes(10)),
            spot_price=self.props.spot_price if self.props.enable_spot_instances else None,
            spot_instance_draining_enabled=self.props.enable_spot_instances
        )
        
        # Add scaling policies
        self.auto_scaling_group.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            cooldown=Duration.minutes(5)
        )
        
        self.auto_scaling_group.scale_on_metric(
            "MemoryScaling",
            metric=cloudwatch.Metric(
                namespace="CWAgent",
                metric_name="MemoryUtilization",
                dimensions_map={
                    "AutoScalingGroupName": self.auto_scaling_group.auto_scaling_group_name
                }
            ),
            scaling_steps=[
                autoscaling.ScalingInterval(upper=50, change=0),
                autoscaling.ScalingInterval(lower=50, upper=80, change=1),
                autoscaling.ScalingInterval(lower=80, change=2)
            ],
            adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY
        )
    
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
        
        # Create load balancer
        if self.props.load_balancer_type == "application":
            self.load_balancer = elbv2.ApplicationLoadBalancer(
                self,
                "ApplicationLoadBalancer",
                vpc=self.vpc,
                internet_facing=self.props.associate_public_ip,
                security_group=self.lb_security_group,
                vpc_subnets=ec2.SubnetSelection(subnets=self.subnets),
                load_balancer_name=self.get_resource_name("alb")
            )
            
            # Create target group
            self.target_group = elbv2.ApplicationTargetGroup(
                self,
                "TargetGroup",
                vpc=self.vpc,
                port=self.props.target_port,
                protocol=elbv2.ApplicationProtocol.HTTP,
                target_group_name=self.get_resource_name("tg"),
                health_check=elbv2.HealthCheck(
                    enabled=True,
                    healthy_http_codes="200",
                    path=self.props.health_check_path,
                    protocol=elbv2.Protocol.HTTP,
                    timeout=Duration.seconds(5),
                    interval=Duration.seconds(30),
                    healthy_threshold_count=2,
                    unhealthy_threshold_count=3
                ),
                targets=[self.auto_scaling_group] if hasattr(self, 'auto_scaling_group') else None
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
                internet_facing=self.props.associate_public_ip,
                vpc_subnets=ec2.SubnetSelection(subnets=self.subnets),
                load_balancer_name=self.get_resource_name("nlb")
            )
            
            # Create target group
            self.target_group = elbv2.NetworkTargetGroup(
                self,
                "TargetGroup",
                vpc=self.vpc,
                port=self.props.target_port,
                protocol=elbv2.Protocol.TCP,
                target_group_name=self.get_resource_name("tg"),
                health_check=elbv2.HealthCheck(
                    enabled=True,
                    protocol=elbv2.Protocol.TCP,
                    timeout=Duration.seconds(10),
                    interval=Duration.seconds(30),
                    healthy_threshold_count=2,
                    unhealthy_threshold_count=3
                ),
                targets=[self.auto_scaling_group] if hasattr(self, 'auto_scaling_group') else None
            )
            
            # Create listener
            self.listener = self.load_balancer.add_listener(
                "Listener",
                port=80,
                protocol=elbv2.Protocol.TCP,
                default_target_groups=[self.target_group]
            )
    
    def _create_backup_plan(self) -> None:
        """Create backup plan for EC2 instances."""
        
        if not self.props.enable_backup:
            return
        
        # Create backup vault
        self.backup_vault = backup.BackupVault(
            self,
            "Ec2BackupVault",
            backup_vault_name=self.get_resource_name("backup-vault"),
            encryption_key=self.encryption_key,
            removal_policy=self._get_removal_policy()
        )
        
        # Create backup plan
        self.backup_plan = backup.BackupPlan(
            self,
            "Ec2BackupPlan",
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
                recovery_point_tags={
                    "Environment": self.environment,
                    "Project": self.project_name,
                    "BackupType": "Automated"
                }
            )
        )
        
        # Add EC2 instances to backup plan
        if hasattr(self, 'auto_scaling_group'):
            self.backup_plan.add_selection(
                "Ec2BackupSelection",
                resources=[
                    backup.BackupResource.from_tag("aws:autoscaling:groupName", self.auto_scaling_group.auto_scaling_group_name)
                ],
                backup_selection_name=self.get_resource_name("backup-selection")
            )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create CloudWatch log group
        if self.props.enable_cloudwatch_logs:
            self.log_group = logs.LogGroup(
                self,
                "Ec2LogGroup",
                log_group_name=f"/aws/ec2/{self.get_resource_name('instances')}",
                retention=getattr(logs.RetentionDays, f"_{self.props.log_retention_days}_DAYS", logs.RetentionDays.ONE_MONTH),
                encryption_key=self.encryption_key,
                removal_policy=self._get_removal_policy()
            )
        
        # Create custom metrics
        if hasattr(self, 'auto_scaling_group'):
            self.cpu_utilization_metric = cloudwatch.Metric(
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions_map={
                    "AutoScalingGroupName": self.auto_scaling_group.auto_scaling_group_name
                }
            )
            
            # Create alarms
            self.create_alarm(
                "HighCPUUtilization",
                self.cpu_utilization_metric,
                threshold=80,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High CPU utilization on EC2 instances"
            )
            
            self.create_alarm(
                "LowCPUUtilization",
                self.cpu_utilization_metric,
                threshold=10,
                comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
                description="Low CPU utilization on EC2 instances"
            )
        
        # Load balancer monitoring
        if self.props.enable_load_balancer and hasattr(self, 'load_balancer'):
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
                description="Unhealthy targets detected"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        if hasattr(self, 'auto_scaling_group'):
            self.add_output(
                "AutoScalingGroupName",
                self.auto_scaling_group.auto_scaling_group_name,
                "Name of the Auto Scaling Group"
            )
            
            self.add_output(
                "AutoScalingGroupArn",
                self.auto_scaling_group.auto_scaling_group_arn,
                "ARN of the Auto Scaling Group"
            )
        
        if hasattr(self, 'load_balancer'):
            self.add_output(
                "LoadBalancerDnsName",
                self.load_balancer.load_balancer_dns_name,
                "DNS name of the load balancer"
            )
            
            self.add_output(
                "LoadBalancerArn",
                self.load_balancer.load_balancer_arn,
                "ARN of the load balancer"
            )
        
        self.add_output(
            "LaunchTemplateName",
            self.launch_template.launch_template_name,
            "Name of the launch template"
        )
        
        self.add_output(
            "InstanceRoleArn",
            self.instance_role.role_arn,
            "ARN of the instance IAM role"
        )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = []
        
        if hasattr(self, 'auto_scaling_group'):
            metrics.extend([
                self.cpu_utilization_metric,
                cloudwatch.Metric(
                    namespace="AWS/EC2",
                    metric_name="NetworkIn",
                    dimensions_map={
                        "AutoScalingGroupName": self.auto_scaling_group.auto_scaling_group_name
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/EC2",
                    metric_name="NetworkOut",
                    dimensions_map={
                        "AutoScalingGroupName": self.auto_scaling_group.auto_scaling_group_name
                    }
                )
            ])
        
        if self.props.enable_load_balancer and hasattr(self, 'load_balancer'):
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
