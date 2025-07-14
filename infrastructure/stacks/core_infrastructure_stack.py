"""
Core Infrastructure Stack
Provides foundational AWS infrastructure including VPC, subnets, NAT gateways, and basic networking
"""

from typing import Dict, Any, List
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_kms as kms,
    aws_logs as logs,
    aws_iam as iam,
    CfnOutput,
    RemovalPolicy,
    Duration,
)


class CoreInfrastructureStack(Stack):
    """Core infrastructure stack providing foundational AWS resources."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_config: Dict[str, Any],
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_config = env_config
        self.environment_name = env_config["environment_name"]
        
        # Create core infrastructure components
        self._create_kms_keys()
        self._create_vpc()
        self._create_s3_buckets()
        self._create_iam_roles()
        self._create_cloudwatch_log_groups()
        self._create_outputs()
    
    def _create_kms_keys(self) -> None:
        """Create KMS keys for encryption."""
        # Main encryption key for the platform
        self.main_kms_key = kms.Key(
            self,
            "MainKMSKey",
            description=f"Main encryption key for DevSecOps platform ({self.environment_name})",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN if self.env_config.get("enable_deletion_protection") else RemovalPolicy.DESTROY,
        )
        
        # S3 encryption key
        self.s3_kms_key = kms.Key(
            self,
            "S3KMSKey",
            description=f"S3 encryption key for DevSecOps platform ({self.environment_name})",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN if self.env_config.get("enable_deletion_protection") else RemovalPolicy.DESTROY,
        )
        
        # CloudWatch Logs encryption key
        self.logs_kms_key = kms.Key(
            self,
            "LogsKMSKey",
            description=f"CloudWatch Logs encryption key ({self.environment_name})",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN if self.env_config.get("enable_deletion_protection") else RemovalPolicy.DESTROY,
        )
        
        # Add CloudWatch Logs service principal to the key policy
        self.logs_kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudWatchLogs",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal(f"logs.{self.region}.amazonaws.com")],
                actions=[
                    "kms:Encrypt",
                    "kms:Decrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                    "kms:DescribeKey"
                ],
                resources=["*"],
                conditions={
                    "ArnEquals": {
                        "kms:EncryptionContext:aws:logs:arn": f"arn:aws:logs:{self.region}:{self.account}:log-group:*"
                    }
                }
            )
        )
    
    def _create_vpc(self) -> None:
        """Create VPC with public and private subnets."""
        # Create VPC
        self.vpc = ec2.Vpc(
            self,
            "VPC",
            ip_addresses=ec2.IpAddresses.cidr(self.env_config["vpc_cidr"]),
            max_azs=len(self.env_config["availability_zones"]),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )
        
        # Enable VPC Flow Logs
        if self.env_config.get("enable_vpc_flow_logs", True):
            flow_logs_role = iam.Role(
                self,
                "VPCFlowLogsRole",
                assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/VPCFlowLogsDeliveryRolePolicy")
                ]
            )
            
            self.vpc_flow_logs = ec2.FlowLog(
                self,
                "VPCFlowLogs",
                resource_type=ec2.FlowLogResourceType.from_vpc(self.vpc),
                destination=ec2.FlowLogDestination.to_cloud_watch_logs(
                    log_group=logs.LogGroup(
                        self,
                        "VPCFlowLogsGroup",
                        log_group_name=f"/aws/vpc/flowlogs/{self.environment_name}",
                        retention=logs.RetentionDays.ONE_MONTH,
                        encryption_key=self.logs_kms_key,
                        removal_policy=RemovalPolicy.DESTROY,
                    ),
                    iam_role=flow_logs_role
                ),
                traffic_type=ec2.FlowLogTrafficType.ALL,
            )
        
        # Create VPC Endpoints for AWS services
        self._create_vpc_endpoints()
    
    def _create_vpc_endpoints(self) -> None:
        """Create VPC endpoints for AWS services."""
        # S3 Gateway Endpoint
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)]
        )
        
        # DynamoDB Gateway Endpoint
        self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)]
        )
        
        # Interface endpoints for commonly used services
        interface_endpoints = [
            ("ECR", ec2.InterfaceVpcEndpointAwsService.ECR),
            ("ECR_DOCKER", ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER),
            ("ECS", ec2.InterfaceVpcEndpointAwsService.ECS),
            ("LOGS", ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS),
            ("MONITORING", ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_MONITORING),
            ("SSM", ec2.InterfaceVpcEndpointAwsService.SSM),
            ("SECRETS_MANAGER", ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER),
            ("KMS", ec2.InterfaceVpcEndpointAwsService.KMS),
        ]
        
        for name, service in interface_endpoints:
            self.vpc.add_interface_endpoint(
                f"{name}Endpoint",
                service=service,
                subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                private_dns_enabled=True,
            )
    
    def _create_s3_buckets(self) -> None:
        """Create S3 buckets for various purposes."""
        # Data lake bucket
        self.data_lake_bucket = s3.Bucket(
            self,
            "DataLakeBucket",
            bucket_name=f"{self.env_config['project_name']}-data-lake-{self.environment_name}-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.s3_kms_key,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN if self.env_config.get("enable_deletion_protection") else RemovalPolicy.DESTROY,
            auto_delete_objects=not self.env_config.get("enable_deletion_protection", False),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DataLakeLifecycle",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(365)
                        )
                    ]
                )
            ]
        )
        
        # Artifacts bucket for CI/CD
        self.artifacts_bucket = s3.Bucket(
            self,
            "ArtifactsBucket",
            bucket_name=f"{self.env_config['project_name']}-artifacts-{self.environment_name}-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.s3_kms_key,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ArtifactsLifecycle",
                    enabled=True,
                    expiration=Duration.days(90)
                )
            ]
        )

    def _create_iam_roles(self) -> None:
        """Create common IAM roles."""
        # Data pipeline execution role
        self.data_pipeline_role = iam.Role(
            self,
            "DataPipelineRole",
            role_name=f"DataPipelineRole-{self.environment_name}",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                iam.ServicePrincipal("glue.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
            ],
            inline_policies={
                "DataPipelinePolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject",
                                "s3:ListBucket",
                            ],
                            resources=[
                                self.data_lake_bucket.bucket_arn,
                                f"{self.data_lake_bucket.bucket_arn}/*",
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kms:Decrypt",
                                "kms:Encrypt",
                                "kms:GenerateDataKey",
                            ],
                            resources=[
                                self.main_kms_key.key_arn,
                                self.s3_kms_key.key_arn,
                            ]
                        )
                    ]
                )
            }
        )

        # CI/CD execution role
        self.cicd_role = iam.Role(
            self,
            "CICDRole",
            role_name=f"CICDRole-{self.environment_name}",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeBuildDeveloperAccess"),
            ],
            inline_policies={
                "CICDPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:ListBucket",
                            ],
                            resources=[
                                self.artifacts_bucket.bucket_arn,
                                f"{self.artifacts_bucket.bucket_arn}/*",
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )

    def _create_cloudwatch_log_groups(self) -> None:
        """Create CloudWatch log groups."""
        # Application logs
        self.app_log_group = logs.LogGroup(
            self,
            "ApplicationLogs",
            log_group_name=f"/aws/application/{self.environment_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            encryption_key=self.logs_kms_key,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Data pipeline logs
        self.pipeline_log_group = logs.LogGroup(
            self,
            "DataPipelineLogs",
            log_group_name=f"/aws/datapipeline/{self.environment_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            encryption_key=self.logs_kms_key,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Security logs
        self.security_log_group = logs.LogGroup(
            self,
            "SecurityLogs",
            log_group_name=f"/aws/security/{self.environment_name}",
            retention=logs.RetentionDays.THREE_MONTHS,
            encryption_key=self.logs_kms_key,
            removal_policy=RemovalPolicy.RETAIN if self.env_config.get("enable_deletion_protection") else RemovalPolicy.DESTROY,
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        CfnOutput(
            self,
            "VPCId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name=f"{self.stack_name}-VPCId"
        )

        CfnOutput(
            self,
            "DataLakeBucketName",
            value=self.data_lake_bucket.bucket_name,
            description="Data Lake S3 Bucket Name",
            export_name=f"{self.stack_name}-DataLakeBucketName"
        )

        CfnOutput(
            self,
            "ArtifactsBucketName",
            value=self.artifacts_bucket.bucket_name,
            description="Artifacts S3 Bucket Name",
            export_name=f"{self.stack_name}-ArtifactsBucketName"
        )

        CfnOutput(
            self,
            "MainKMSKeyId",
            value=self.main_kms_key.key_id,
            description="Main KMS Key ID",
            export_name=f"{self.stack_name}-MainKMSKeyId"
        )
        
        # Logs bucket
        self.logs_bucket = s3.Bucket(
            self,
            "LogsBucket",
            bucket_name=f"{self.env_config['project_name']}-logs-{self.environment_name}-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.s3_kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN if self.env_config.get("enable_deletion_protection") else RemovalPolicy.DESTROY,
            auto_delete_objects=not self.env_config.get("enable_deletion_protection", False),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="LogsLifecycle",
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
                    ],
                    expiration=Duration.days(2555)  # 7 years
                )
            ]
        )
