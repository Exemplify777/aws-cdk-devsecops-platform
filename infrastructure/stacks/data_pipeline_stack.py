"""
Data Pipeline Stack
Implements data processing infrastructure including Lambda, ECS, Glue, and data storage
"""

from typing import Dict, Any, List
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_glue as glue,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_s3 as s3,
    aws_iam as iam,
    aws_rds as rds,
    aws_secretsmanager as secrets,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    CfnOutput,
    RemovalPolicy,
    Duration,
)


class DataPipelineStack(Stack):
    """Data pipeline stack for ETL/ELT processing."""
    
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
        
        # Create data pipeline components
        self._create_database()
        self._create_glue_resources()
        self._create_lambda_functions()
        self._create_ecs_cluster()
        self._create_step_functions()
        self._create_event_rules()
        self._create_outputs()
    
    def _create_database(self) -> None:
        """Create RDS database for metadata and configuration."""
        # Create database subnet group
        self.db_subnet_group = rds.SubnetGroup(
            self,
            "DatabaseSubnetGroup",
            description="Subnet group for RDS database",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
        )
        
        # Create database credentials secret
        self.db_secret = secrets.Secret(
            self,
            "DatabaseSecret",
            description="Database credentials",
            generate_secret_string=secrets.SecretStringGenerator(
                secret_string_template='{"username": "admin"}',
                generate_string_key="password",
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                password_length=32,
            ),
        )
        
        # Create RDS instance
        self.database = rds.DatabaseInstance(
            self,
            "Database",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_4
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.MICRO if self.environment_name == "dev" else ec2.InstanceSize.SMALL
            ),
            vpc=self.vpc,
            subnet_group=self.db_subnet_group,
            security_groups=[self.security_groups["database"]],
            credentials=rds.Credentials.from_secret(self.db_secret),
            allocated_storage=self.env_config.get("db_allocated_storage", 20),
            storage_encrypted=True,
            backup_retention=Duration.days(self.env_config.get("db_backup_retention", 7)),
            deletion_protection=self.env_config.get("enable_deletion_protection", False),
            removal_policy=RemovalPolicy.RETAIN if self.env_config.get("enable_deletion_protection") else RemovalPolicy.DESTROY,
            auto_minor_version_upgrade=True,
            multi_az=self.environment_name == "prod",
            monitoring_interval=Duration.seconds(60) if self.environment_name != "dev" else None,
        )
    
    def _create_glue_resources(self) -> None:
        """Create AWS Glue resources for data cataloging and ETL."""
        # Create Glue database
        self.glue_database = glue.CfnDatabase(
            self,
            "GlueDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=f"devsecops_data_catalog_{self.environment_name}",
                description=f"Data catalog for DevSecOps platform ({self.environment_name})",
            ),
        )
        
        # Create Glue service role
        self.glue_role = iam.Role(
            self,
            "GlueServiceRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
            ],
            inline_policies={
                "GlueS3Access": iam.PolicyDocument(
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
                                f"arn:aws:s3:::{self.env_config['project_name']}-data-lake-{self.environment_name}-{self.account}",
                                f"arn:aws:s3:::{self.env_config['project_name']}-data-lake-{self.environment_name}-{self.account}/*",
                            ]
                        )
                    ]
                )
            }
        )
        
        # Create Glue crawler for data discovery
        self.glue_crawler = glue.CfnCrawler(
            self,
            "DataLakeCrawler",
            name=f"data-lake-crawler-{self.environment_name}",
            role=self.glue_role.role_arn,
            database_name=self.glue_database.ref,
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{self.env_config['project_name']}-data-lake-{self.environment_name}-{self.account}/raw/"
                    )
                ]
            ),
            schedule=glue.CfnCrawler.ScheduleProperty(
                schedule_expression="cron(0 2 * * ? *)"  # Daily at 2 AM
            ),
        )
    
    def _create_lambda_functions(self) -> None:
        """Create Lambda functions for data processing."""
        # Data validation Lambda
        self.data_validator_lambda = lambda_.Function(
            self,
            "DataValidator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    '''Data validation Lambda function'''
    logger.info(f"Processing event: {json.dumps(event)}")
    
    # Basic data validation logic
    try:
        # Extract S3 object information
        bucket = event.get('bucket')
        key = event.get('key')
        
        if not bucket or not key:
            raise ValueError("Missing bucket or key in event")
        
        # Perform validation (placeholder)
        validation_result = {
            'status': 'success',
            'bucket': bucket,
            'key': key,
            'timestamp': context.aws_request_id,
            'validation_checks': {
                'file_exists': True,
                'file_size_valid': True,
                'schema_valid': True
            }
        }
        
        logger.info(f"Validation completed: {validation_result}")
        return validation_result
        
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': context.aws_request_id
        }
            """),
            timeout=Duration.minutes(5),
            memory_size=256,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[self.security_groups["lambda"]],
            environment={
                "ENVIRONMENT": self.environment_name,
                "DATABASE_SECRET_ARN": self.db_secret.secret_arn,
            },
        )
        
        # Grant Lambda access to secrets
        self.db_secret.grant_read(self.data_validator_lambda)
        
        # Data transformation Lambda
        self.data_transformer_lambda = lambda_.Function(
            self,
            "DataTransformer",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    '''Data transformation Lambda function'''
    logger.info(f"Processing event: {json.dumps(event)}")
    
    try:
        # Extract transformation parameters
        source_bucket = event.get('source_bucket')
        source_key = event.get('source_key')
        target_bucket = event.get('target_bucket')
        target_key = event.get('target_key')
        
        # Perform transformation (placeholder)
        transformation_result = {
            'status': 'success',
            'source': f"s3://{source_bucket}/{source_key}",
            'target': f"s3://{target_bucket}/{target_key}",
            'timestamp': context.aws_request_id,
            'records_processed': 1000,
            'transformation_type': 'csv_to_parquet'
        }
        
        logger.info(f"Transformation completed: {transformation_result}")
        return transformation_result
        
    except Exception as e:
        logger.error(f"Transformation failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': context.aws_request_id
        }
            """),
            timeout=Duration.minutes(15),
            memory_size=512,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[self.security_groups["lambda"]],
            environment={
                "ENVIRONMENT": self.environment_name,
                "DATABASE_SECRET_ARN": self.db_secret.secret_arn,
            },
        )
        
        # Grant Lambda access to secrets
        self.db_secret.grant_read(self.data_transformer_lambda)

    def _create_ecs_cluster(self) -> None:
        """Create ECS cluster for containerized data processing."""
        # Create ECS cluster
        self.ecs_cluster = ecs.Cluster(
            self,
            "DataProcessingCluster",
            cluster_name=f"data-processing-{self.environment_name}",
            vpc=self.vpc,
            container_insights=True,
        )

        # Create task definition for data processing
        self.data_processing_task = ecs.FargateTaskDefinition(
            self,
            "DataProcessingTask",
            family=f"data-processing-{self.environment_name}",
            cpu=self.env_config.get("container_cpu", 256),
            memory_limit_mib=self.env_config.get("container_memory", 512),
        )

        # Add container to task definition
        self.data_processing_container = self.data_processing_task.add_container(
            "DataProcessingContainer",
            image=ecs.ContainerImage.from_registry("python:3.11-slim"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="data-processing",
                log_retention=logs.RetentionDays.ONE_MONTH,
            ),
            environment={
                "ENVIRONMENT": self.environment_name,
                "AWS_DEFAULT_REGION": self.region,
            },
            secrets={
                "DATABASE_URL": ecs.Secret.from_secrets_manager(self.db_secret, "password"),
            },
        )

        # Create ECS service
        self.data_processing_service = ecs.FargateService(
            self,
            "DataProcessingService",
            cluster=self.ecs_cluster,
            task_definition=self.data_processing_task,
            desired_count=self.env_config.get("desired_capacity", 1),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[self.security_groups["ecs"]],
            enable_logging=True,
        )

    def _create_step_functions(self) -> None:
        """Create Step Functions for data pipeline orchestration."""
        # Define the data processing workflow
        validate_task = sfn_tasks.LambdaInvoke(
            self,
            "ValidateData",
            lambda_function=self.data_validator_lambda,
            output_path="$.Payload",
        )

        transform_task = sfn_tasks.LambdaInvoke(
            self,
            "TransformData",
            lambda_function=self.data_transformer_lambda,
            output_path="$.Payload",
        )

        # Define success and failure states
        success_state = sfn.Succeed(self, "ProcessingSucceeded")
        failure_state = sfn.Fail(self, "ProcessingFailed")

        # Create choice state for validation result
        validation_choice = sfn.Choice(self, "ValidationChoice")
        validation_choice.when(
            sfn.Condition.string_equals("$.status", "success"),
            transform_task.next(success_state)
        ).otherwise(failure_state)

        # Define the workflow
        definition = validate_task.next(validation_choice)

        # Create the state machine
        self.data_pipeline_state_machine = sfn.StateMachine(
            self,
            "DataPipelineStateMachine",
            state_machine_name=f"data-pipeline-{self.environment_name}",
            definition=definition,
            timeout=Duration.hours(2),
        )

    def _create_event_rules(self) -> None:
        """Create EventBridge rules for triggering data pipelines."""
        # S3 event rule for new data files
        self.s3_event_rule = events.Rule(
            self,
            "S3DataFileRule",
            rule_name=f"s3-data-file-{self.environment_name}",
            description="Trigger data pipeline when new files are uploaded to S3",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {
                        "name": [f"{self.env_config['project_name']}-data-lake-{self.environment_name}-{self.account}"]
                    },
                    "object": {
                        "key": [{"prefix": "raw/"}]
                    }
                }
            ),
        )

        # Add Step Functions as target
        self.s3_event_rule.add_target(
            targets.SfnStateMachine(
                self.data_pipeline_state_machine,
                input=events.RuleTargetInput.from_object({
                    "bucket": events.EventField.from_path("$.detail.bucket.name"),
                    "key": events.EventField.from_path("$.detail.object.key"),
                    "event_time": events.EventField.from_path("$.time"),
                })
            )
        )

        # Scheduled rule for daily processing
        self.daily_processing_rule = events.Rule(
            self,
            "DailyProcessingRule",
            rule_name=f"daily-processing-{self.environment_name}",
            description="Daily data processing schedule",
            schedule=events.Schedule.cron(hour="2", minute="0"),  # 2 AM daily
        )

        # Add Step Functions as target for scheduled processing
        self.daily_processing_rule.add_target(
            targets.SfnStateMachine(
                self.data_pipeline_state_machine,
                input=events.RuleTargetInput.from_object({
                    "trigger_type": "scheduled",
                    "schedule": "daily",
                    "timestamp": events.EventField.from_path("$.time"),
                })
            )
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        CfnOutput(
            self,
            "DatabaseEndpoint",
            value=self.database.instance_endpoint.hostname,
            description="RDS Database Endpoint",
            export_name=f"{self.stack_name}-DatabaseEndpoint"
        )

        CfnOutput(
            self,
            "DatabaseSecretArn",
            value=self.db_secret.secret_arn,
            description="Database Secret ARN",
            export_name=f"{self.stack_name}-DatabaseSecretArn"
        )

        CfnOutput(
            self,
            "ECSClusterName",
            value=self.ecs_cluster.cluster_name,
            description="ECS Cluster Name",
            export_name=f"{self.stack_name}-ECSClusterName"
        )

        CfnOutput(
            self,
            "StateMachineArn",
            value=self.data_pipeline_state_machine.state_machine_arn,
            description="Data Pipeline State Machine ARN",
            export_name=f"{self.stack_name}-StateMachineArn"
        )

        CfnOutput(
            self,
            "GlueDatabaseName",
            value=self.glue_database.ref,
            description="Glue Database Name",
            export_name=f"{self.stack_name}-GlueDatabaseName"
        )
