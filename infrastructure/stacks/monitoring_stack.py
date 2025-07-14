"""
Monitoring Stack
Implements comprehensive monitoring and observability with CloudWatch, alarms, and dashboards
"""

from typing import Dict, Any, List
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_logs as logs,
    aws_lambda as lambda_,
    aws_ec2 as ec2,
    aws_iam as iam,
    CfnOutput,
    RemovalPolicy,
    Duration,
)


class MonitoringStack(Stack):
    """Monitoring stack for comprehensive observability."""
    
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
        
        # Create monitoring components
        self._create_sns_topics()
        self._create_cloudwatch_dashboards()
        self._create_alarms()
        self._create_log_insights_queries()
        self._create_custom_metrics_lambda()
        self._create_outputs()
    
    def _create_sns_topics(self) -> None:
        """Create SNS topics for notifications."""
        # Critical alerts topic
        self.critical_alerts_topic = sns.Topic(
            self,
            "CriticalAlerts",
            topic_name=f"critical-alerts-{self.environment_name}",
            display_name=f"Critical Alerts ({self.environment_name})",
        )
        
        # Warning alerts topic
        self.warning_alerts_topic = sns.Topic(
            self,
            "WarningAlerts",
            topic_name=f"warning-alerts-{self.environment_name}",
            display_name=f"Warning Alerts ({self.environment_name})",
        )
        
        # Add email subscription if configured
        if self.env_config.get("notification_email"):
            self.critical_alerts_topic.add_subscription(
                sns_subscriptions.EmailSubscription(self.env_config["notification_email"])
            )
            self.warning_alerts_topic.add_subscription(
                sns_subscriptions.EmailSubscription(self.env_config["notification_email"])
            )
    
    def _create_cloudwatch_dashboards(self) -> None:
        """Create CloudWatch dashboards."""
        # Main platform dashboard
        self.main_dashboard = cloudwatch.Dashboard(
            self,
            "MainDashboard",
            dashboard_name=f"DevSecOps-Platform-{self.environment_name}",
        )
        
        # Add widgets to dashboard
        self._add_infrastructure_widgets()
        self._add_application_widgets()
        self._add_security_widgets()
        self._add_cost_widgets()
    
    def _add_infrastructure_widgets(self) -> None:
        """Add infrastructure monitoring widgets."""
        # EC2 instances widget
        ec2_widget = cloudwatch.GraphWidget(
            title="EC2 Instances",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/EC2",
                    metric_name="CPUUtilization",
                    statistic="Average",
                    period=Duration.minutes(5),
                ),
                cloudwatch.Metric(
                    namespace="AWS/EC2",
                    metric_name="NetworkIn",
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
            ],
            width=12,
            height=6,
        )
        
        # RDS widget
        rds_widget = cloudwatch.GraphWidget(
            title="RDS Database",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/RDS",
                    metric_name="CPUUtilization",
                    statistic="Average",
                    period=Duration.minutes(5),
                ),
                cloudwatch.Metric(
                    namespace="AWS/RDS",
                    metric_name="DatabaseConnections",
                    statistic="Average",
                    period=Duration.minutes(5),
                ),
            ],
            width=12,
            height=6,
        )
        
        # Lambda functions widget
        lambda_widget = cloudwatch.GraphWidget(
            title="Lambda Functions",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    statistic="Average",
                    period=Duration.minutes(5),
                ),
            ],
            width=12,
            height=6,
        )
        
        self.main_dashboard.add_widgets(ec2_widget, rds_widget, lambda_widget)
    
    def _add_application_widgets(self) -> None:
        """Add application monitoring widgets."""
        # API Gateway widget
        api_widget = cloudwatch.GraphWidget(
            title="API Gateway",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="Count",
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="4XXError",
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="5XXError",
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
            ],
            right=[
                cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="Latency",
                    statistic="Average",
                    period=Duration.minutes(5),
                ),
            ],
            width=12,
            height=6,
        )
        
        # ECS widget
        ecs_widget = cloudwatch.GraphWidget(
            title="ECS Services",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/ECS",
                    metric_name="CPUUtilization",
                    statistic="Average",
                    period=Duration.minutes(5),
                ),
                cloudwatch.Metric(
                    namespace="AWS/ECS",
                    metric_name="MemoryUtilization",
                    statistic="Average",
                    period=Duration.minutes(5),
                ),
            ],
            width=12,
            height=6,
        )
        
        self.main_dashboard.add_widgets(api_widget, ecs_widget)
    
    def _add_security_widgets(self) -> None:
        """Add security monitoring widgets."""
        # WAF widget
        waf_widget = cloudwatch.GraphWidget(
            title="WAF Security",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/WAFV2",
                    metric_name="AllowedRequests",
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                cloudwatch.Metric(
                    namespace="AWS/WAFV2",
                    metric_name="BlockedRequests",
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
            ],
            width=12,
            height=6,
        )
        
        # GuardDuty findings widget (custom metric)
        guardduty_widget = cloudwatch.SingleValueWidget(
            title="GuardDuty Findings (24h)",
            metrics=[
                cloudwatch.Metric(
                    namespace="Custom/Security",
                    metric_name="GuardDutyFindings",
                    statistic="Sum",
                    period=Duration.hours(24),
                ),
            ],
            width=6,
            height=6,
        )
        
        self.main_dashboard.add_widgets(waf_widget, guardduty_widget)
    
    def _add_cost_widgets(self) -> None:
        """Add cost monitoring widgets."""
        # Estimated charges widget
        cost_widget = cloudwatch.SingleValueWidget(
            title="Estimated Monthly Charges",
            metrics=[
                cloudwatch.Metric(
                    namespace="AWS/Billing",
                    metric_name="EstimatedCharges",
                    statistic="Maximum",
                    period=Duration.hours(6),
                    dimensions_map={"Currency": "USD"},
                ),
            ],
            width=6,
            height=6,
        )
        
        self.main_dashboard.add_widgets(cost_widget)
    
    def _create_alarms(self) -> None:
        """Create CloudWatch alarms."""
        # High CPU utilization alarm
        self.high_cpu_alarm = cloudwatch.Alarm(
            self,
            "HighCPUAlarm",
            alarm_name=f"high-cpu-{self.environment_name}",
            alarm_description="High CPU utilization detected",
            metric=cloudwatch.Metric(
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                statistic="Average",
                period=Duration.minutes(5),
            ),
            threshold=80,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )
        
        self.high_cpu_alarm.add_alarm_action(
            cw_actions.SnsAction(self.warning_alerts_topic)
        )
        
        # Lambda error rate alarm
        self.lambda_error_alarm = cloudwatch.Alarm(
            self,
            "LambdaErrorAlarm",
            alarm_name=f"lambda-errors-{self.environment_name}",
            alarm_description="High Lambda error rate detected",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            threshold=5,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )
        
        self.lambda_error_alarm.add_alarm_action(
            cw_actions.SnsAction(self.critical_alerts_topic)
        )
        
        # Database connection alarm
        self.db_connection_alarm = cloudwatch.Alarm(
            self,
            "DatabaseConnectionAlarm",
            alarm_name=f"db-connections-{self.environment_name}",
            alarm_description="High database connection count",
            metric=cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="DatabaseConnections",
                statistic="Average",
                period=Duration.minutes(5),
            ),
            threshold=80,
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )
        
        self.db_connection_alarm.add_alarm_action(
            cw_actions.SnsAction(self.warning_alerts_topic)
        )
        
        # Cost alarm
        if self.env_config.get("cost_alert_threshold"):
            self.cost_alarm = cloudwatch.Alarm(
                self,
                "CostAlarm",
                alarm_name=f"cost-threshold-{self.environment_name}",
                alarm_description="Monthly cost threshold exceeded",
                metric=cloudwatch.Metric(
                    namespace="AWS/Billing",
                    metric_name="EstimatedCharges",
                    statistic="Maximum",
                    period=Duration.hours(6),
                    dimensions_map={"Currency": "USD"},
                ),
                threshold=self.env_config["cost_alert_threshold"],
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            )
            
            self.cost_alarm.add_alarm_action(
                cw_actions.SnsAction(self.critical_alerts_topic)
            )

    def _create_log_insights_queries(self) -> None:
        """Create CloudWatch Logs Insights queries."""
        # Error analysis query
        self.error_query = logs.CfnQueryDefinition(
            self,
            "ErrorAnalysisQuery",
            name=f"Error-Analysis-{self.environment_name}",
            query_string="""
                fields @timestamp, @message, @logStream
                | filter @message like /ERROR/
                | stats count() by bin(5m)
                | sort @timestamp desc
            """,
            log_group_names=[
                f"/aws/application/{self.environment_name}",
                f"/aws/datapipeline/{self.environment_name}",
            ],
        )

        # Performance analysis query
        self.performance_query = logs.CfnQueryDefinition(
            self,
            "PerformanceAnalysisQuery",
            name=f"Performance-Analysis-{self.environment_name}",
            query_string="""
                fields @timestamp, @duration, @requestId
                | filter @type = "REPORT"
                | stats avg(@duration), max(@duration), min(@duration) by bin(5m)
                | sort @timestamp desc
            """,
            log_group_names=[
                f"/aws/lambda/data-validator-{self.environment_name}",
                f"/aws/lambda/data-transformer-{self.environment_name}",
            ],
        )

    def _create_custom_metrics_lambda(self) -> None:
        """Create Lambda function for custom metrics collection."""
        self.metrics_collector_lambda = lambda_.Function(
            self,
            "MetricsCollector",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')
guardduty = boto3.client('guardduty')

def handler(event, context):
    '''Custom metrics collection Lambda'''
    try:
        # Collect GuardDuty findings
        detectors = guardduty.list_detectors()

        total_findings = 0
        for detector_id in detectors.get('DetectorIds', []):
            findings = guardduty.list_findings(
                DetectorId=detector_id,
                FindingCriteria={
                    'Criterion': {
                        'updatedAt': {
                            'gte': int((datetime.now().timestamp() - 86400) * 1000)  # Last 24 hours
                        }
                    }
                }
            )
            total_findings += len(findings.get('FindingIds', []))

        # Send custom metric
        cloudwatch.put_metric_data(
            Namespace='Custom/Security',
            MetricData=[
                {
                    'MetricName': 'GuardDutyFindings',
                    'Value': total_findings,
                    'Unit': 'Count',
                    'Timestamp': datetime.now()
                }
            ]
        )

        logger.info(f"Sent GuardDuty findings metric: {total_findings}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Metrics collected successfully',
                'guardduty_findings': total_findings
            })
        }

    except Exception as e:
        logger.error(f"Error collecting metrics: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
            """),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "ENVIRONMENT": self.environment_name,
            },
        )

        # Grant permissions to the Lambda function
        self.metrics_collector_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "guardduty:ListDetectors",
                    "guardduty:ListFindings",
                    "cloudwatch:PutMetricData",
                ],
                resources=["*"]
            )
        )

        # Schedule the Lambda to run every hour
        from aws_cdk import aws_events as events
        from aws_cdk import aws_events_targets as targets

        metrics_schedule = events.Rule(
            self,
            "MetricsCollectionSchedule",
            schedule=events.Schedule.rate(Duration.hours(1)),
        )

        metrics_schedule.add_target(
            targets.LambdaFunction(self.metrics_collector_lambda)
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        CfnOutput(
            self,
            "DashboardURL",
            value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.main_dashboard.dashboard_name}",
            description="CloudWatch Dashboard URL",
            export_name=f"{self.stack_name}-DashboardURL"
        )

        CfnOutput(
            self,
            "CriticalAlertsTopicArn",
            value=self.critical_alerts_topic.topic_arn,
            description="Critical Alerts SNS Topic ARN",
            export_name=f"{self.stack_name}-CriticalAlertsTopicArn"
        )

        CfnOutput(
            self,
            "WarningAlertsTopicArn",
            value=self.warning_alerts_topic.topic_arn,
            description="Warning Alerts SNS Topic ARN",
            export_name=f"{self.stack_name}-WarningAlertsTopicArn"
        )
