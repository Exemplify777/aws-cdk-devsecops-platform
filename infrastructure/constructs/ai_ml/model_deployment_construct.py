"""
Model Deployment Construct for DevSecOps Platform.

This construct implements comprehensive model deployment with A/B testing,
canary deployments, multi-model endpoints, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    aws_sagemaker as sagemaker,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_s3 as s3,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class ModelDeploymentConstructProps(ConstructProps):
    """Properties for Model Deployment Construct."""

    # Deployment Configuration
    deployment_name: Optional[str] = None
    deployment_strategy: str = "blue_green"  # blue_green, canary, rolling

    # Model Configuration
    model_artifacts_bucket: Optional[str] = None
    model_artifacts_prefix: str = "models/"
    model_versions: Optional[List[Dict[str, Any]]] = None

    # Endpoint Configuration
    endpoint_name: Optional[str] = None
    instance_type: str = "ml.t2.medium"
    initial_instance_count: int = 1

    # A/B Testing Configuration
    enable_ab_testing: bool = True
    variant_configs: Optional[List[Dict[str, Any]]] = None
    traffic_routing_config: Optional[Dict[str, float]] = None

    # Canary Deployment Configuration
    canary_percentage: float = 10.0
    canary_duration_minutes: int = 30
    success_threshold_percentage: float = 95.0

    # Auto Rollback Configuration
    enable_auto_rollback: bool = True
    rollback_alarm_threshold: float = 5.0  # Error rate percentage
    rollback_evaluation_period_minutes: int = 5

    # API Gateway Integration
    enable_api_gateway: bool = True
    api_name: Optional[str] = None
    api_stage_name: str = "prod"
    enable_api_key: bool = True

    # Load Testing Configuration
    enable_load_testing: bool = True
    load_test_duration_minutes: int = 10
    target_rps: int = 100

    # Monitoring Configuration
    enable_detailed_monitoring: bool = True
    custom_metrics: Optional[List[Dict[str, Any]]] = None

    # Shadow Testing Configuration
    enable_shadow_testing: bool = False
    shadow_traffic_percentage: float = 5.0

    # Multi-Model Configuration
    enable_multi_model: bool = False
    max_models_per_endpoint: int = 10


class ModelDeploymentConstruct(BaseConstruct):
    """
    Model Deployment Construct.

    Implements comprehensive model deployment with:
    - Blue-green and canary deployment strategies
    - A/B testing with traffic splitting
    - Auto-rollback based on metrics
    - API Gateway integration for external access
    - Load testing and performance validation
    - Shadow testing for safe model validation
    - Multi-model endpoints for cost optimization
    - Comprehensive monitoring and alerting
    - Step Functions for deployment orchestration
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: ModelDeploymentConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize Model Deployment Construct.

        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)

        self.props = props

        # Set defaults
        if self.props.variant_configs is None:
            self.props.variant_configs = [
                {
                    "name": "variant-a",
                    "model_name": "model-a",
                    "instance_type": self.props.instance_type,
                    "initial_instance_count": self.props.initial_instance_count,
                    "initial_variant_weight": 1.0
                }
            ]

        if self.props.traffic_routing_config is None:
            self.props.traffic_routing_config = {"variant-a": 100.0}

        if self.props.custom_metrics is None:
            self.props.custom_metrics = []

        # Create resources
        self._create_iam_roles()
        self._create_model_artifacts_bucket()
        self._create_endpoint_configuration()
        self._create_deployment_pipeline()
        self._create_api_gateway()
        self._create_monitoring()
        self._create_load_testing()

        # Add outputs
        self._create_outputs()

    def _create_iam_roles(self) -> None:
        """Create IAM roles for model deployment."""

        # SageMaker execution role
        self.sagemaker_role = self.create_service_role(
            "ModelDeploymentSageMakerRole",
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
                                "s3:ListBucket"
                            ],
                            resources=[
                                f"arn:aws:s3:::{self.props.model_artifacts_bucket}",
                                f"arn:aws:s3:::{self.props.model_artifacts_bucket}/*"
                            ]
                        )
                    ]
                )
            }
        )

        # Step Functions execution role
        self.step_functions_role = self.create_service_role(
            "DeploymentStepFunctionsRole",
            "states.amazonaws.com",
            inline_policies={
                "SageMakerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sagemaker:CreateEndpoint",
                                "sagemaker:CreateEndpointConfig",
                                "sagemaker:UpdateEndpoint",
                                "sagemaker:DeleteEndpoint",
                                "sagemaker:DeleteEndpointConfig",
                                "sagemaker:DescribeEndpoint",
                                "sagemaker:DescribeEndpointConfig"
                            ],
                            resources=["*"]
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
                            resources=["*"]
                        )
                    ]
                ),
                "CloudWatchAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cloudwatch:GetMetricStatistics",
                                "cloudwatch:PutMetricData"
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )

    def _create_model_artifacts_bucket(self) -> None:
        """Create or reference model artifacts bucket."""

        if self.props.model_artifacts_bucket:
            self.model_bucket = s3.Bucket.from_bucket_name(
                self,
                "ModelArtifactsBucket",
                self.props.model_artifacts_bucket
            )
        else:
            self.model_bucket = s3.Bucket(
                self,
                "ModelArtifactsBucket",
                bucket_name=self.get_resource_name("model-artifacts"),
                versioning=True,
                encryption=s3.BucketEncryption.KMS,
                encryption_key=self.encryption_key,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                removal_policy=self._get_removal_policy()
            )

    def _create_endpoint_configuration(self) -> None:
        """Create SageMaker endpoint configuration."""

        # Create production variants
        production_variants = []
        for variant_config in self.props.variant_configs:
            production_variants.append(
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    variant_name=variant_config["name"],
                    model_name=variant_config["model_name"],
                    instance_type=variant_config["instance_type"],
                    initial_instance_count=variant_config["initial_instance_count"],
                    initial_variant_weight=variant_config["initial_variant_weight"]
                )
            )

        # Data capture configuration for monitoring
        data_capture_config = sagemaker.CfnEndpointConfig.DataCaptureConfigProperty(
            enable_capture=True,
            initial_sampling_percentage=100,
            destination_s3_uri=f"s3://{self.model_bucket.bucket_name}/data-capture/",
            capture_options=[
                sagemaker.CfnEndpointConfig.CaptureOptionProperty(capture_mode="Input"),
                sagemaker.CfnEndpointConfig.CaptureOptionProperty(capture_mode="Output")
            ]
        )

        # Endpoint configuration
        self.endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            "EndpointConfig",
            endpoint_config_name=self.get_resource_name("endpoint-config"),
            production_variants=production_variants,
            data_capture_config=data_capture_config if self.props.enable_detailed_monitoring else None,
            tags=[
                {"Key": "Environment", "Value": self.environment},
                {"Key": "Project", "Value": self.project_name}
            ]
        )

        # Endpoint
        self.endpoint = sagemaker.CfnEndpoint(
            self,
            "Endpoint",
            endpoint_name=self.props.endpoint_name or self.get_resource_name("endpoint"),
            endpoint_config_name=self.endpoint_config.endpoint_config_name,
            tags=[
                {"Key": "Environment", "Value": self.environment},
                {"Key": "Project", "Value": self.project_name}
            ]
        )

        self.endpoint.add_dependency(self.endpoint_config)

    def _create_deployment_pipeline(self) -> None:
        """Create Step Functions deployment pipeline."""

        # Lambda functions for deployment steps
        self._create_deployment_lambdas()

        # Define deployment steps
        validate_model_step = sfn_tasks.LambdaInvoke(
            self,
            "ValidateModel",
            lambda_function=self.validate_model_lambda,
            payload=sfn.TaskInput.from_object({
                "model_artifacts_uri": f"s3://{self.model_bucket.bucket_name}/{self.props.model_artifacts_prefix}",
                "deployment_config": sfn.JsonPath.string_at("$.deployment_config")
            })
        )

        create_endpoint_config_step = sfn_tasks.LambdaInvoke(
            self,
            "CreateEndpointConfig",
            lambda_function=self.create_endpoint_config_lambda,
            payload=sfn.TaskInput.from_object({
                "endpoint_config_name": sfn.JsonPath.string_at("$.endpoint_config_name"),
                "variant_configs": sfn.JsonPath.string_at("$.variant_configs")
            })
        )

        deploy_endpoint_step = sfn_tasks.LambdaInvoke(
            self,
            "DeployEndpoint",
            lambda_function=self.deploy_endpoint_lambda,
            payload=sfn.TaskInput.from_object({
                "endpoint_name": sfn.JsonPath.string_at("$.endpoint_name"),
                "endpoint_config_name": sfn.JsonPath.string_at("$.endpoint_config_name"),
                "deployment_strategy": self.props.deployment_strategy
            })
        )

        monitor_deployment_step = sfn_tasks.LambdaInvoke(
            self,
            "MonitorDeployment",
            lambda_function=self.monitor_deployment_lambda,
            payload=sfn.TaskInput.from_object({
                "endpoint_name": sfn.JsonPath.string_at("$.endpoint_name"),
                "monitoring_duration": self.props.canary_duration_minutes
            })
        )

        # Conditional rollback
        rollback_step = sfn_tasks.LambdaInvoke(
            self,
            "RollbackDeployment",
            lambda_function=self.rollback_lambda,
            payload=sfn.TaskInput.from_object({
                "endpoint_name": sfn.JsonPath.string_at("$.endpoint_name"),
                "previous_config": sfn.JsonPath.string_at("$.previous_config")
            })
        )

        # Success notification
        success_step = sfn_tasks.LambdaInvoke(
            self,
            "NotifySuccess",
            lambda_function=self.notification_lambda,
            payload=sfn.TaskInput.from_object({
                "status": "SUCCESS",
                "endpoint_name": sfn.JsonPath.string_at("$.endpoint_name")
            })
        )

        # Failure notification
        failure_step = sfn_tasks.LambdaInvoke(
            self,
            "NotifyFailure",
            lambda_function=self.notification_lambda,
            payload=sfn.TaskInput.from_object({
                "status": "FAILURE",
                "endpoint_name": sfn.JsonPath.string_at("$.endpoint_name"),
                "error": sfn.JsonPath.string_at("$.error")
            })
        )

        # Define deployment workflow
        deployment_choice = sfn.Choice(self, "DeploymentHealthy?")
        deployment_choice.when(
            sfn.Condition.boolean_equals("$.deployment_healthy", True),
            success_step
        ).otherwise(
            rollback_step.next(failure_step)
        )

        # Create state machine
        definition = validate_model_step.next(
            create_endpoint_config_step.next(
                deploy_endpoint_step.next(
                    monitor_deployment_step.next(deployment_choice)
                )
            )
        )

        self.deployment_state_machine = sfn.StateMachine(
            self,
            "DeploymentStateMachine",
            state_machine_name=self.get_resource_name("deployment-pipeline"),
            definition=definition,
            role=self.step_functions_role,
            timeout=Duration.hours(2)
        )

    def _create_deployment_lambdas(self) -> None:
        """Create Lambda functions for deployment pipeline."""

        # Common Lambda role
        lambda_role = self.create_service_role(
            "DeploymentLambdaRole",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaBasicExecutionRole"
            ],
            inline_policies={
                "SageMakerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sagemaker:*"
                            ],
                            resources=["*"]
                        )
                    ]
                ),
                "CloudWatchAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cloudwatch:GetMetricStatistics",
                                "cloudwatch:PutMetricData"
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )

        # Model validation Lambda
        self.validate_model_lambda = lambda_.Function(
            self,
            "ValidateModelLambda",
            function_name=self.get_resource_name("validate-model"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="validate_model.handler",
            code=lambda_.Code.from_asset("src/lambda/model_deployment"),
            role=lambda_role,
            timeout=Duration.minutes(5),
            environment={
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            }
        )

        # Endpoint config creation Lambda
        self.create_endpoint_config_lambda = lambda_.Function(
            self,
            "CreateEndpointConfigLambda",
            function_name=self.get_resource_name("create-endpoint-config"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="create_endpoint_config.handler",
            code=lambda_.Code.from_asset("src/lambda/model_deployment"),
            role=lambda_role,
            timeout=Duration.minutes(5)
        )

        # Endpoint deployment Lambda
        self.deploy_endpoint_lambda = lambda_.Function(
            self,
            "DeployEndpointLambda",
            function_name=self.get_resource_name("deploy-endpoint"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="deploy_endpoint.handler",
            code=lambda_.Code.from_asset("src/lambda/model_deployment"),
            role=lambda_role,
            timeout=Duration.minutes(15)
        )

        # Deployment monitoring Lambda
        self.monitor_deployment_lambda = lambda_.Function(
            self,
            "MonitorDeploymentLambda",
            function_name=self.get_resource_name("monitor-deployment"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="monitor_deployment.handler",
            code=lambda_.Code.from_asset("src/lambda/model_deployment"),
            role=lambda_role,
            timeout=Duration.minutes(10),
            environment={
                "SUCCESS_THRESHOLD": str(self.props.success_threshold_percentage),
                "ROLLBACK_THRESHOLD": str(self.props.rollback_alarm_threshold)
            }
        )

        # Rollback Lambda
        self.rollback_lambda = lambda_.Function(
            self,
            "RollbackLambda",
            function_name=self.get_resource_name("rollback"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="rollback.handler",
            code=lambda_.Code.from_asset("src/lambda/model_deployment"),
            role=lambda_role,
            timeout=Duration.minutes(10)
        )

        # Notification Lambda
        self.notification_lambda = lambda_.Function(
            self,
            "NotificationLambda",
            function_name=self.get_resource_name("notification"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="notification.handler",
            code=lambda_.Code.from_asset("src/lambda/model_deployment"),
            role=lambda_role,
            timeout=Duration.minutes(2)
        )

    def _create_api_gateway(self) -> None:
        """Create API Gateway for model inference."""

        if not self.props.enable_api_gateway:
            return

        # Create API Gateway
        self.api = apigateway.RestApi(
            self,
            "ModelInferenceAPI",
            rest_api_name=self.props.api_name or self.get_resource_name("inference-api"),
            description=f"Model inference API for {self.project_name}",
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name=self.props.api_stage_name,
                throttling_rate_limit=1000,
                throttling_burst_limit=2000,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            )
        )

        # Create Lambda function for API Gateway integration
        api_lambda_role = self.create_service_role(
            "APILambdaRole",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaBasicExecutionRole"
            ],
            inline_policies={
                "SageMakerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sagemaker:InvokeEndpoint"
                            ],
                            resources=[
                                f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{self.endpoint.endpoint_name}"
                            ]
                        )
                    ]
                )
            }
        )

        self.inference_lambda = lambda_.Function(
            self,
            "InferenceLambda",
            function_name=self.get_resource_name("inference"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="inference.handler",
            code=lambda_.Code.from_asset("src/lambda/model_deployment"),
            role=api_lambda_role,
            timeout=Duration.seconds(30),
            environment={
                "ENDPOINT_NAME": self.endpoint.endpoint_name,
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            }
        )

        # Create API integration
        inference_integration = apigateway.LambdaIntegration(
            self.inference_lambda,
            request_templates={
                "application/json": json.dumps({
                    "body": "$input.body",
                    "headers": "$input.params().header",
                    "queryStringParameters": "$input.params().querystring"
                })
            }
        )

        # Create API resources and methods
        predict_resource = self.api.root.add_resource("predict")
        predict_resource.add_method(
            "POST",
            inference_integration,
            api_key_required=self.props.enable_api_key,
            method_responses=[
                apigateway.MethodResponse(status_code="200"),
                apigateway.MethodResponse(status_code="400"),
                apigateway.MethodResponse(status_code="500")
            ]
        )

        # Health check endpoint
        health_resource = self.api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigateway.MockIntegration(
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": json.dumps({
                                "status": "healthy",
                                "timestamp": "$context.requestTime"
                            })
                        }
                    )
                ],
                request_templates={
                    "application/json": json.dumps({"statusCode": 200})
                }
            ),
            method_responses=[
                apigateway.MethodResponse(status_code="200")
            ]
        )

        # Create API key if enabled
        if self.props.enable_api_key:
            self.api_key = apigateway.ApiKey(
                self,
                "InferenceAPIKey",
                api_key_name=self.get_resource_name("inference-api-key")
            )

            # Create usage plan
            self.usage_plan = apigateway.UsagePlan(
                self,
                "InferenceUsagePlan",
                name=self.get_resource_name("inference-usage-plan"),
                throttle=apigateway.ThrottleSettings(
                    rate_limit=1000,
                    burst_limit=2000
                ),
                quota=apigateway.QuotaSettings(
                    limit=100000,
                    period=apigateway.Period.DAY
                ),
                api_stages=[
                    apigateway.UsagePlanPerApiStage(
                        api=self.api,
                        stage=self.api.deployment_stage
                    )
                ]
            )

            self.usage_plan.add_api_key(self.api_key)

    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""

        # Endpoint monitoring
        self.invocations_metric = cloudwatch.Metric(
            namespace="AWS/SageMaker",
            metric_name="Invocations",
            dimensions_map={
                "EndpointName": self.endpoint.endpoint_name
            }
        )

        self.model_latency_metric = cloudwatch.Metric(
            namespace="AWS/SageMaker",
            metric_name="ModelLatency",
            dimensions_map={
                "EndpointName": self.endpoint.endpoint_name
            }
        )

        # Create alarms
        self.create_alarm(
            "HighErrorRate",
            cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="Invocation4XXErrors",
                dimensions_map={
                    "EndpointName": self.endpoint.endpoint_name
                }
            ),
            threshold=self.props.rollback_alarm_threshold,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High error rate - potential rollback trigger"
        )

        self.create_alarm(
            "HighLatency",
            self.model_latency_metric,
            threshold=5000,  # 5 seconds
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High model latency"
        )

        # API Gateway monitoring
        if self.props.enable_api_gateway:
            self.create_alarm(
                "APIHighErrorRate",
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="4XXError",
                    dimensions_map={
                        "ApiName": self.api.rest_api_name
                    }
                ),
                threshold=10,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High API error rate"
            )

    def _create_load_testing(self) -> None:
        """Create load testing configuration."""

        if not self.props.enable_load_testing:
            return

        # Load testing Lambda
        load_test_role = self.create_service_role(
            "LoadTestRole",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaBasicExecutionRole"
            ],
            inline_policies={
                "SageMakerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sagemaker:InvokeEndpoint"
                            ],
                            resources=[
                                f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{self.endpoint.endpoint_name}"
                            ]
                        )
                    ]
                )
            }
        )

        self.load_test_lambda = lambda_.Function(
            self,
            "LoadTestLambda",
            function_name=self.get_resource_name("load-test"),
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="load_test.handler",
            code=lambda_.Code.from_asset("src/lambda/model_deployment"),
            role=load_test_role,
            timeout=Duration.minutes(self.props.load_test_duration_minutes + 5),
            environment={
                "ENDPOINT_NAME": self.endpoint.endpoint_name,
                "TARGET_RPS": str(self.props.target_rps),
                "DURATION_MINUTES": str(self.props.load_test_duration_minutes)
            }
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""

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

        self.add_output(
            "DeploymentStateMachineArn",
            self.deployment_state_machine.state_machine_arn,
            "ARN of the deployment state machine"
        )

        if self.props.enable_api_gateway:
            self.add_output(
                "InferenceAPIUrl",
                self.api.url,
                "URL of the inference API"
            )

            if self.props.enable_api_key:
                self.add_output(
                    "APIKeyId",
                    self.api_key.key_id,
                    "ID of the API key"
                )

    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        metrics = [
            self.invocations_metric,
            self.model_latency_metric,
            cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="Invocation4XXErrors",
                dimensions_map={
                    "EndpointName": self.endpoint.endpoint_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="Invocation5XXErrors",
                dimensions_map={
                    "EndpointName": self.endpoint.endpoint_name
                }
            )
        ]

        if self.props.enable_api_gateway:
            metrics.extend([
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="Count",
                    dimensions_map={
                        "ApiName": self.api.rest_api_name
                    }
                ),
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="Latency",
                    dimensions_map={
                        "ApiName": self.api.rest_api_name
                    }
                )
            ])

        return metrics

    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass