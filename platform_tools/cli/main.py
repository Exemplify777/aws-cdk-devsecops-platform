"""
DevSecOps Platform CLI
Command-line interface for project management and automation
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import typer
import boto3
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from cookiecutter.main import cookiecutter

from platform.cli.config import CLIConfig
from platform.cli.templates import TemplateManager
from platform.cli.github import GitHubManager
from platform.cli.aws import AWSManager

app = typer.Typer(
    name="ddk-cli",
    help="DevSecOps Platform CLI for data pipelines and ML workflows",
    add_completion=False,
)
console = Console()


@app.command()
def init(
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive setup"),
):
    """Initialize the DevSecOps platform CLI."""
    console.print(Panel.fit("🚀 DevSecOps Platform CLI Initialization", style="bold blue"))
    
    config = CLIConfig()
    
    if interactive:
        console.print("\n[bold]Let's set up your DevSecOps platform configuration![/bold]\n")
        
        # AWS Configuration
        aws_region = Prompt.ask("AWS Region", default="us-east-1")
        aws_profile = Prompt.ask("AWS Profile", default="default")
        
        # GitHub Configuration
        github_org = Prompt.ask("GitHub Organization")
        github_token = Prompt.ask("GitHub Token (optional)", default="", show_default=False)
        
        # Project Configuration
        project_prefix = Prompt.ask("Project Prefix", default="data-platform")
        default_environment = Prompt.ask("Default Environment", default="dev")
        
        config.update({
            "aws": {
                "region": aws_region,
                "profile": aws_profile,
            },
            "github": {
                "organization": github_org,
                "token": github_token,
            },
            "project": {
                "prefix": project_prefix,
                "default_environment": default_environment,
            }
        })
    
    config.save()
    console.print("✅ Configuration saved successfully!")


@app.command()
def create_project(
    name: str = typer.Argument(..., help="Project name"),
    template: str = typer.Option("data-pipeline", "--template", "-t", help="Project template"),
    environment: str = typer.Option("dev", "--env", "-e", help="Target environment"),
    github_repo: bool = typer.Option(True, "--github/--no-github", help="Create GitHub repository"),
    deploy: bool = typer.Option(False, "--deploy", help="Deploy after creation"),
):
    """Create a new data pipeline project."""
    console.print(Panel.fit(f"🏗️  Creating project: {name}", style="bold green"))
    
    config = CLIConfig()
    template_manager = TemplateManager()
    
    # Validate template
    if not template_manager.template_exists(template):
        console.print(f"❌ Template '{template}' not found")
        available_templates = template_manager.list_templates()
        console.print(f"Available templates: {', '.join(available_templates)}")
        raise typer.Exit(1)
    
    project_dir = Path.cwd() / name
    
    if project_dir.exists():
        if not Confirm.ask(f"Directory '{name}' already exists. Continue?"):
            raise typer.Exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Generate project from template
        task = progress.add_task("Generating project from template...", total=None)
        
        template_context = {
            "project_name": name,
            "environment": environment,
            "aws_region": config.get("aws.region", "us-east-1"),
            "github_org": config.get("github.organization", ""),
            "created_date": datetime.now().isoformat(),
        }
        
        template_path = template_manager.get_template_path(template)
        cookiecutter(
            str(template_path),
            extra_context=template_context,
            no_input=True,
            output_dir=str(Path.cwd()),
        )
        
        progress.update(task, description="✅ Project generated")
        
        # Initialize Git repository
        if github_repo:
            task = progress.add_task("Initializing Git repository...", total=None)
            
            os.chdir(project_dir)
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit: Generated from DevSecOps platform"],
                check=True,
                capture_output=True
            )
            
            progress.update(task, description="✅ Git repository initialized")
            
            # Create GitHub repository
            if config.get("github.token"):
                task = progress.add_task("Creating GitHub repository...", total=None)
                
                github_manager = GitHubManager(config.get("github.token"))
                repo_url = github_manager.create_repository(
                    name=name,
                    organization=config.get("github.organization"),
                    description=f"Data pipeline project: {name}",
                    private=True,
                )
                
                subprocess.run(
                    ["git", "remote", "add", "origin", repo_url],
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "push", "-u", "origin", "main"],
                    check=True,
                    capture_output=True
                )
                
                progress.update(task, description="✅ GitHub repository created")
        
        # Deploy infrastructure
        if deploy:
            task = progress.add_task("Deploying infrastructure...", total=None)
            
            aws_manager = AWSManager(
                region=config.get("aws.region"),
                profile=config.get("aws.profile")
            )
            
            deployment_result = aws_manager.deploy_project(name, environment)
            
            if deployment_result["success"]:
                progress.update(task, description="✅ Infrastructure deployed")
            else:
                progress.update(task, description="❌ Deployment failed")
                console.print(f"Deployment error: {deployment_result['error']}")
    
    console.print(f"\n🎉 Project '{name}' created successfully!")
    console.print(f"📁 Location: {project_dir}")
    
    if github_repo and config.get("github.token"):
        console.print(f"🔗 GitHub: https://github.com/{config.get('github.organization')}/{name}")


@app.command()
def list_projects(
    environment: Optional[str] = typer.Option(None, "--env", "-e", help="Filter by environment"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
):
    """List all projects in the platform."""
    console.print(Panel.fit("📋 Platform Projects", style="bold blue"))
    
    config = CLIConfig()
    aws_manager = AWSManager(
        region=config.get("aws.region"),
        profile=config.get("aws.profile")
    )
    
    projects = aws_manager.list_projects(environment=environment, status=status)
    
    if not projects:
        console.print("No projects found.")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Environment", style="yellow")
    table.add_column("Status", style="red")
    table.add_column("Created", style="blue")
    table.add_column("Owner", style="white")
    
    for project in projects:
        table.add_row(
            project["name"],
            project["type"],
            project["environment"],
            project["status"],
            project["created_at"],
            project["owner"],
        )
    
    console.print(table)


@app.command()
def deploy(
    project: Optional[str] = typer.Argument(None, help="Project name (current directory if not specified)"),
    environment: str = typer.Option("dev", "--env", "-e", help="Target environment"),
    stack: Optional[str] = typer.Option(None, "--stack", "-s", help="Specific stack to deploy"),
    approve: bool = typer.Option(False, "--approve", help="Auto-approve deployment"),
):
    """Deploy project infrastructure."""
    if not project:
        project = Path.cwd().name
    
    console.print(Panel.fit(f"🚀 Deploying {project} to {environment}", style="bold green"))
    
    config = CLIConfig()
    aws_manager = AWSManager(
        region=config.get("aws.region"),
        profile=config.get("aws.profile")
    )
    
    if not approve:
        if not Confirm.ask(f"Deploy {project} to {environment}?"):
            raise typer.Exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Deploying infrastructure...", total=None)
        
        result = aws_manager.deploy_project(project, environment, stack)
        
        if result["success"]:
            progress.update(task, description="✅ Deployment completed")
            console.print("\n🎉 Deployment successful!")
            
            if result.get("outputs"):
                console.print("\n📊 Stack Outputs:")
                for key, value in result["outputs"].items():
                    console.print(f"  {key}: {value}")
        else:
            progress.update(task, description="❌ Deployment failed")
            console.print(f"\n💥 Deployment failed: {result['error']}")
            raise typer.Exit(1)


@app.command()
def destroy(
    project: Optional[str] = typer.Argument(None, help="Project name (current directory if not specified)"),
    environment: str = typer.Option("dev", "--env", "-e", help="Target environment"),
    force: bool = typer.Option(False, "--force", help="Force destruction without confirmation"),
):
    """Destroy project infrastructure."""
    if not project:
        project = Path.cwd().name
    
    console.print(Panel.fit(f"💥 Destroying {project} in {environment}", style="bold red"))
    
    if not force:
        console.print(f"[bold red]WARNING: This will destroy all resources for {project} in {environment}![/bold red]")
        if not Confirm.ask("Are you sure you want to continue?"):
            raise typer.Exit(1)
        
        if not Confirm.ask("Type the project name to confirm", default=project) == project:
            console.print("❌ Project name mismatch. Aborting.")
            raise typer.Exit(1)
    
    config = CLIConfig()
    aws_manager = AWSManager(
        region=config.get("aws.region"),
        profile=config.get("aws.profile")
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Destroying infrastructure...", total=None)
        
        result = aws_manager.destroy_project(project, environment)
        
        if result["success"]:
            progress.update(task, description="✅ Destruction completed")
            console.print("\n🗑️  Infrastructure destroyed successfully!")
        else:
            progress.update(task, description="❌ Destruction failed")
            console.print(f"\n💥 Destruction failed: {result['error']}")
            raise typer.Exit(1)


@app.command()
def status(
    project: Optional[str] = typer.Argument(None, help="Project name (current directory if not specified)"),
    environment: str = typer.Option("dev", "--env", "-e", help="Target environment"),
):
    """Show project status and health."""
    if not project:
        project = Path.cwd().name
    
    console.print(Panel.fit(f"📊 Status: {project} ({environment})", style="bold blue"))
    
    config = CLIConfig()
    aws_manager = AWSManager(
        region=config.get("aws.region"),
        profile=config.get("aws.profile")
    )
    
    status_info = aws_manager.get_project_status(project, environment)
    
    if not status_info:
        console.print("❌ Project not found or not deployed")
        return
    
    # Infrastructure status
    console.print("\n[bold]Infrastructure Status:[/bold]")
    infra_table = Table(show_header=True, header_style="bold magenta")
    infra_table.add_column("Stack", style="cyan")
    infra_table.add_column("Status", style="green")
    infra_table.add_column("Last Updated", style="blue")
    
    for stack in status_info.get("stacks", []):
        infra_table.add_row(
            stack["name"],
            stack["status"],
            stack["last_updated"],
        )
    
    console.print(infra_table)
    
    # Health checks
    console.print("\n[bold]Health Checks:[/bold]")
    health_table = Table(show_header=True, header_style="bold magenta")
    health_table.add_column("Service", style="cyan")
    health_table.add_column("Status", style="green")
    health_table.add_column("Message", style="white")
    
    for check in status_info.get("health_checks", []):
        health_table.add_row(
            check["service"],
            "✅ Healthy" if check["healthy"] else "❌ Unhealthy",
            check["message"],
        )
    
    console.print(health_table)


@app.command()
def logs(
    project: Optional[str] = typer.Argument(None, help="Project name (current directory if not specified)"),
    environment: str = typer.Option("dev", "--env", "-e", help="Target environment"),
    service: Optional[str] = typer.Option(None, "--service", "-s", help="Specific service"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(100, "--lines", "-n", help="Number of lines to show"),
):
    """View project logs."""
    if not project:
        project = Path.cwd().name
    
    console.print(Panel.fit(f"📜 Logs: {project} ({environment})", style="bold blue"))
    
    config = CLIConfig()
    aws_manager = AWSManager(
        region=config.get("aws.region"),
        profile=config.get("aws.profile")
    )
    
    aws_manager.stream_logs(project, environment, service, follow, lines)


@app.command()
def templates():
    """List available project templates."""
    console.print(Panel.fit("📋 Available Templates", style="bold blue"))
    
    template_manager = TemplateManager()
    templates = template_manager.list_templates()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Template", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Type", style="green")
    
    for template in templates:
        info = template_manager.get_template_info(template)
        table.add_row(
            template,
            info.get("description", "No description"),
            info.get("type", "Unknown"),
        )
    
    console.print(table)


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    reset: bool = typer.Option(False, "--reset", help="Reset configuration"),
):
    """Manage CLI configuration."""
    config_obj = CLIConfig()
    
    if reset:
        if Confirm.ask("Reset all configuration?"):
            config_obj.reset()
            console.print("✅ Configuration reset")
        return
    
    if show:
        console.print(Panel.fit("⚙️  Current Configuration", style="bold blue"))
        console.print(json.dumps(config_obj.data, indent=2))
        return
    
    # Interactive configuration update
    console.print("Use 'ddk-cli init' to configure the CLI")


if __name__ == "__main__":
    app()
