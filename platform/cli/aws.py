"""
AWS Integration for CLI
"""

import boto3
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import subprocess
from rich.console import Console

console = Console()


class AWSManager:
    """Manages AWS operations for the CLI."""
    
    def __init__(self, region: str = "us-east-1", profile: Optional[str] = None):
        self.region = region
        self.profile = profile
        
        # Initialize AWS session
        if profile:
            self.session = boto3.Session(profile_name=profile, region_name=region)
        else:
            self.session = boto3.Session(region_name=region)
        
        self.cloudformation = self.session.client("cloudformation")
        self.logs = self.session.client("logs")
        self.ecs = self.session.client("ecs")
        self.lambda_client = self.session.client("lambda")
        self.dynamodb = self.session.client("dynamodb")
    
    def deploy_project(self, project_name: str, environment: str, stack: Optional[str] = None) -> Dict[str, Any]:
        """Deploy project infrastructure using CDK."""
        try:
            # Build CDK command
            cmd = ["cdk", "deploy"]
            
            if stack:
                cmd.append(stack)
            else:
                cmd.append("--all")
            
            cmd.extend([
                "--context", f"environment={environment}",
                "--require-approval=never",
                "--outputs-file", "cdk-outputs.json"
            ])
            
            # Set AWS environment variables
            env = {
                "AWS_REGION": self.region,
                "CDK_DEFAULT_REGION": self.region,
            }
            
            if self.profile:
                env["AWS_PROFILE"] = self.profile
            
            # Execute CDK deploy
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **env}
            )
            
            if result.returncode == 0:
                # Read outputs if available
                outputs = {}
                try:
                    with open("cdk-outputs.json", "r") as f:
                        outputs = json.load(f)
                except FileNotFoundError:
                    pass
                
                return {
                    "success": True,
                    "outputs": outputs,
                    "message": "Deployment completed successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "message": "Deployment failed"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Deployment failed with exception"
            }
    
    def destroy_project(self, project_name: str, environment: str) -> Dict[str, Any]:
        """Destroy project infrastructure using CDK."""
        try:
            cmd = [
                "cdk", "destroy", "--all",
                "--context", f"environment={environment}",
                "--force"
            ]
            
            env = {
                "AWS_REGION": self.region,
                "CDK_DEFAULT_REGION": self.region,
            }
            
            if self.profile:
                env["AWS_PROFILE"] = self.profile
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **env}
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Destruction completed successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "message": "Destruction failed"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Destruction failed with exception"
            }
    
    def list_projects(self, environment: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List projects from CloudFormation stacks."""
        try:
            stacks = self.cloudformation.list_stacks(
                StackStatusFilter=[
                    "CREATE_COMPLETE",
                    "UPDATE_COMPLETE",
                    "CREATE_IN_PROGRESS",
                    "UPDATE_IN_PROGRESS",
                ]
            )
            
            projects = []
            
            for stack in stacks["StackSummaries"]:
                stack_name = stack["StackName"]
                
                # Filter by environment if specified
                if environment and environment not in stack_name:
                    continue
                
                # Extract project info from stack name and tags
                project_info = {
                    "name": stack_name,
                    "type": "unknown",
                    "environment": "unknown",
                    "status": stack["StackStatus"],
                    "created_at": stack["CreationTime"].strftime("%Y-%m-%d %H:%M:%S"),
                    "owner": "unknown",
                }
                
                # Try to get more details from stack tags
                try:
                    stack_details = self.cloudformation.describe_stacks(StackName=stack_name)
                    tags = stack_details["Stacks"][0].get("Tags", [])
                    
                    for tag in tags:
                        if tag["Key"] == "Environment":
                            project_info["environment"] = tag["Value"]
                        elif tag["Key"] == "Project":
                            project_info["type"] = tag["Value"]
                        elif tag["Key"] == "Owner":
                            project_info["owner"] = tag["Value"]
                
                except Exception:
                    pass
                
                # Filter by status if specified
                if status and status.lower() not in project_info["status"].lower():
                    continue
                
                projects.append(project_info)
            
            return projects
        
        except Exception as e:
            console.print(f"Error listing projects: {e}")
            return []
    
    def get_project_status(self, project_name: str, environment: str) -> Optional[Dict[str, Any]]:
        """Get detailed project status."""
        try:
            # Find stacks for this project
            stack_prefix = f"{project_name}-{environment}" if project_name != environment else project_name
            
            stacks = self.cloudformation.list_stacks()
            project_stacks = [
                stack for stack in stacks["StackSummaries"]
                if stack_prefix in stack["StackName"]
            ]
            
            if not project_stacks:
                return None
            
            status_info = {
                "project": project_name,
                "environment": environment,
                "stacks": [],
                "health_checks": [],
            }
            
            # Get stack details
            for stack in project_stacks:
                stack_info = {
                    "name": stack["StackName"],
                    "status": stack["StackStatus"],
                    "last_updated": stack.get("LastUpdatedTime", stack["CreationTime"]).strftime("%Y-%m-%d %H:%M:%S"),
                }
                status_info["stacks"].append(stack_info)
            
            # Perform health checks
            status_info["health_checks"] = self._perform_health_checks(project_name, environment)
            
            return status_info
        
        except Exception as e:
            console.print(f"Error getting project status: {e}")
            return None
    
    def _perform_health_checks(self, project_name: str, environment: str) -> List[Dict[str, Any]]:
        """Perform basic health checks."""
        health_checks = []
        
        # Check Lambda functions
        try:
            functions = self.lambda_client.list_functions()
            lambda_count = len([
                f for f in functions["Functions"]
                if environment in f["FunctionName"]
            ])
            
            health_checks.append({
                "service": "Lambda Functions",
                "healthy": lambda_count > 0,
                "message": f"{lambda_count} functions found"
            })
        except Exception as e:
            health_checks.append({
                "service": "Lambda Functions",
                "healthy": False,
                "message": f"Error checking Lambda: {e}"
            })
        
        # Check ECS clusters
        try:
            clusters = self.ecs.list_clusters()
            ecs_clusters = [
                c for c in clusters["clusterArns"]
                if environment in c
            ]
            
            health_checks.append({
                "service": "ECS Clusters",
                "healthy": len(ecs_clusters) > 0,
                "message": f"{len(ecs_clusters)} clusters found"
            })
        except Exception as e:
            health_checks.append({
                "service": "ECS Clusters",
                "healthy": False,
                "message": f"Error checking ECS: {e}"
            })
        
        # Check DynamoDB tables
        try:
            tables = self.dynamodb.list_tables()
            dynamo_tables = [
                t for t in tables["TableNames"]
                if environment in t
            ]
            
            health_checks.append({
                "service": "DynamoDB Tables",
                "healthy": len(dynamo_tables) > 0,
                "message": f"{len(dynamo_tables)} tables found"
            })
        except Exception as e:
            health_checks.append({
                "service": "DynamoDB Tables",
                "healthy": False,
                "message": f"Error checking DynamoDB: {e}"
            })
        
        return health_checks
    
    def stream_logs(self, project_name: str, environment: str, service: Optional[str] = None, 
                   follow: bool = False, lines: int = 100) -> None:
        """Stream logs from CloudWatch."""
        try:
            # Find log groups for the project
            log_groups = self.logs.describe_log_groups()
            
            project_log_groups = [
                lg["logGroupName"] for lg in log_groups["logGroups"]
                if environment in lg["logGroupName"]
            ]
            
            if service:
                project_log_groups = [
                    lg for lg in project_log_groups
                    if service in lg
                ]
            
            if not project_log_groups:
                console.print("No log groups found for the project")
                return
            
            # Get recent log events
            end_time = int(time.time() * 1000)
            start_time = end_time - (24 * 60 * 60 * 1000)  # Last 24 hours
            
            for log_group in project_log_groups:
                console.print(f"\n[bold]Log Group: {log_group}[/bold]")
                
                try:
                    events = self.logs.filter_log_events(
                        logGroupName=log_group,
                        startTime=start_time,
                        endTime=end_time,
                        limit=lines
                    )
                    
                    for event in events["events"]:
                        timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)
                        console.print(f"[dim]{timestamp}[/dim] {event['message']}")
                
                except Exception as e:
                    console.print(f"Error reading logs from {log_group}: {e}")
            
            # TODO: Implement follow mode with real-time streaming
            if follow:
                console.print("\n[yellow]Follow mode not yet implemented[/yellow]")
        
        except Exception as e:
            console.print(f"Error streaming logs: {e}")
