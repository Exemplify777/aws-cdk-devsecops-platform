"""
Bedrock Construct for DevSecOps Platform.

This construct implements Amazon Bedrock with enterprise-grade configurations,
model access, guardrails, and operational best practices.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    aws_s3 as s3,
    aws_kms as kms,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class BedrockConstructProps(ConstructProps):
    """Properties for Bedrock Construct."""
    
    # Model Configuration
    foundation_models: List[str] = None  # List of model IDs to enable
    enable_anthropic_claude: bool = True
    enable_amazon_titan: bool = True
    enable_ai21_jurassic: bool = False
    enable_cohere_command: bool = False
    enable_meta_llama: bool = False
    
    # Guardrails Configuration
    enable_guardrails: bool = True
    content_filters: List[str] = None  # HATE, INSULTS, SEXUAL, VIOLENCE, MISCONDUCT, PROMPT_ATTACK
    topic_filters: List[Dict[str, Any]] = None
    word_filters: List[str] = None
    pii_filters: List[str] = None  # NAME, EMAIL, PHONE, etc.
    
    # API Configuration
    enable_api_gateway: bool = True
    api_name: Optional[str] = None
    enable_api_key: bool = True
    throttle_rate_limit: int = 100
    throttle_burst_limit: int = 200
    
    # Lambda Configuration
    lambda_memory_size: int = 1024
    lambda_timeout_minutes: int = 5
    lambda_runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9
    
    # Logging Configuration
    enable_model_invocation_logging: bool = True
    log_retention_days: int = 30
    
    # Security Configuration
    enable_vpc_endpoint: bool = False
    vpc_id: Optional[str] = None
    subnet_ids: List[str] = None
    
    # Cost Management
    enable_cost_monitoring: bool = True
    monthly_budget_limit: float = 1000.0  # USD
    
    # Fine-tuning Configuration
    enable_fine_tuning: bool = False
    training_data_bucket: Optional[str] = None
    
    # Knowledge Base Configuration
    enable_knowledge_base: bool = False
    knowledge_base_name: Optional[str] = None
    vector_store_type: str = "opensearch"  # opensearch, pinecone, redis


class BedrockConstruct(BaseConstruct):
    """
    Bedrock Construct.
    
    Implements a comprehensive Amazon Bedrock setup with:
    - Foundation model access and management
    - Guardrails for responsible AI
    - API Gateway integration for external access
    - Lambda functions for model invocation
    - Comprehensive logging and monitoring
    - Cost management and budgets
    - Fine-tuning capabilities
    - Knowledge base integration
    - VPC endpoint for secure access
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: BedrockConstructProps,
        **kwargs
    ) -> None:
        """
        Initialize Bedrock Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Set defaults
        if self.props.foundation_models is None:
            self.props.foundation_models = []
            if self.props.enable_anthropic_claude:
                self.props.foundation_models.extend([
                    "anthropic.claude-3-sonnet-20240229-v1:0",
                    "anthropic.claude-3-haiku-20240307-v1:0"
                ])
            if self.props.enable_amazon_titan:
                self.props.foundation_models.extend([
                    "amazon.titan-text-express-v1",
                    "amazon.titan-embed-text-v1"
                ])
        
        if self.props.content_filters is None:
            self.props.content_filters = ["HATE", "INSULTS", "SEXUAL", "VIOLENCE"]
        
        # Create resources
        self._create_guardrails()
        self._create_lambda_functions()
        self._create_api_gateway()
        self._create_knowledge_base()
        self._create_vpc_endpoint()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_guardrails(self) -> None:
        """Create Bedrock guardrails."""
        
        if not self.props.enable_guardrails:
            return
        
        # Create content policy
        content_policy_config = []
        for filter_type in self.props.content_filters:
            content_policy_config.append(
                bedrock.CfnGuardrail.ContentFilterConfigProperty(
                    type=filter_type,
                    input_strength="HIGH",
                    output_strength="HIGH"
                )
            )
        
        # Create topic policy
        topic_policy_config = []
        if self.props.topic_filters:
            for topic_filter in self.props.topic_filters:
                topic_policy_config.append(
                    bedrock.CfnGuardrail.TopicConfigProperty(
                        name=topic_filter["name"],
                        definition=topic_filter["definition"],
                        examples=topic_filter.get("examples", []),
                        type="DENY"
                    )
                )
        
        # Create word policy
        word_policy_config = None
        if self.props.word_filters:
            word_policy_config = bedrock.CfnGuardrail.WordPolicyConfigProperty(
                words_config=[
                    bedrock.CfnGuardrail.WordConfigProperty(text=word)
                    for word in self.props.word_filters
                ]
            )
        
        # Create sensitive information policy
        pii_policy_config = []
        if self.props.pii_filters:
            for pii_type in self.props.pii_filters:
                pii_policy_config.append(
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type=pii_type,
                        action="BLOCK"
                    )
                )
        
        # Create guardrail
        self.guardrail = bedrock.CfnGuardrail(
            self,
            "BedrockGuardrail",
            name=self.get_resource_name("guardrail"),
            description=f"Guardrail for {self.project_name} Bedrock applications",
            blocked_input_messaging="I cannot process this request due to content policy violations.",
            blocked_outputs_messaging="I cannot provide this response due to content policy violations.",
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=content_policy_config
            ) if content_policy_config else None,
            topic_policy_config=bedrock.CfnGuardrail.TopicPolicyConfigProperty(
                topics_config=topic_policy_config
            ) if topic_policy_config else None,
            word_policy_config=word_policy_config,
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=pii_policy_config
            ) if pii_policy_config else None,
            tags=[
                {
                    "key": "Environment",
                    "value": self.environment
                },
                {
                    "key": "Project",
                    "value": self.project_name
                }
            ]
        )
        
        # Create guardrail version
        self.guardrail_version = bedrock.CfnGuardrailVersion(
            self,
            "GuardrailVersion",
            guardrail_identifier=self.guardrail.attr_guardrail_id,
            description="Initial version of the guardrail"
        )
    
    def _create_lambda_functions(self) -> None:
        """Create Lambda functions for Bedrock integration."""
        
        # Create IAM role for Lambda
        self.lambda_role = self.create_service_role(
            "BedrockLambdaRole",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaBasicExecutionRole"
            ],
            inline_policies={
                "BedrockAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream"
                            ],
                            resources=[
                                f"arn:aws:bedrock:{self.region}::foundation-model/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock:ApplyGuardrail"
                            ],
                            resources=[
                                self.guardrail.attr_guardrail_arn
                            ] if hasattr(self, 'guardrail') else ["*"]
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
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/*"
                            ]
                        )
                    ]
                )
            }
        )
        
        # Create text generation Lambda
        self.text_generation_lambda = lambda_.Function(
            self,
            "TextGenerationLambda",
            function_name=self.get_resource_name("text-generation"),
            runtime=self.props.lambda_runtime,
            handler="text_generation.handler",
            code=lambda_.Code.from_asset("src/lambda/bedrock"),
            role=self.lambda_role,
            memory_size=self.props.lambda_memory_size,
            timeout=Duration.minutes(self.props.lambda_timeout_minutes),
            environment={
                "FOUNDATION_MODELS": json.dumps(self.props.foundation_models),
                "GUARDRAIL_ID": self.guardrail.attr_guardrail_id if hasattr(self, 'guardrail') else "",
                "GUARDRAIL_VERSION": self.guardrail_version.attr_version if hasattr(self, 'guardrail_version') else "",
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE
        )
        
        # Create embedding Lambda
        self.embedding_lambda = lambda_.Function(
            self,
            "EmbeddingLambda",
            function_name=self.get_resource_name("embedding"),
            runtime=self.props.lambda_runtime,
            handler="embedding.handler",
            code=lambda_.Code.from_asset("src/lambda/bedrock"),
            role=self.lambda_role,
            memory_size=self.props.lambda_memory_size,
            timeout=Duration.minutes(self.props.lambda_timeout_minutes),
            environment={
                "EMBEDDING_MODEL": "amazon.titan-embed-text-v1",
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE
        )
    
    def _create_api_gateway(self) -> None:
        """Create API Gateway for Bedrock access."""
        
        if not self.props.enable_api_gateway:
            return
        
        # Create API Gateway
        self.api = apigateway.RestApi(
            self,
            "BedrockApi",
            rest_api_name=self.props.api_name or self.get_resource_name("bedrock-api"),
            description=f"Bedrock API for {self.project_name}",
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name=self.environment,
                throttling_rate_limit=self.props.throttle_rate_limit,
                throttling_burst_limit=self.props.throttle_burst_limit,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )
        
        # Create API key if enabled
        if self.props.enable_api_key:
            self.api_key = apigateway.ApiKey(
                self,
                "BedrockApiKey",
                api_key_name=self.get_resource_name("bedrock-api-key"),
                description=f"API key for {self.project_name} Bedrock API"
            )
            
            # Create usage plan
            self.usage_plan = apigateway.UsagePlan(
                self,
                "BedrockUsagePlan",
                name=self.get_resource_name("bedrock-usage-plan"),
                description=f"Usage plan for {self.project_name} Bedrock API",
                throttle=apigateway.ThrottleSettings(
                    rate_limit=self.props.throttle_rate_limit,
                    burst_limit=self.props.throttle_burst_limit
                ),
                quota=apigateway.QuotaSettings(
                    limit=10000,
                    period=apigateway.Period.DAY
                ),
                api_stages=[
                    apigateway.UsagePlanPerApiStage(
                        api=self.api,
                        stage=self.api.deployment_stage
                    )
                ]
            )
            
            # Associate API key with usage plan
            self.usage_plan.add_api_key(self.api_key)
        
        # Create Lambda integrations
        text_integration = apigateway.LambdaIntegration(
            self.text_generation_lambda,
            request_templates={
                "application/json": json.dumps({
                    "body": "$input.body",
                    "headers": "$input.params().header",
                    "queryStringParameters": "$input.params().querystring"
                })
            }
        )
        
        embedding_integration = apigateway.LambdaIntegration(
            self.embedding_lambda,
            request_templates={
                "application/json": json.dumps({
                    "body": "$input.body",
                    "headers": "$input.params().header",
                    "queryStringParameters": "$input.params().querystring"
                })
            }
        )
        
        # Create API resources and methods
        text_resource = self.api.root.add_resource("generate")
        text_resource.add_method(
            "POST",
            text_integration,
            api_key_required=self.props.enable_api_key,
            method_responses=[
                apigateway.MethodResponse(status_code="200"),
                apigateway.MethodResponse(status_code="400"),
                apigateway.MethodResponse(status_code="500")
            ]
        )
        
        embedding_resource = self.api.root.add_resource("embed")
        embedding_resource.add_method(
            "POST",
            embedding_integration,
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
    
    def _create_knowledge_base(self) -> None:
        """Create Bedrock Knowledge Base."""
        
        if not self.props.enable_knowledge_base:
            return
        
        # Create S3 bucket for knowledge base data
        self.knowledge_base_bucket = s3.Bucket(
            self,
            "KnowledgeBaseBucket",
            bucket_name=self.get_resource_name("knowledge-base"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy()
        )
        
        # Create IAM role for Knowledge Base
        self.knowledge_base_role = self.create_service_role(
            "KnowledgeBaseRole",
            "bedrock.amazonaws.com",
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
                                self.knowledge_base_bucket.bucket_arn,
                                f"{self.knowledge_base_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                ),
                "BedrockAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock:InvokeModel"
                            ],
                            resources=[
                                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v1"
                            ]
                        )
                    ]
                )
            }
        )
        
        # Note: Bedrock Knowledge Base CDK support is limited
        # This would typically be created using custom resources or AWS CLI
        pass
    
    def _create_vpc_endpoint(self) -> None:
        """Create VPC endpoint for Bedrock."""
        
        if not self.props.enable_vpc_endpoint or not self.props.vpc_id:
            return
        
        # Get VPC
        vpc = ec2.Vpc.from_lookup(
            self,
            "BedrockVPC",
            vpc_id=self.props.vpc_id
        )
        
        # Create security group for VPC endpoint
        endpoint_sg = ec2.SecurityGroup(
            self,
            "BedrockEndpointSG",
            vpc=vpc,
            security_group_name=self.get_resource_name("bedrock-endpoint-sg"),
            description="Security group for Bedrock VPC endpoint",
            allow_all_outbound=False
        )
        
        endpoint_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="HTTPS access from VPC"
        )
        
        # Create VPC endpoint
        self.vpc_endpoint = vpc.add_interface_endpoint(
            "BedrockEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
            security_groups=[endpoint_sg],
            subnets=ec2.SubnetSelection(
                subnet_ids=self.props.subnet_ids
            ) if self.props.subnet_ids else None
        )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create CloudWatch log group for model invocations
        if self.props.enable_model_invocation_logging:
            self.model_invocation_log_group = logs.LogGroup(
                self,
                "ModelInvocationLogs",
                log_group_name=f"/aws/bedrock/{self.get_resource_name('model-invocations')}",
                retention=getattr(logs.RetentionDays, f"_{self.props.log_retention_days}_DAYS", logs.RetentionDays.ONE_MONTH),
                encryption_key=self.encryption_key,
                removal_policy=self._get_removal_policy()
            )
        
        # Create custom metrics
        self.model_invocations_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/Bedrock",
            metric_name="ModelInvocations",
            dimensions_map={
                "Environment": self.environment,
                "ModelId": "All"
            }
        )
        
        self.guardrail_blocks_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/Bedrock",
            metric_name="GuardrailBlocks",
            dimensions_map={
                "Environment": self.environment,
                "GuardrailId": self.guardrail.attr_guardrail_id if hasattr(self, 'guardrail') else "None"
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighModelInvocationErrors",
            cloudwatch.Metric(
                namespace="AWS/Bedrock",
                metric_name="InvocationErrors",
                statistic="Sum"
            ),
            threshold=10,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High number of Bedrock model invocation errors"
        )
        
        self.create_alarm(
            "HighGuardrailBlocks",
            self.guardrail_blocks_metric,
            threshold=50,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High number of guardrail blocks"
        )
        
        # Cost monitoring
        if self.props.enable_cost_monitoring:
            self.create_alarm(
                "HighBedrockCosts",
                cloudwatch.Metric(
                    namespace="AWS/Billing",
                    metric_name="EstimatedCharges",
                    dimensions_map={
                        "Currency": "USD",
                        "ServiceName": "Amazon Bedrock"
                    }
                ),
                threshold=self.props.monthly_budget_limit,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                description="High Bedrock costs detected"
            )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        if hasattr(self, 'guardrail'):
            self.add_output(
                "GuardrailId",
                self.guardrail.attr_guardrail_id,
                "ID of the Bedrock guardrail"
            )
            
            self.add_output(
                "GuardrailArn",
                self.guardrail.attr_guardrail_arn,
                "ARN of the Bedrock guardrail"
            )
        
        if self.props.enable_api_gateway:
            self.add_output(
                "ApiUrl",
                self.api.url,
                "URL of the Bedrock API"
            )
            
            self.add_output(
                "ApiId",
                self.api.rest_api_id,
                "ID of the Bedrock API Gateway"
            )
            
            if self.props.enable_api_key:
                self.add_output(
                    "ApiKeyId",
                    self.api_key.key_id,
                    "ID of the Bedrock API key"
                )
        
        self.add_output(
            "TextGenerationLambdaArn",
            self.text_generation_lambda.function_arn,
            "ARN of the text generation Lambda function"
        )
        
        self.add_output(
            "EmbeddingLambdaArn",
            self.embedding_lambda.function_arn,
            "ARN of the embedding Lambda function"
        )
        
        if hasattr(self, 'knowledge_base_bucket'):
            self.add_output(
                "KnowledgeBaseBucketName",
                self.knowledge_base_bucket.bucket_name,
                "Name of the knowledge base S3 bucket"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        return [
            self.model_invocations_metric,
            self.guardrail_blocks_metric,
            cloudwatch.Metric(
                namespace="AWS/Bedrock",
                metric_name="InvocationLatency",
                statistic="Average"
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions_map={
                    "FunctionName": self.text_generation_lambda.function_name
                }
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Duration",
                dimensions_map={
                    "FunctionName": self.text_generation_lambda.function_name
                }
            )
        ]
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
