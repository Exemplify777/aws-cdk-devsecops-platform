"""
Integration tests for CLI functionality
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from platform.cli.main import app


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


def test_cli_init_command(runner):
    """Test CLI initialization command."""
    with patch('platform.cli.config.CLIConfig.save') as mock_save:
        result = runner.invoke(app, ['init', '--no-interactive'])
        assert result.exit_code == 0
        mock_save.assert_called_once()


def test_cli_templates_command(runner):
    """Test templates listing command."""
    result = runner.invoke(app, ['templates'])
    assert result.exit_code == 0
    assert "data-pipeline" in result.stdout


def test_cli_create_project_command(runner, temp_project_dir):
    """Test project creation command."""
    os.chdir(temp_project_dir)
    
    with patch('platform.cli.templates.TemplateManager.template_exists', return_value=True), \
         patch('cookiecutter.main.cookiecutter') as mock_cookiecutter, \
         patch('subprocess.run') as mock_subprocess:
        
        mock_subprocess.return_value.returncode = 0
        
        result = runner.invoke(app, [
            'create-project', 
            'test-project',
            '--template', 'data-pipeline',
            '--no-github',
            '--no-deploy'
        ])
        
        assert result.exit_code == 0
        mock_cookiecutter.assert_called_once()


def test_cli_config_show_command(runner):
    """Test config show command."""
    with patch('platform.cli.config.CLIConfig') as mock_config:
        mock_config.return_value.data = {"test": "config"}
        
        result = runner.invoke(app, ['config', '--show'])
        assert result.exit_code == 0
        assert "test" in result.stdout


@pytest.mark.integration
def test_cli_deploy_command(runner):
    """Test deploy command."""
    with patch('platform.cli.aws.AWSManager.deploy_project') as mock_deploy:
        mock_deploy.return_value = {
            "success": True,
            "outputs": {"TestOutput": "test-value"}
        }
        
        result = runner.invoke(app, [
            'deploy',
            'test-project',
            '--env', 'dev',
            '--approve'
        ])
        
        assert result.exit_code == 0
        mock_deploy.assert_called_once()


@pytest.mark.integration
def test_cli_status_command(runner):
    """Test status command."""
    with patch('platform.cli.aws.AWSManager.get_project_status') as mock_status:
        mock_status.return_value = {
            "project": "test-project",
            "environment": "dev",
            "stacks": [
                {
                    "name": "test-stack",
                    "status": "CREATE_COMPLETE",
                    "last_updated": "2024-01-01T00:00:00Z"
                }
            ],
            "health_checks": [
                {
                    "service": "Lambda Functions",
                    "healthy": True,
                    "message": "2 functions found"
                }
            ]
        }
        
        result = runner.invoke(app, [
            'status',
            'test-project',
            '--env', 'dev'
        ])
        
        assert result.exit_code == 0
        assert "test-project" in result.stdout
        assert "CREATE_COMPLETE" in result.stdout


@pytest.mark.integration
def test_cli_list_projects_command(runner):
    """Test list projects command."""
    with patch('platform.cli.aws.AWSManager.list_projects') as mock_list:
        mock_list.return_value = [
            {
                "name": "test-project-1",
                "type": "data-pipeline",
                "environment": "dev",
                "status": "CREATE_COMPLETE",
                "created_at": "2024-01-01 00:00:00",
                "owner": "test-user"
            },
            {
                "name": "test-project-2",
                "type": "ml-workflow",
                "environment": "staging",
                "status": "UPDATE_COMPLETE",
                "created_at": "2024-01-02 00:00:00",
                "owner": "test-user"
            }
        ]
        
        result = runner.invoke(app, ['list-projects'])
        
        assert result.exit_code == 0
        assert "test-project-1" in result.stdout
        assert "test-project-2" in result.stdout


@pytest.mark.integration
def test_cli_destroy_command(runner):
    """Test destroy command."""
    with patch('platform.cli.aws.AWSManager.destroy_project') as mock_destroy:
        mock_destroy.return_value = {"success": True}
        
        result = runner.invoke(app, [
            'destroy',
            'test-project',
            '--env', 'dev',
            '--force'
        ])
        
        assert result.exit_code == 0
        mock_destroy.assert_called_once()


def test_cli_error_handling(runner):
    """Test CLI error handling."""
    with patch('platform.cli.aws.AWSManager.deploy_project') as mock_deploy:
        mock_deploy.return_value = {
            "success": False,
            "error": "Deployment failed"
        }
        
        result = runner.invoke(app, [
            'deploy',
            'test-project',
            '--env', 'dev',
            '--approve'
        ])
        
        assert result.exit_code == 1
        assert "Deployment failed" in result.stdout
