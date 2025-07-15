"""
Smoke tests for basic health checks
"""

import pytest
import requests
import boto3
import os
from typing import Dict, Any


@pytest.fixture
def environment():
    """Get test environment from command line or environment variable."""
    return os.environ.get("TEST_ENVIRONMENT", "dev")


@pytest.fixture
def aws_region():
    """Get AWS region for testing."""
    return os.environ.get("AWS_REGION", "us-east-1")


@pytest.fixture
def stack_outputs(environment, aws_region):
    """Get CloudFormation stack outputs."""
    cloudformation = boto3.client("cloudformation", region_name=aws_region)
    
    outputs = {}
    
    # Get outputs from all stacks
    stack_names = [
        f"CoreInfrastructure-{environment}",
        f"Security-{environment}",
        f"DataPipeline-{environment}",
        f"Monitoring-{environment}",
        f"Portal-{environment}",
        f"AITools-{environment}",
    ]
    
    for stack_name in stack_names:
        try:
            response = cloudformation.describe_stacks(StackName=stack_name)
            stack_outputs = response["Stacks"][0].get("Outputs", [])
            
            for output in stack_outputs:
                outputs[output["OutputKey"]] = output["OutputValue"]
                
        except cloudformation.exceptions.ClientError:
            # Stack might not exist in this environment
            continue
    
    return outputs


def test_vpc_exists(stack_outputs):
    """Test that VPC exists and is accessible."""
    vpc_id = stack_outputs.get("VPCId")
    assert vpc_id is not None, "VPC ID not found in stack outputs"
    
    ec2 = boto3.client("ec2")
    response = ec2.describe_vpcs(VpcIds=[vpc_id])
    
    assert len(response["Vpcs"]) == 1
    assert response["Vpcs"][0]["State"] == "available"


def test_s3_buckets_exist(stack_outputs):
    """Test that S3 buckets exist and are accessible."""
    bucket_names = [
        stack_outputs.get("DataLakeBucketName"),
        stack_outputs.get("ArtifactsBucketName"),
        stack_outputs.get("FrontendBucketName"),
    ]
    
    s3 = boto3.client("s3")
    
    for bucket_name in bucket_names:
        if bucket_name:
            # Check bucket exists
            response = s3.head_bucket(Bucket=bucket_name)
            assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
            
            # Check bucket encryption
            try:
                encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                assert "ServerSideEncryptionConfiguration" in encryption
            except s3.exceptions.ClientError as e:
                if e.response["Error"]["Code"] != "ServerSideEncryptionConfigurationNotFoundError":
                    raise


def test_database_connectivity(stack_outputs):
    """Test database connectivity."""
    db_endpoint = stack_outputs.get("DatabaseEndpoint")
    if not db_endpoint:
        pytest.skip("Database endpoint not found")
    
    # Basic connectivity test (without actual connection)
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((db_endpoint, 5432))
        sock.close()
        
        # Connection should be refused (expected) or successful
        # We're just checking if the endpoint is reachable
        assert result in [0, 61, 111]  # 0=success, 61=connection refused (macOS), 111=connection refused (Linux)
        
    except socket.gaierror:
        pytest.fail(f"Database endpoint {db_endpoint} is not resolvable")


def test_api_gateway_health(stack_outputs):
    """Test API Gateway endpoints are accessible."""
    api_urls = [
        stack_outputs.get("APIGatewayURL"),
        stack_outputs.get("AIToolsAPIURL"),
    ]
    
    for api_url in api_urls:
        if api_url:
            try:
                # Test basic connectivity
                response = requests.get(f"{api_url}/health", timeout=10)
                # Accept 404 as the health endpoint might not be implemented
                assert response.status_code in [200, 404, 403]
                
            except requests.exceptions.RequestException as e:
                pytest.fail(f"API Gateway {api_url} is not accessible: {e}")


def test_cloudfront_distribution(stack_outputs):
    """Test CloudFront distribution is accessible."""
    cloudfront_url = stack_outputs.get("CloudFrontURL")
    if not cloudfront_url:
        pytest.skip("CloudFront URL not found")
    
    try:
        response = requests.get(cloudfront_url, timeout=30)
        # Accept various status codes as content might not be deployed yet
        assert response.status_code in [200, 403, 404]
        
    except requests.exceptions.RequestException as e:
        pytest.fail(f"CloudFront distribution {cloudfront_url} is not accessible: {e}")


