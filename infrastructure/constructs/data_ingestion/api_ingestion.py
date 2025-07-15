"""
API Data Ingestion Construct for DevSecOps Platform.

This construct implements API Gateway → Lambda → S3 pattern with authentication,
rate limiting, request validation, and comprehensive error handling.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_iam as iam,
    aws_cognito as cognito,
    aws_wafv2 as wafv2,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
)
from constructs import Construct

from ..common.base import BaseConstruct
from ..common.types import ConstructProps


@dataclass
class ApiIngestionProps(ConstructProps):
    """Properties for API Ingestion Construct."""
    
    # API Gateway Configuration
    api_name: Optional[str] = None
    api_description: str = "Data ingestion API"
    enable_cors: bool = True
    cors_origins: List[str] = None
    
    # Authentication
    enable_authentication: bool = True
    auth_type: str = "cognito"  # cognito, iam, api_key
    create_user_pool: bool = True
    user_pool_name: Optional[str] = None
    
    # Rate Limiting
    enable_rate_limiting: bool = True
    throttle_rate_limit: int = 1000
    throttle_burst_limit: int = 2000
    
    # Request Validation
    enable_request_validation: bool = True
    request_schema: Dict[str, Any] = None
    max_request_size_mb: int = 10
    
    # Lambda Configuration
    lambda_memory_size: int = 1024
    lambda_timeout_minutes: int = 5
    lambda_runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9
    
    # S3 Configuration
    output_bucket_name: Optional[str] = None
    enable_data_partitioning: bool = True
    partition_keys: List[str] = None
    
    # WAF Configuration
    enable_waf: bool = True
    enable_geo_blocking: bool = False
    blocked_countries: List[str] = None
    
    # Monitoring
    enable_detailed_monitoring: bool = True
    enable_x_ray_tracing: bool = True


class ApiIngestionConstruct(BaseConstruct):
    """
    API Data Ingestion Construct.
    
    Implements a comprehensive API-based data ingestion pipeline with:
    - API Gateway with authentication and rate limiting
    - Lambda function for data processing and validation
    - S3 for data storage with partitioning
    - Cognito User Pool for authentication
    - WAF for security protection
    - Request validation and error handling
    - Comprehensive monitoring and alerting
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        props: ApiIngestionProps,
        **kwargs
    ) -> None:
        """
        Initialize API Ingestion Construct.
        
        Args:
            scope: Parent construct
            construct_id: Unique identifier
            props: Construct properties
        """
        super().__init__(scope, construct_id, props, **kwargs)
        
        self.props = props
        
        # Create resources
        self._create_s3_bucket()
        self._create_lambda_function()
        self._create_authentication()
        self._create_api_gateway()
        self._create_waf_protection()
        self._create_monitoring()
        
        # Add outputs
        self._create_outputs()
    
    def _create_s3_bucket(self) -> None:
        """Create S3 bucket for API data storage."""
        
        self.data_bucket = s3.Bucket(
            self,
            "ApiDataBucket",
            bucket_name=self.props.output_bucket_name or self.get_resource_name("api-data"),
            versioning=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self._get_removal_policy(),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ApiDataLifecycle",
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
    
    def _create_lambda_function(self) -> None:
        """Create Lambda function for API data processing."""
        
        # Create IAM role for Lambda
        self.lambda_role = self.create_service_role(
            "ApiProcessorLambda",
            "lambda.amazonaws.com",
            managed_policies=[
                "service-role/AWSLambdaBasicExecutionRole"
            ],
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:PutObject",
                                "s3:PutObjectAcl"
                            ],
                            resources=[
                                f"{self.data_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                ),
                "KMSAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "kms:Decrypt",
                                "kms:GenerateDataKey"
                            ],
                            resources=[self.encryption_key.key_arn]
                        )
                    ]
                )
            }
        )
        
        # Create Lambda function
        self.api_processor = lambda_.Function(
            self,
            "ApiProcessor",
            function_name=self.get_resource_name("api-processor"),
            runtime=self.props.lambda_runtime,
            handler="api_processor.handler",
            code=lambda_.Code.from_asset("src/lambda/api_ingestion"),
            role=self.lambda_role,
            memory_size=self.props.lambda_memory_size,
            timeout=Duration.minutes(self.props.lambda_timeout_minutes),
            environment={
                "DATA_BUCKET": self.data_bucket.bucket_name,
                "ENABLE_PARTITIONING": str(self.props.enable_data_partitioning),
                "PARTITION_KEYS": json.dumps(self.props.partition_keys or ["year", "month", "day"]),
                "MAX_REQUEST_SIZE_MB": str(self.props.max_request_size_mb),
                "LOG_LEVEL": "INFO" if self.environment == "prod" else "DEBUG"
            },
            tracing=lambda_.Tracing.ACTIVE if self.props.enable_x_ray_tracing else lambda_.Tracing.DISABLED
        )
    
    def _create_authentication(self) -> None:
        """Create authentication resources."""
        
        if not self.props.enable_authentication:
            return
        
        if self.props.auth_type == "cognito" and self.props.create_user_pool:
            # Create Cognito User Pool
            self.user_pool = cognito.UserPool(
                self,
                "ApiUserPool",
                user_pool_name=self.props.user_pool_name or self.get_resource_name("api-users"),
                password_policy=cognito.PasswordPolicy(
                    min_length=12,
                    require_lowercase=True,
                    require_uppercase=True,
                    require_digits=True,
                    require_symbols=True
                ),
                mfa=cognito.Mfa.OPTIONAL,
                mfa_second_factor=cognito.MfaSecondFactor(
                    sms=True,
                    otp=True
                ),
                account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
                removal_policy=self._get_removal_policy()
            )
            
            # Create User Pool Client
            self.user_pool_client = cognito.UserPoolClient(
                self,
                "ApiUserPoolClient",
                user_pool=self.user_pool,
                user_pool_client_name=self.get_resource_name("api-client"),
                generate_secret=True,
                auth_flows=cognito.AuthFlow(
                    user_password=True,
                    user_srp=True
                ),
                o_auth=cognito.OAuthSettings(
                    flows=cognito.OAuthFlows(
                        authorization_code_grant=True,
                        client_credentials=True
                    ),
                    scopes=[
                        cognito.OAuthScope.OPENID,
                        cognito.OAuthScope.EMAIL,
                        cognito.OAuthScope.PROFILE
                    ]
                )
            )
            
            # Create User Pool Domain
            self.user_pool_domain = cognito.UserPoolDomain(
                self,
                "ApiUserPoolDomain",
                user_pool=self.user_pool,
                cognito_domain=cognito.CognitoDomainOptions(
                    domain_prefix=self.get_resource_name("api-auth")
                )
            )
    
    def _create_api_gateway(self) -> None:
        """Create API Gateway with authentication and validation."""
        
        # Create API Gateway
        self.api = apigateway.RestApi(
            self,
            "DataIngestionApi",
            rest_api_name=self.props.api_name or self.get_resource_name("api"),
            description=self.props.api_description,
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            cloud_watch_role=True,
            deploy_options=apigateway.StageOptions(
                stage_name=self.environment,
                throttling_rate_limit=self.props.throttle_rate_limit,
                throttling_burst_limit=self.props.throttle_burst_limit,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=self.props.enable_detailed_monitoring,
                metrics_enabled=True,
                tracing_enabled=self.props.enable_x_ray_tracing
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=self.props.cors_origins or ["*"],
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ) if self.props.enable_cors else None
        )
        
        # Create authorizer if authentication is enabled
        authorizer = None
        if self.props.enable_authentication and self.props.auth_type == "cognito":
            authorizer = apigateway.CognitoUserPoolsAuthorizer(
                self,
                "ApiAuthorizer",
                cognito_user_pools=[self.user_pool],
                authorizer_name=self.get_resource_name("authorizer")
            )
        
        # Create request validator
        request_validator = None
        if self.props.enable_request_validation:
            request_validator = apigateway.RequestValidator(
                self,
                "RequestValidator",
                rest_api=self.api,
                validate_request_body=True,
                validate_request_parameters=True
            )
        
        # Create request model
        request_model = None
        if self.props.request_schema:
            request_model = apigateway.Model(
                self,
                "RequestModel",
                rest_api=self.api,
                content_type="application/json",
                schema=apigateway.JsonSchema(
                    schema=apigateway.JsonSchemaVersion.DRAFT4,
                    type=apigateway.JsonSchemaType.OBJECT,
                    properties=self.props.request_schema
                )
            )
        
        # Create Lambda integration
        lambda_integration = apigateway.LambdaIntegration(
            self.api_processor,
            request_templates={
                "application/json": json.dumps({
                    "body": "$input.body",
                    "headers": "$input.params().header",
                    "queryStringParameters": "$input.params().querystring",
                    "pathParameters": "$input.params().path",
                    "requestContext": {
                        "requestId": "$context.requestId",
                        "sourceIp": "$context.identity.sourceIp",
                        "userAgent": "$context.identity.userAgent"
                    }
                })
            }
        )
        
        # Create API resources and methods
        data_resource = self.api.root.add_resource("data")
        
        # POST method for data ingestion
        data_resource.add_method(
            "POST",
            lambda_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO if authorizer else apigateway.AuthorizationType.NONE,
            authorizer=authorizer,
            request_validator=request_validator,
            request_models={"application/json": request_model} if request_model else None,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_models={
                        "application/json": apigateway.Model.EMPTY_MODEL
                    }
                ),
                apigateway.MethodResponse(
                    status_code="400",
                    response_models={
                        "application/json": apigateway.Model.ERROR_MODEL
                    }
                ),
                apigateway.MethodResponse(
                    status_code="500",
                    response_models={
                        "application/json": apigateway.Model.ERROR_MODEL
                    }
                )
            ]
        )
        
        # GET method for health check
        data_resource.add_method(
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
    
    def _create_waf_protection(self) -> None:
        """Create WAF protection for API Gateway."""
        
        if not self.props.enable_waf:
            return
        
        # Create WAF rules
        rules = []
        
        # Rate limiting rule
        rules.append(
            wafv2.CfnWebACL.RuleProperty(
                name="RateLimitRule",
                priority=1,
                action=wafv2.CfnWebACL.RuleActionProperty(
                    block={}
                ),
                statement=wafv2.CfnWebACL.StatementProperty(
                    rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                        limit=self.props.throttle_rate_limit,
                        aggregate_key_type="IP"
                    )
                ),
                visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                    sampled_requests_enabled=True,
                    cloud_watch_metrics_enabled=True,
                    metric_name="RateLimitRule"
                )
            )
        )
        
        # AWS Managed Core Rule Set
        rules.append(
            wafv2.CfnWebACL.RuleProperty(
                name="AWSManagedRulesCommonRuleSet",
                priority=2,
                override_action=wafv2.CfnWebACL.OverrideActionProperty(
                    none={}
                ),
                statement=wafv2.CfnWebACL.StatementProperty(
                    managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                        vendor_name="AWS",
                        name="AWSManagedRulesCommonRuleSet"
                    )
                ),
                visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                    sampled_requests_enabled=True,
                    cloud_watch_metrics_enabled=True,
                    metric_name="CommonRuleSetMetric"
                )
            )
        )
        
        # Geo blocking rule (if enabled)
        if self.props.enable_geo_blocking and self.props.blocked_countries:
            rules.append(
                wafv2.CfnWebACL.RuleProperty(
                    name="GeoBlockingRule",
                    priority=3,
                    action=wafv2.CfnWebACL.RuleActionProperty(
                        block={}
                    ),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        geo_match_statement=wafv2.CfnWebACL.GeoMatchStatementProperty(
                            country_codes=self.props.blocked_countries
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="GeoBlockingRule"
                    )
                )
            )
        
        # Create WAF Web ACL
        self.web_acl = wafv2.CfnWebACL(
            self,
            "ApiWebACL",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(
                allow={}
            ),
            rules=rules,
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name="ApiWebACL"
            )
        )
        
        # Associate WAF with API Gateway
        wafv2.CfnWebACLAssociation(
            self,
            "ApiWebACLAssociation",
            resource_arn=f"arn:aws:apigateway:{self.region}::/restapis/{self.api.rest_api_id}/stages/{self.environment}",
            web_acl_arn=self.web_acl.attr_arn
        )
    
    def _create_monitoring(self) -> None:
        """Create monitoring and alerting."""
        
        # Create custom metrics
        self.api_requests_metric = cloudwatch.Metric(
            namespace=f"{self.project_name}/ApiIngestion",
            metric_name="ApiRequests",
            dimensions_map={
                "Environment": self.environment,
                "ApiName": self.api.rest_api_name
            }
        )
        
        # Create alarms
        self.create_alarm(
            "HighApiErrorRate",
            cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="4XXError",
                dimensions_map={"ApiName": self.api.rest_api_name}
            ),
            threshold=10,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High 4XX error rate in API"
        )
        
        self.create_alarm(
            "HighApiLatency",
            cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Latency",
                dimensions_map={"ApiName": self.api.rest_api_name}
            ),
            threshold=5000,  # 5 seconds
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            description="High latency in API responses"
        )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        self.add_output(
            "ApiUrl",
            self.api.url,
            "URL of the data ingestion API"
        )
        
        self.add_output(
            "ApiId",
            self.api.rest_api_id,
            "ID of the API Gateway"
        )
        
        self.add_output(
            "DataBucketName",
            self.data_bucket.bucket_name,
            "Name of the data storage bucket"
        )
        
        if self.props.enable_authentication and hasattr(self, 'user_pool'):
            self.add_output(
                "UserPoolId",
                self.user_pool.user_pool_id,
                "ID of the Cognito User Pool"
            )
            
            self.add_output(
                "UserPoolClientId",
                self.user_pool_client.user_pool_client_id,
                "ID of the Cognito User Pool Client"
            )
    
    def _setup_monitoring_metrics(self) -> List[cloudwatch.Metric]:
        """Set up construct-specific monitoring metrics."""
        return [
            self.api_requests_metric,
            cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Count",
                dimensions_map={"ApiName": self.api.rest_api_name}
            ),
            cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions_map={"FunctionName": self.api_processor.function_name}
            )
        ]
    
    def _create_resources(self) -> None:
        """Create construct-specific resources."""
        # Resources are created in the constructor
        pass
