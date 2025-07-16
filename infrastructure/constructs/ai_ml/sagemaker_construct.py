"""
SageMaker Construct for DevSecOps Platform.

This construct implements Amazon SageMaker with enterprise-grade configurations,
model training, deployment, monitoring, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from aws_cdk import (
    Duration,
    aws_sagemaker as sagemaker,
    aws_iam as iam,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    aws_ec2 as ec2,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class SageMakerConstructProps(ConstructProps):
    """Properties for SageMaker Construct."""
    
    # Model Configuration
    model_name: Optional[str] = None
    model_package_group_name: Optional[str] = None
    enable_model_registry: bool = True
    
    # Training Configuration
    enable_training: bool = True
    training_instance_type: str = "ml.m5.large"
    training_instance_count: int = 1
    training_volume_size_gb: int = 30
    max_runtime_hours: int = 24
    
    # Endpoint Configuration
    enable_endpoint: bool = True
    endpoint_name: Optional[str] = None
    endpoint_instance_type: str = "ml.t2.medium"
    endpoint_instance_count: int = 1
    enable_auto_scaling: bool = True
    min_capacity: int = 1
    max_capacity: int = 10
    target_invocations_per_instance: int = 1000
    
    # Data Configuration
    training_data_bucket: Optional[str] = None
    training_data_prefix: str = "training-data/"
    model_artifacts_bucket: Optional[str] = None
    model_artifacts_prefix: str = "model-artifacts/"
    
    # Network Configuration
    vpc_id: Optional[str] = None
    subnet_ids: List[str] = None
    security_group_ids: List[str] = None
    
    # Monitoring Configuration
    enable_model_monitoring: bool = True
    enable_data_quality_monitoring: bool = True
    enable_model_bias_monitoring: bool = True
    enable_model_explainability: bool = True
    monitoring_schedule_name: Optional[str] = None
    
    # Processing Configuration
    enable_processing: bool = False
    processing_instance_type: str = "ml.m5.large"
    processing_instance_count: int = 1
    
    # Pipeline Configuration
    enable_pipeline: bool = False
    pipeline_name: Optional[str] = None
    
    # Feature Store Configuration
    enable_feature_store: bool = False
    feature_group_name: Optional[str] = None
    
    # Multi-Model Endpoint Configuration
    enable_multi_model_endpoint: bool = False
    
    # A/B Testing Configuration
    enable_ab_testing: bool = False
    variant_weights: Dict[str, float] = None


class SageMakerConstruct(BaseConstruct):
    """
    SageMaker Construct.
    
    Implements a comprehensive SageMaker setup with:
    - Model training with distributed training support
    - Model registry for version management
    - Real-time and batch inference endpoints
    - Auto-scaling based on invocation metrics
    - Model monitoring and data quality checks
    - Feature store for ML feature management
    - ML pipelines for automated workflows
    - A/B testing for model variants
    - Multi-model endpoints for cost optimization
    - Comprehensive monitoring and alerting
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: SageMakerConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize SageMaker Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.variant_weights is None:
            self.props.variant_weights = {"variant-1": 1.0}
        
        # Create resources
        self._create_vpc_resources()
        self._create_s3_buckets()
        self._create_iam_roles()
        self._create_model_package_group()
        self._create_training_job()
        self._create_model()
        self._create_endpoint()
        self._create_auto_scaling()
        self._create_monitoring()
        self._create_feature_store()
        self._create_pipeline()
        
        # Add outputs
        self._create_outputs()
    
    def _create_vpc_resources(self) -> None:
        """Create or reference VPC resources."""
        
        if self.props.vpc_id:
            self.vpc = ec2.Vpc.from_lookup(
                self,
                "SageMakerVPC",
                vpc_id=self.props.vpc_id
            )
            
            # Get subnets
            if self.props.subnet_ids:
                self.subnets = [
                    ec2.Subnet.from_subnet_id(self, f"Subnet{i}", subnet_id)
                    for i, subnet_id in enumerate(self.props.subnet_ids)
                ]
            else:
                self.subnets = self.vpc.private_subnets
            
            # Create security group
            if not self.props.security_group_ids:
                self.security_group = ec2.SecurityGroup(
                    self,
                    "SageMakerSecurityGroup",
                    vpc=self.vpc,
                    security_group_name=self.get_resource_name("sagemaker-sg"),
                    description="Security group for SageMaker",
                    allow_all_outbound=True
                )
                self.security_groups = [self.security_group]
            else:
                self.security_groups = [
                    ec2.SecurityGroup.from_security_group_id(self, f"SG{i}", sg_id)
                    for i, sg_id in enumerate(self.props.security_group_ids)
                ]
    
    def _create_s3_buckets(self) -> None:
        """Create S3 buckets for training data and model artifacts."""
        
        # Training data bucket
        if not self.props.training_data_bucket:
            self.training_data_bucket = s3.Bucket(
                self,
                "TrainingDataBucket",
                bucket_name=self.get_resource_name("training-data"),
                versioning=True,
                encryption=s3.BucketEncryption.KMS,
                encryption_key=self.encryption_key,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                removal_policy=self._get_removal_policy()
            )
        else:
            self.training_data_bucket = s3.Bucket.from_bucket_name(
                self,
                "ExistingTrainingDataBucket",
                self.props.training_data_bucket
            )
        
        # Model artifacts bucket
        if not self.props.model_artifacts_bucket:
            self.model_artifacts_bucket = s3.Bucket(
                self,
                "ModelArtifactsBucket",
                bucket_name=self.get_resource_name("model-artifacts"),
                versioning=True,
                encryption=s3.BucketEncryption.KMS,
                encryption_key=self.encryption_key,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                removal_policy=self._get_removal_policy(),
                lifecycle_rules=[
                    s3.LifecycleRule(
                        id="ModelArtifactsLifecycle",
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

            # Apply standardized tags to model artifacts bucket
            artifacts_bucket_tags = self.get_resource_tags(
                application="ml-platform",
                component="model-artifacts",
                data_classification=getattr(self.props, 'data_classification', 'confidential'),
                backup_schedule="daily"
            )
            for key, value in artifacts_bucket_tags.items():
                if value:  # Only apply non-None values
                    self.model_artifacts_bucket.node.add_metadata(f"tag:{key}", value)
        else:
            self.model_artifacts_bucket = s3.Bucket.from_bucket_name(
                self,
                "ExistingModelArtifactsBucket",
                self.props.model_artifacts_bucket
            )
    
    def _create_iam_roles(self) -> None:
        """Create IAM roles for SageMaker."""
        
        # SageMaker execution role
        self.execution_role = self.create_service_role(
            "SageMakerExecutionRole",
            "sagemaker.amazonaws.com",
            managed_policies=[
                "AmazonSageMakerFullAccess"
            ],
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                self.training_data_bucket.bucket_arn,
                                f"{self.training_data_bucket.bucket_arn}/*",
                                self.model_artifacts_bucket.bucket_arn,
                                f"{self.model_artifacts_bucket.bucket_arn}/*"
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
                                "logs:PutLogEvents"
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/sagemaker/*"
                            ]
                        )
                    ]
                ),
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
                )
            }
        )
    
    def _create_model_package_group(self) -> None:
        """Create model package group for model registry."""
        
        if not self.props.enable_model_registry:
            return
        
        self.model_package_group = sagemaker.CfnModelPackageGroup(
            self,
            "ModelPackageGroup",
            model_package_group_name=self.props.model_package_group_name or self.get_resource_name("model-group"),
            model_package_group_description=f"Model package group for {self.project_name}",
            tags=[
                {
                    "Key": "Environment",
                    "Value": self.environment
                },
                {
                    "Key": "Project",
                    "Value": self.project_name
                }
            ]
        )
    
    def _create_training_job(self) -> None:
        """Create SageMaker training job configuration."""
        
        if not self.props.enable_training:
            return
        
        # VPC configuration
        vpc_config = None
        if hasattr(self, 'vpc'):
            vpc_config = sagemaker.CfnTrainingJob.VpcConfigProperty(
                security_group_ids=[sg.security_group_id for sg in self.security_groups],
                subnets=[subnet.subnet_id for subnet in self.subnets]
            )
        
        # Training job definition (template for actual training jobs)
        self.training_job_definition = {
            "AlgorithmSpecification": {
                "TrainingImage": "382416733822.dkr.ecr.us-east-1.amazonaws.com/sklearn_pandas:latest",
                "TrainingInputMode": "File"
            },
            "RoleArn": self.execution_role.role_arn,
            "InputDataConfig": [
                {
                    "ChannelName": "training",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": f"s3://{self.training_data_bucket.bucket_name}/{self.props.training_data_prefix}",
                            "S3DataDistributionType": "FullyReplicated"
                        }
                    },
                    "ContentType": "text/csv",
                    "CompressionType": "None"
                }
            ],
            "OutputDataConfig": {
                "S3OutputPath": f"s3://{self.model_artifacts_bucket.bucket_name}/{self.props.model_artifacts_prefix}"
            },
            "ResourceConfig": {
                "InstanceType": self.props.training_instance_type,
                "InstanceCount": self.props.training_instance_count,
                "VolumeSizeInGB": self.props.training_volume_size_gb
            },
            "StoppingCondition": {
                "MaxRuntimeInSeconds": self.props.max_runtime_hours * 3600
            },
            "VpcConfig": vpc_config
        }
    
    def _create_model(self) -> None:
        """Create SageMaker model."""
        
        # VPC configuration
        vpc_config = None
        if hasattr(self, 'vpc'):
            vpc_config = sagemaker.CfnModel.VpcConfigProperty(
                security_group_ids=[sg.security_group_id for sg in self.security_groups],
                subnets=[subnet.subnet_id for subnet in self.subnets]
            )
        
        self.model = sagemaker.CfnModel(
            self,
            "SageMakerModel",
            model_name=self.props.model_name or self.get_resource_name("model"),
            execution_role_arn=self.execution_role.role_arn,
            primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                image="382416733822.dkr.ecr.us-east-1.amazonaws.com/sklearn_pandas:latest",
                model_data_url=f"s3://{self.model_artifacts_bucket.bucket_name}/{self.props.model_artifacts_prefix}model.tar.gz",
                environment={
                    "SAGEMAKER_PROGRAM": "inference.py",
                    "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/code"
                }
            ),
            vpc_config=vpc_config,
            tags=[
                {
                    "Key": "Environment",
                    "Value": self.environment
                },
                {
                    "Key": "Project",
                    "Value": self.project_name
                }
            ]
        )
    
    def _create_endpoint(self) -> None:
        """Create SageMaker endpoint."""
        
        if not self.props.enable_endpoint:
            return
        
        # Endpoint configuration
        self.endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            "EndpointConfig",
            endpoint_config_name=self.get_resource_name("endpoint-config"),
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    variant_name="variant-1",
                    model_name=self.model.model_name,
                    instance_type=self.props.endpoint_instance_type,
                    initial_instance_count=self.props.endpoint_instance_count,
                    initial_variant_weight=1.0
                )
            ],
            data_capture_config=sagemaker.CfnEndpointConfig.DataCaptureConfigProperty(
                enable_capture=True,
                initial_sampling_percentage=100,
                destination_s3_uri=f"s3://{self.model_artifacts_bucket.bucket_name}/data-capture/",
                capture_options=[
                    sagemaker.CfnEndpointConfig.CaptureOptionProperty(
                        capture_mode="Input"
                    ),
                    sagemaker.CfnEndpointConfig.CaptureOptionProperty(
                        capture_mode="Output"
                    )
                ]
            ) if self.props.enable_model_monitoring else None,
            tags=[
                {
                    "Key": "Environment",
                    "Value": self.environment
                },
                {
                    "Key": "Project",
                    "Value": self.project_name
                }
            ]
        )
        
        # Endpoint
        self.endpoint = sagemaker.CfnEndpoint(
            self,
            "Endpoint",
            endpoint_name=self.props.endpoint_name or self.get_resource_name("endpoint"),
            endpoint_config_name=self.endpoint_config.endpoint_config_name,
            tags=[
                {
                    "Key": "Environment",
                    "Value": self.environment
                },
                {
                    "Key": "Project",
                    "Value": self.project_name
                }
            ]
        )
        
        self.endpoint.add_dependency(self.endpoint_config)
        self.endpoint.add_dependency(self.model)
    
    def _create_auto_scaling(self) -> None:
        """Create auto-scaling for SageMaker endpoint."""
        
        if not self.props.enable_auto_scaling or not self.props.enable_endpoint:
            return
        
        from aws_cdk import aws_applicationautoscaling as autoscaling
        
        # Create scalable target
        self.scalable_target = autoscaling.ScalableTarget(
            self,
            "EndpointScalableTarget",
            service_namespace=autoscaling.ServiceNamespace.SAGEMAKER,
            resource_id=f"endpoint/{self.endpoint.endpoint_name}/variant/variant-1",
            scalable_dimension="sagemaker:variant:DesiredInstanceCount",
            min_capacity=self.props.min_capacity,
            max_capacity=self.props.max_capacity
        )
        
        # Create scaling policy
        self.scaling_policy = autoscaling.TargetTrackingScalingPolicy(
            self,
            "EndpointScalingPolicy",
            scaling_target=self.scalable_target,
            target_value=self.props.target_invocations_per_instance,
            metric=cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="InvocationsPerInstance",
                dimensions_map={
                    "EndpointName": self.endpoint.endpoint_name,
                    "VariantName": "variant-1"
                }
            ),
            scale_in_cooldown=Duration.minutes(5),
            scale_out_cooldown=Duration.minutes(2)
        )
    
    def _create_monitoring(self) -> None:
        """Create model monitoring and alerting."""
        
        # Create custom metrics
        if self.props.enable_endpoint:
            self.invocations_metric = cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="Invocations",
                dimensions_map={
                    "EndpointName": self.endpoint.endpoint_name,
                    "VariantName": "variant-1"
                }
            )
            
            self.model_latency_metric = cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="ModelLatency",
                dimensions_map={
                    "EndpointName": self.endpoint.endpoint_name,
                    "VariantName": "variant-1"
                }
            )
            
            # Create alarms
            self.create_alarm(
                "HighModelLatency",
                self.model_latency_metric,
                threshold=5000,  # 5 seconds
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High model inference latency"
            )
            
            self.create_alarm(
                "HighInvocationErrors",
                cloudwatch.Metric(
                    namespace="AWS/SageMaker",
                    metric_name="Invocation4XXErrors",
                    dimensions_map={
                        "EndpointName": self.endpoint.endpoint_name,
                        "VariantName": "variant-1"
                    }
                ),
                threshold=10,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High number of invocation errors"
            )
        
        # Model monitoring
        if self.props.enable_model_monitoring and self.props.enable_endpoint:
            self._create_model_monitoring()
    
    def _create_model_monitoring(self) -> None:
        """Create model monitoring schedule."""
        
        # Create monitoring schedule
        monitoring_schedule_name = self.props.monitoring_schedule_name or self.get_resource_name("monitoring")
        
        self.monitoring_schedule = sagemaker.CfnMonitoringSchedule(
            self,
            "ModelMonitoringSchedule",
            monitoring_schedule_name=monitoring_schedule_name,
            monitoring_schedule_config=sagemaker.CfnMonitoringSchedule.MonitoringScheduleConfigProperty(
                monitoring_job_definition=sagemaker.CfnMonitoringSchedule.MonitoringJobDefinitionProperty(
                    monitoring_app_specification=sagemaker.CfnMonitoringSchedule.MonitoringAppSpecificationProperty(
                        image_uri="159807026194.dkr.ecr.us-east-1.amazonaws.com/sagemaker-model-monitor-analyzer:latest"
                    ),
                    monitoring_inputs=[
                        sagemaker.CfnMonitoringSchedule.MonitoringInputProperty(
                            endpoint_input=sagemaker.CfnMonitoringSchedule.EndpointInputProperty(
                                endpoint_name=self.endpoint.endpoint_name,
                                local_path="/opt/ml/processing/input/endpoint"
                            )
                        )
                    ],
                    monitoring_output_config=sagemaker.CfnMonitoringSchedule.MonitoringOutputConfigProperty(
                        monitoring_outputs=[
                            sagemaker.CfnMonitoringSchedule.MonitoringOutputProperty(
                                s3_output=sagemaker.CfnMonitoringSchedule.S3OutputProperty(
                                    s3_uri=f"s3://{self.model_artifacts_bucket.bucket_name}/monitoring-output/",
                                    local_path="/opt/ml/processing/output"
                                )
                            )
                        ]
                    ),
                    monitoring_resources=sagemaker.CfnMonitoringSchedule.MonitoringResourcesProperty(
                        cluster_config=sagemaker.CfnMonitoringSchedule.ClusterConfigProperty(
                            instance_count=1,
                            instance_type="ml.m5.large",
                            volume_size_in_gb=20
                        )
                    ),
                    role_arn=self.execution_role.role_arn
                ),
                schedule_config=sagemaker.CfnMonitoringSchedule.ScheduleConfigProperty(
                    schedule_expression="cron(0 * * * ? *)"  # Hourly
                )
            ),
            tags=[
                {
                    "Key": "Environment",
                    "Value": self.environment
                },
                {
                    "Key": "Project",
                    "Value": self.project_name
                }
            ]
        )
    
    def _create_feature_store(self) -> None:
        """Create SageMaker Feature Store."""
        
        if not self.props.enable_feature_store:
            return
        
        # Feature group
        self.feature_group = sagemaker.CfnFeatureGroup(
            self,
            "FeatureGroup",
            feature_group_name=self.props.feature_group_name or self.get_resource_name("feature-group"),
            record_identifier_feature_name="record_id",
            event_time_feature_name="event_time",
            feature_definitions=[
                sagemaker.CfnFeatureGroup.FeatureDefinitionProperty(
                    feature_name="record_id",
                    feature_type="String"
                ),
                sagemaker.CfnFeatureGroup.FeatureDefinitionProperty(
                    feature_name="event_time",
                    feature_type="String"
                )
            ],
            online_store_config=sagemaker.CfnFeatureGroup.OnlineStoreConfigProperty(
                enable_online_store=True,
                security_config=sagemaker.CfnFeatureGroup.OnlineStoreSecurityConfigProperty(
                    kms_key_id=self.encryption_key.key_id
                )
            ),
            offline_store_config=sagemaker.CfnFeatureGroup.OfflineStoreConfigProperty(
                s3_storage_config=sagemaker.CfnFeatureGroup.S3StorageConfigProperty(
                    s3_uri=f"s3://{self.model_artifacts_bucket.bucket_name}/feature-store/",
                    kms_key_id=self.encryption_key.key_id
                ),
                disable_glue_table_creation=False
            ),
            role_arn=self.execution_role.role_arn,
            tags=[
                {
                    "Key": "Environment",
                    "Value": self.environment
                },
                {
                    "Key": "Project",
                    "Value": self.project_name
                }
            ]
        )
    
    def _create_pipeline(self) -> None:
        """Create SageMaker ML Pipeline."""
        
        if not self.props.enable_pipeline:
            return
        
        # Pipeline definition would be created here
        # This is a placeholder for the pipeline structure
        self.pipeline_definition = {
            "Version": "2020-12-01",
            "Metadata": {},
            "Parameters": [],
            "PipelineExperimentConfig": {
                "ExperimentName": f"{self.project_name}-experiment",
                "TrialName": f"{self.project_name}-trial"
            },
            "Steps": []
        }
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        if hasattr(self, 'model'):
            self.add_output(
                "ModelName",
                self.model.model_name,
                "Name of the SageMaker model"
            )
        
        if self.props.enable_endpoint and hasattr(self, 'endpoint'):
            self.add_output(
                "EndpointName",
                self.endpoint.endpoint_name,
                "Name of the SageMaker endpoint"
            )
            
            self.add_output(
                "EndpointConfigName",
                self.endpoint_config.endpoint_config_name,
                "Name of the endpoint configuration"
            )
        
        if self.props.enable_model_registry and hasattr(self, 'model_package_group'):
            self.add_output(
                "ModelPackageGroupName",
                self.model_package_group.model_package_group_name,
                "Name of the model package group"
            )
        
        self.add_output(
            "ExecutionRoleArn",
            self.execution_role.role_arn,
            "ARN of the SageMaker execution role"
        )
        
        self.add_output(
            "TrainingDataBucketName",
            self.training_data_bucket.bucket_name,
            "Name of the training data bucket"
        )
        
        self.add_output(
            "ModelArtifactsBucketName",
            self.model_artifacts_bucket.bucket_name,
            "Name of the model artifacts bucket"
        )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = []
        
        if self.props.enable_endpoint and hasattr(self, 'endpoint'):
            metrics.extend([
                self.invocations_metric,
                self.model_latency_metric,
                cloudwatch.Metric(
                    namespace="AWS/SageMaker",
                    metric_name="Invocation4XXErrors",
                    dimensions_map={
                        "EndpointName": self.endpoint.endpoint_name,
                        "VariantName": "variant-1"
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/SageMaker",
                    metric_name="Invocation5XXErrors",
                    dimensions_map={
                        "EndpointName": self.endpoint.endpoint_name,
                        "VariantName": "variant-1"
                    }
                )
            ])
        
        return metrics
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
