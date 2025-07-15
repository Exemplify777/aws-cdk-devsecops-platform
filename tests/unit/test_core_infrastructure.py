"""
Unit tests for Core Infrastructure Stack
"""

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template

from infrastructure.stacks.core_infrastructure_stack import CoreInfrastructureStack


@pytest.fixture
def app():
    """Create CDK app for testing."""
    return App()


@pytest.fixture
def env_config():
    """Test environment configuration."""
    return {
        "environment_name": "test",
        "project_name": "test-project",
        "organization": "test-org",
        "aws_region": "us-east-1",
        "vpc_cidr": "10.0.0.0/16",
        "availability_zones": ["us-east-1a", "us-east-1b"],
        "enable_deletion_protection": False,
        "enable_vpc_flow_logs": True,
        "db_allocated_storage": 20,
        "db_backup_retention": 7,
        "container_cpu": 256,
        "container_memory": 512,
    }


@pytest.fixture
def core_stack(app, env_config):
    """Create Core Infrastructure Stack for testing."""
    return CoreInfrastructureStack(
        app,
        "TestCoreInfrastructure",
        env_config=env_config,
        env=Environment(account="123456789012", region="us-east-1")
    )


def test_vpc_creation(core_stack):
    """Test VPC is created with correct configuration."""
    template = Template.from_stack(core_stack)
    
    # Check VPC exists
    template.has_resource_properties("AWS::EC2::VPC", {
        "CidrBlock": "10.0.0.0/16",
        "EnableDnsHostnames": True,
        "EnableDnsSupport": True,
    })
    
    # Check subnets are created
    template.resource_count_is("AWS::EC2::Subnet", 6)  # 2 AZs * 3 subnet types


def test_kms_keys_creation(core_stack):
    """Test KMS keys are created with proper configuration."""
    template = Template.from_stack(core_stack)
    
    # Check KMS keys exist
    template.resource_count_is("AWS::KMS::Key", 3)  # Main, S3, Logs
    
    # Check key rotation is enabled
    template.has_resource_properties("AWS::KMS::Key", {
        "EnableKeyRotation": True
    })


def test_s3_buckets_creation(core_stack):
    """Test S3 buckets are created with proper configuration."""
    template = Template.from_stack(core_stack)
    
    # Check S3 buckets exist
    template.resource_count_is("AWS::S3::Bucket", 3)  # Data lake, artifacts, logs
    
    # Check encryption is enabled
    template.has_resource_properties("AWS::S3::Bucket", {
        "BucketEncryption": {
            "ServerSideEncryptionConfiguration": [
                {
                    "ServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms"
                    }
                }
            ]
        }
    })
    
    # Check versioning is enabled
    template.has_resource_properties("AWS::S3::Bucket", {
        "VersioningConfiguration": {
            "Status": "Enabled"
        }
    })


def test_vpc_endpoints_creation(core_stack):
    """Test VPC endpoints are created."""
    template = Template.from_stack(core_stack)
    
    # Check gateway endpoints
    template.has_resource_properties("AWS::EC2::VPCEndpoint", {
        "ServiceName": "com.amazonaws.us-east-1.s3"
    })
    
    template.has_resource_properties("AWS::EC2::VPCEndpoint", {
        "ServiceName": "com.amazonaws.us-east-1.dynamodb"
    })


def test_iam_roles_creation(core_stack):
    """Test IAM roles are created with proper policies."""
    template = Template.from_stack(core_stack)
    
    # Check IAM roles exist
    template.resource_count_is("AWS::IAM::Role", 3)  # Data pipeline, CI/CD, VPC Flow Logs
    
    # Check data pipeline role has correct trust policy
    template.has_resource_properties("AWS::IAM::Role", {
        "AssumeRolePolicyDocument": {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": ["lambda.amazonaws.com", "ecs-tasks.amazonaws.com", "glue.amazonaws.com"]
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
    })


def test_cloudwatch_log_groups_creation(core_stack):
    """Test CloudWatch log groups are created."""
    template = Template.from_stack(core_stack)
    
    # Check log groups exist
    template.resource_count_is("AWS::Logs::LogGroup", 4)  # App, pipeline, security, VPC flow logs
    
    # Check encryption is enabled
    template.has_resource_properties("AWS::Logs::LogGroup", {
        "KmsKeyId": {
            "Fn::GetAtt": ["LogsKMSKey", "Arn"]
        }
    })


def test_vpc_flow_logs_creation(core_stack):
    """Test VPC Flow Logs are created when enabled."""
    template = Template.from_stack(core_stack)
    
    # Check VPC Flow Logs exist
    template.has_resource_properties("AWS::EC2::FlowLog", {
        "ResourceType": "VPC",
        "TrafficType": "ALL"
    })


def test_outputs_creation(core_stack):
    """Test CloudFormation outputs are created."""
    template = Template.from_stack(core_stack)
    
    # Check outputs exist
    outputs = template.find_outputs("*")
    
    assert "VPCId" in outputs
    assert "DataLakeBucketName" in outputs
    assert "ArtifactsBucketName" in outputs
    assert "MainKMSKeyId" in outputs


def test_stack_with_deletion_protection(app, env_config):
    """Test stack behavior with deletion protection enabled."""
    env_config["enable_deletion_protection"] = True
    
    stack = CoreInfrastructureStack(
        app,
        "TestCoreInfrastructureProtected",
        env_config=env_config,
        env=Environment(account="123456789012", region="us-east-1")
    )
    
    template = Template.from_stack(stack)
    
    # Check KMS keys have RETAIN policy
    template.has_resource_properties("AWS::KMS::Key", {
        "DeletionPolicy": "Retain"
    })


def test_stack_without_vpc_flow_logs(app, env_config):
    """Test stack behavior with VPC Flow Logs disabled."""
    env_config["enable_vpc_flow_logs"] = False
    
    stack = CoreInfrastructureStack(
        app,
        "TestCoreInfrastructureNoFlowLogs",
        env_config=env_config,
        env=Environment(account="123456789012", region="us-east-1")
    )
    
    template = Template.from_stack(stack)
    
    # Check VPC Flow Logs don't exist
    template.resource_count_is("AWS::EC2::FlowLog", 0)
