"""
Security Stack
Implements comprehensive security controls including security groups, WAF, GuardDuty, and compliance monitoring
"""

from typing import Dict, Any, List
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_wafv2 as waf,
    aws_guardduty as guardduty,
    aws_securityhub as securityhub,
    aws_config as config,
    aws_cloudtrail as cloudtrail,
    aws_s3 as s3,
    aws_iam as iam,
    aws_kms as kms,
    aws_logs as logs,
    CfnOutput,
    RemovalPolicy,
    Duration,
)


class SecurityStack(Stack):
    """Security stack implementing comprehensive security controls."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_config: Dict[str, Any],
        vpc: ec2.Vpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_config = env_config
        self.environment_name = env_config["environment_name"]
        self.vpc = vpc
        
        # Create security components
        self._create_security_groups()
        self._create_waf()
        self._create_cloudtrail()
        self._create_config()
        self._create_guardduty()
        self._create_security_hub()
        self._create_outputs()
    
    def _create_security_groups(self) -> None:
        """Create security groups for different tiers."""
        # Web tier security group
        self.web_sg = ec2.SecurityGroup(
            self,
            "WebSecurityGroup",
            vpc=self.vpc,
            description="Security group for web tier",
            allow_all_outbound=False,
        )
        
        # Allow HTTPS inbound
        self.web_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS inbound"
        )
        
        # Allow HTTP inbound (for ALB health checks)
        self.web_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP inbound for health checks"
        )
        
        # Application tier security group
        self.app_sg = ec2.SecurityGroup(
            self,
            "AppSecurityGroup",
            vpc=self.vpc,
            description="Security group for application tier",
            allow_all_outbound=False,
        )
        
        # Allow traffic from web tier
        self.app_sg.add_ingress_rule(
            peer=self.web_sg,
            connection=ec2.Port.tcp(8080),
            description="Allow traffic from web tier"
        )
        
        # Database tier security group
        self.db_sg = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=self.vpc,
            description="Security group for database tier",
            allow_all_outbound=False,
        )
        
        # Allow traffic from application tier
        self.db_sg.add_ingress_rule(
            peer=self.app_sg,
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from app tier"
        )
        
        # Lambda security group
        self.lambda_sg = ec2.SecurityGroup(
            self,
            "LambdaSecurityGroup",
            vpc=self.vpc,
            description="Security group for Lambda functions",
            allow_all_outbound=True,  # Lambda needs outbound access
        )
        
        # ECS security group
        self.ecs_sg = ec2.SecurityGroup(
            self,
            "ECSSecurityGroup",
            vpc=self.vpc,
            description="Security group for ECS tasks",
            allow_all_outbound=True,
        )
        
        # Allow traffic from ALB
        self.ecs_sg.add_ingress_rule(
            peer=self.web_sg,
            connection=ec2.Port.tcp(8080),
            description="Allow traffic from ALB"
        )
        
        # Store security groups for easy access
        self.security_groups = {
            "web": self.web_sg,
            "app": self.app_sg,
            "database": self.db_sg,
            "lambda": self.lambda_sg,
            "ecs": self.ecs_sg,
        }
    
    def _create_waf(self) -> None:
        """Create WAF Web ACL for application protection."""
        # Create WAF Web ACL
        self.web_acl = waf.CfnWebACL(
            self,
            "WebACL",
            scope="REGIONAL",
            default_action=waf.CfnWebACL.DefaultActionProperty(allow={}),
            rules=[
                # AWS Managed Core Rule Set
                waf.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesCommonRuleSet",
                    priority=1,
                    override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet"
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="CommonRuleSetMetric"
                    )
                ),
                # AWS Managed Known Bad Inputs Rule Set
                waf.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesKnownBadInputsRuleSet",
                    priority=2,
                    override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesKnownBadInputsRuleSet"
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="KnownBadInputsMetric"
                    )
                ),
                # Rate limiting rule
                waf.CfnWebACL.RuleProperty(
                    name="RateLimitRule",
                    priority=3,
                    action=waf.CfnWebACL.RuleActionProperty(
                        block={}
                    ),
                    statement=waf.CfnWebACL.StatementProperty(
                        rate_based_statement=waf.CfnWebACL.RateBasedStatementProperty(
                            limit=2000,
                            aggregate_key_type="IP"
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimitMetric"
                    )
                )
            ],
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name="WebACLMetric"
            )
        )
    
    def _create_cloudtrail(self) -> None:
        """Create CloudTrail for audit logging."""
        if not self.env_config.get("enable_cloudtrail", True):
            return
        
        # Create CloudTrail S3 bucket
        self.cloudtrail_bucket = s3.Bucket(
            self,
            "CloudTrailBucket",
            bucket_name=f"{self.env_config['project_name']}-cloudtrail-{self.environment_name}-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN if self.env_config.get("enable_deletion_protection") else RemovalPolicy.DESTROY,
            auto_delete_objects=not self.env_config.get("enable_deletion_protection", False),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="CloudTrailLifecycle",
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
        
        # Create CloudTrail
        self.cloudtrail = cloudtrail.Trail(
            self,
            "CloudTrail",
            trail_name=f"DevSecOps-CloudTrail-{self.environment_name}",
            bucket=self.cloudtrail_bucket,
            include_global_service_events=True,
            is_multi_region_trail=True,
            enable_file_validation=True,
            send_to_cloud_watch_logs=True,
            cloud_watch_logs_retention=logs.RetentionDays.ONE_YEAR,
        )

    def _create_config(self) -> None:
        """Create AWS Config for compliance monitoring."""
        if not self.env_config.get("enable_config", True):
            return

        # Create Config S3 bucket
        self.config_bucket = s3.Bucket(
            self,
            "ConfigBucket",
            bucket_name=f"{self.env_config['project_name']}-config-{self.environment_name}-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN if self.env_config.get("enable_deletion_protection") else RemovalPolicy.DESTROY,
            auto_delete_objects=not self.env_config.get("enable_deletion_protection", False),
        )

        # Create Config service role
        self.config_role = iam.Role(
            self,
            "ConfigRole",
            assumed_by=iam.ServicePrincipal("config.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/ConfigRole")
            ]
        )

        # Grant Config access to the S3 bucket
        self.config_bucket.grant_read_write(self.config_role)

        # Create Config Configuration Recorder
        self.config_recorder = config.CfnConfigurationRecorder(
            self,
            "ConfigRecorder",
            name=f"DevSecOps-Config-{self.environment_name}",
            role_arn=self.config_role.role_arn,
            recording_group=config.CfnConfigurationRecorder.RecordingGroupProperty(
                all_supported=True,
                include_global_resource_types=True,
                recording_mode_overrides=[
                    config.CfnConfigurationRecorder.RecordingModeOverrideProperty(
                        resource_types=["AWS::EC2::Instance"],
                        recording_mode=config.CfnConfigurationRecorder.RecordingModeProperty(
                            recording_frequency="DAILY"
                        )
                    )
                ]
            )
        )

        # Create Config Delivery Channel
        self.config_delivery_channel = config.CfnDeliveryChannel(
            self,
            "ConfigDeliveryChannel",
            name=f"DevSecOps-Config-DeliveryChannel-{self.environment_name}",
            s3_bucket_name=self.config_bucket.bucket_name,
        )

        # Add Config Rules
        self._create_config_rules()

    def _create_config_rules(self) -> None:
        """Create AWS Config rules for compliance."""
        # Root access key check
        config.CfnConfigRule(
            self,
            "RootAccessKeyCheck",
            config_rule_name="root-access-key-check",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="ROOT_ACCESS_KEY_CHECK"
            )
        )

        # S3 bucket public access prohibited
        config.CfnConfigRule(
            self,
            "S3BucketPublicAccessProhibited",
            config_rule_name="s3-bucket-public-access-prohibited",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="S3_BUCKET_PUBLIC_ACCESS_PROHIBITED"
            )
        )

        # EC2 security group attached to ENI
        config.CfnConfigRule(
            self,
            "EC2SecurityGroupAttachedToEni",
            config_rule_name="ec2-security-group-attached-to-eni",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="EC2_SECURITY_GROUP_ATTACHED_TO_ENI"
            )
        )

        # IAM password policy
        config.CfnConfigRule(
            self,
            "IAMPasswordPolicy",
            config_rule_name="iam-password-policy",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="IAM_PASSWORD_POLICY"
            )
        )

    def _create_guardduty(self) -> None:
        """Create GuardDuty for threat detection."""
        if not self.env_config.get("enable_guardduty", True):
            return

        self.guardduty_detector = guardduty.CfnDetector(
            self,
            "GuardDutyDetector",
            enable=True,
            finding_publishing_frequency="FIFTEEN_MINUTES",
            datasources=guardduty.CfnDetector.CFNDataSourceConfigurationsProperty(
                s3_logs=guardduty.CfnDetector.CFNS3LogsConfigurationProperty(enable=True),
                kubernetes=guardduty.CfnDetector.CFNKubernetesConfigurationProperty(
                    audit_logs=guardduty.CfnDetector.CFNKubernetesAuditLogsConfigurationProperty(enable=True)
                ),
                malware_protection=guardduty.CfnDetector.CFNMalwareProtectionConfigurationProperty(
                    scan_ec2_instance_with_findings=guardduty.CfnDetector.CFNScanEc2InstanceWithFindingsConfigurationProperty(
                        ebs_volumes=True
                    )
                )
            )
        )

    def _create_security_hub(self) -> None:
        """Create Security Hub for centralized security findings."""
        if not self.env_config.get("enable_security_hub", True):
            return

        self.security_hub = securityhub.CfnHub(
            self,
            "SecurityHub",
            enable_default_standards=True,
            control_finding_generator="SECURITY_CONTROL",
            auto_enable_controls=True,
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        CfnOutput(
            self,
            "WebSecurityGroupId",
            value=self.web_sg.security_group_id,
            description="Web Security Group ID",
            export_name=f"{self.stack_name}-WebSecurityGroupId"
        )

        CfnOutput(
            self,
            "AppSecurityGroupId",
            value=self.app_sg.security_group_id,
            description="Application Security Group ID",
            export_name=f"{self.stack_name}-AppSecurityGroupId"
        )

        CfnOutput(
            self,
            "DatabaseSecurityGroupId",
            value=self.db_sg.security_group_id,
            description="Database Security Group ID",
            export_name=f"{self.stack_name}-DatabaseSecurityGroupId"
        )

        if hasattr(self, 'web_acl'):
            CfnOutput(
                self,
                "WebACLArn",
                value=self.web_acl.attr_arn,
                description="WAF Web ACL ARN",
                export_name=f"{self.stack_name}-WebACLArn"
            )