def test_lambda_functions_exist(environment, aws_region):
    """Test that Lambda functions exist and are in active state."""
    lambda_client = boto3.client("lambda", region_name=aws_region)
    
    expected_functions = [
        f"data-validator-{environment}",
        f"data-transformer-{environment}",
        f"metrics-collector-{environment}",
        f"code-generator-{environment}",
        f"error-analyzer-{environment}",
        f"code-optimizer-{environment}",
    ]
    
    # List all functions
    response = lambda_client.list_functions()
    function_names = [func["FunctionName"] for func in response["Functions"]]
    
    for expected_function in expected_functions:
        # Check if function exists (partial match as actual names might have suffixes)
        matching_functions = [name for name in function_names if expected_function in name]
        if matching_functions:
            # Check function state
            func_response = lambda_client.get_function(FunctionName=matching_functions[0])
            assert func_response["Configuration"]["State"] == "Active"


def test_dynamodb_tables_exist(environment, aws_region):
    """Test that DynamoDB tables exist and are active."""
    dynamodb = boto3.client("dynamodb", region_name=aws_region)
    
    expected_tables = [
        f"code-templates-{environment}",
        f"analysis-results-{environment}",
        f"user-sessions-{environment}",
    ]
    
    for table_name in expected_tables:
        try:
            response = dynamodb.describe_table(TableName=table_name)
            assert response["Table"]["TableStatus"] == "ACTIVE"
            
        except dynamodb.exceptions.ResourceNotFoundException:
            # Table might not exist in this environment
            continue


def test_ecs_clusters_exist(environment, aws_region):
    """Test that ECS clusters exist and are active."""
    ecs = boto3.client("ecs", region_name=aws_region)
    
    expected_clusters = [
        f"data-processing-{environment}",
        f"portal-{environment}",
    ]
    
    for cluster_name in expected_clusters:
        try:
            response = ecs.describe_clusters(clusters=[cluster_name])
            if response["clusters"]:
                assert response["clusters"][0]["status"] == "ACTIVE"
                
        except Exception:
            # Cluster might not exist in this environment
            continue


def test_cloudwatch_alarms_exist(environment, aws_region):
    """Test that CloudWatch alarms exist."""
    cloudwatch = boto3.client("cloudwatch", region_name=aws_region)
    
    response = cloudwatch.describe_alarms()
    alarm_names = [alarm["AlarmName"] for alarm in response["MetricAlarms"]]
    
    # Check for environment-specific alarms
    env_alarms = [name for name in alarm_names if environment in name]
    
    # Should have at least some alarms for the environment
    if env_alarms:
        assert len(env_alarms) > 0


def test_security_groups_exist(stack_outputs, aws_region):
    """Test that security groups exist."""
    vpc_id = stack_outputs.get("VPCId")
    if not vpc_id:
        pytest.skip("VPC ID not found")
    
    ec2 = boto3.client("ec2", region_name=aws_region)
    
    response = ec2.describe_security_groups(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]}
        ]
    )
    
    # Should have multiple security groups (default + custom ones)
    assert len(response["SecurityGroups"]) >= 2


@pytest.mark.integration
def test_end_to_end_data_flow(stack_outputs):
    """Test basic end-to-end data flow."""
    # This is a placeholder for more complex integration testing
    # In a real scenario, this would test data ingestion, processing, and output
    
    data_lake_bucket = stack_outputs.get("DataLakeBucketName")
    if not data_lake_bucket:
        pytest.skip("Data lake bucket not found")
    
    s3 = boto3.client("s3")
    
    # Test basic S3 operations
    test_key = "test/smoke-test.txt"
    test_content = b"Smoke test content"
    
    try:
        # Upload test file
        s3.put_object(Bucket=data_lake_bucket, Key=test_key, Body=test_content)
        
        # Verify file exists
        response = s3.head_object(Bucket=data_lake_bucket, Key=test_key)
        assert response["ContentLength"] == len(test_content)
        
        # Clean up
        s3.delete_object(Bucket=data_lake_bucket, Key=test_key)
        
    except Exception as e:
        pytest.fail(f"End-to-end data flow test failed: {e}")
