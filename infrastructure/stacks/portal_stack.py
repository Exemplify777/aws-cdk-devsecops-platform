"""
Portal Stack
Implements self-service portal infrastructure with web interface and API
"""

from typing import Dict, Any
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as route53,
    aws_certificatemanager as acm,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_logs as logs,
    CfnOutput,
    RemovalPolicy,
    Duration,
)


class PortalStack(Stack):
    """Portal stack for self-service web interface."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_config: Dict[str, Any],
        vpc: ec2.Vpc,
        security_groups: Dict[str, ec2.SecurityGroup],
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_config = env_config
        self.environment_name = env_config["environment_name"]
        self.vpc = vpc
        self.security_groups = security_groups
        
        # Create portal components
        self._create_frontend_hosting()
        self._create_api_gateway()
        self._create_backend_services()
        self._create_load_balancer()
        self._create_outputs()
    
    def _create_frontend_hosting(self) -> None:
        """Create S3 bucket and CloudFront for frontend hosting."""
        # S3 bucket for static website hosting
        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"{self.env_config['project_name']}-portal-frontend-{self.environment_name}-{self.account}",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        
        # Origin Access Identity for CloudFront
        self.origin_access_identity = cloudfront.OriginAccessIdentity(
            self,
            "OriginAccessIdentity",
            comment=f"OAI for portal frontend ({self.environment_name})",
        )
        
        # Grant CloudFront access to S3 bucket
        self.frontend_bucket.grant_read(self.origin_access_identity)
        
        # CloudFront distribution
        self.cloudfront_distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    self.frontend_bucket,
                    origin_access_identity=self.origin_access_identity,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        f"{self.api_gateway.rest_api_id}.execute-api.{self.region}.amazonaws.com",
                        origin_path=f"/{self.environment_name}",
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
                ),
            },
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5),
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        )
    
    def _create_api_gateway(self) -> None:
        """Create API Gateway for backend API."""
        # Create API Gateway
        self.api_gateway = apigateway.RestApi(
            self,
            "PortalAPI",
            rest_api_name=f"portal-api-{self.environment_name}",
            description=f"Portal API for DevSecOps platform ({self.environment_name})",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"],
            ),
            deploy_options=apigateway.StageOptions(
                stage_name=self.environment_name,
                throttling_rate_limit=self.env_config.get("api_throttle_rate", 1000),
                throttling_burst_limit=self.env_config.get("api_throttle_burst", 2000),
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
            ),
        )
        
        # Create API resources and methods
        self._create_api_resources()
    
    def _create_api_resources(self) -> None:
        """Create API Gateway resources and methods."""
        # Projects resource
        projects_resource = self.api_gateway.root.add_resource("projects")
        
        # Projects Lambda function
        self.projects_lambda = lambda_.Function(
            self,
            "ProjectsAPI",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    '''Projects API Lambda function'''
    try:
        http_method = event.get('httpMethod')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        
        logger.info(f"Processing {http_method} request")
        
        if http_method == 'GET':
            # List projects
            projects = [
                {
                    'id': 'proj-001',
                    'name': 'Sample Data Pipeline',
                    'type': 'etl',
                    'status': 'active',
                    'created_at': '2024-01-01T00:00:00Z',
                    'owner': 'data-team'
                },
                {
                    'id': 'proj-002',
                    'name': 'ML Training Pipeline',
                    'type': 'ml-workflow',
                    'status': 'active',
                    'created_at': '2024-01-02T00:00:00Z',
                    'owner': 'ml-team'
                }
            ]
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'projects': projects,
                    'total': len(projects)
                })
            }
        
        elif http_method == 'POST':
            # Create new project
            project_id = f"proj-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            new_project = {
                'id': project_id,
                'name': body.get('name', 'Untitled Project'),
                'type': body.get('type', 'etl'),
                'status': 'creating',
                'created_at': datetime.now().isoformat() + 'Z',
                'owner': body.get('owner', 'unknown')
            }
            
            return {
                'statusCode': 201,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(new_project)
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }
            """),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "ENVIRONMENT": self.environment_name,
            },
        )
        
        # Add Lambda integration to API Gateway
        projects_integration = apigateway.LambdaIntegration(
            self.projects_lambda,
            request_templates={"application/json": '{"statusCode": "200"}'},
        )
        
        projects_resource.add_method("GET", projects_integration)
        projects_resource.add_method("POST", projects_integration)
        
        # Deployments resource
        deployments_resource = self.api_gateway.root.add_resource("deployments")
        
        # Deployments Lambda function
        self.deployments_lambda = lambda_.Function(
            self,
            "DeploymentsAPI",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    '''Deployments API Lambda function'''
    try:
        http_method = event.get('httpMethod')
        
        if http_method == 'GET':
            # List deployments
            deployments = [
                {
                    'id': 'deploy-001',
                    'project_id': 'proj-001',
                    'environment': 'dev',
                    'status': 'success',
                    'started_at': '2024-01-01T10:00:00Z',
                    'completed_at': '2024-01-01T10:05:00Z',
                    'duration': 300
                },
                {
                    'id': 'deploy-002',
                    'project_id': 'proj-002',
                    'environment': 'staging',
                    'status': 'in_progress',
                    'started_at': '2024-01-01T11:00:00Z',
                    'completed_at': None,
                    'duration': None
                }
            ]
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'deployments': deployments,
                    'total': len(deployments)
                })
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }
            """),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "ENVIRONMENT": self.environment_name,
            },
        )
        
        # Add Lambda integration to API Gateway
        deployments_integration = apigateway.LambdaIntegration(
            self.deployments_lambda,
            request_templates={"application/json": '{"statusCode": "200"}'},
        )
        
        deployments_resource.add_method("GET", deployments_integration)

    def _create_backend_services(self) -> None:
        """Create ECS services for backend applications."""
        # Create ECS cluster for portal services
        self.portal_cluster = ecs.Cluster(
            self,
            "PortalCluster",
            cluster_name=f"portal-{self.environment_name}",
            vpc=self.vpc,
            container_insights=True,
        )

        # Create task definition for portal backend
        self.portal_task = ecs.FargateTaskDefinition(
            self,
            "PortalTask",
            family=f"portal-backend-{self.environment_name}",
            cpu=self.env_config.get("container_cpu", 256),
            memory_limit_mib=self.env_config.get("container_memory", 512),
        )

        # Add container to task definition
        self.portal_container = self.portal_task.add_container(
            "PortalContainer",
            image=ecs.ContainerImage.from_registry("nginx:alpine"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="portal-backend",
                log_retention=logs.RetentionDays.ONE_MONTH,
            ),
            port_mappings=[
                ecs.PortMapping(container_port=80, protocol=ecs.Protocol.TCP)
            ],
            environment={
                "ENVIRONMENT": self.environment_name,
                "API_GATEWAY_URL": self.api_gateway.url,
            },
        )

        # Create ECS service
        self.portal_service = ecs.FargateService(
            self,
            "PortalService",
            cluster=self.portal_cluster,
            task_definition=self.portal_task,
            desired_count=self.env_config.get("desired_capacity", 1),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[self.security_groups["ecs"]],
            enable_logging=True,
        )

    def _create_load_balancer(self) -> None:
        """Create Application Load Balancer for portal services."""
        # Create ALB
        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "PortalALB",
            vpc=self.vpc,
            internet_facing=True,
            security_group=self.security_groups["web"],
        )

        # Create target group
        self.target_group = elbv2.ApplicationTargetGroup(
            self,
            "PortalTargetGroup",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            vpc=self.vpc,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                enabled=True,
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                path="/health",
                protocol=elbv2.Protocol.HTTP,
                timeout=Duration.seconds(5),
                unhealthy_threshold_count=2,
            ),
        )

        # Add ECS service to target group
        self.portal_service.attach_to_application_target_group(self.target_group)

        # Create ALB listener
        self.alb_listener = self.alb.add_listener(
            "PortalListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_target_groups=[self.target_group],
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{self.cloudfront_distribution.distribution_domain_name}",
            description="CloudFront Distribution URL",
            export_name=f"{self.stack_name}-CloudFrontURL"
        )

        CfnOutput(
            self,
            "APIGatewayURL",
            value=self.api_gateway.url,
            description="API Gateway URL",
            export_name=f"{self.stack_name}-APIGatewayURL"
        )

        CfnOutput(
            self,
            "LoadBalancerDNS",
            value=self.alb.load_balancer_dns_name,
            description="Application Load Balancer DNS Name",
            export_name=f"{self.stack_name}-LoadBalancerDNS"
        )

        CfnOutput(
            self,
            "FrontendBucketName",
            value=self.frontend_bucket.bucket_name,
            description="Frontend S3 Bucket Name",
            export_name=f"{self.stack_name}-FrontendBucketName"
        )
