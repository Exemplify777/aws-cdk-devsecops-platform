"""
Unit tests for convention enforcement utilities.

This module tests the naming conventions, tagging strategies, and validation
framework to ensure consistent and compliant resource management.
"""

import pytest
from typing import Dict, Any

from infrastructure.constructs.common.conventions import (
    ResourceNaming,
    ResourceTagging,
    SecurityValidator,
    ComplianceValidator,
    CostOptimizationValidator,
    ValidationResult,
    ValidationSeverity,
    validate_construct_props
)


class TestResourceNaming:
    """Test cases for ResourceNaming utility."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.naming = ResourceNaming(
            project="dso",
            environment="prod",
            service="data",
            region="us-east-1"
        )
    
    def test_s3_bucket_naming(self):
        """Test S3 bucket naming conventions."""
        bucket_name = self.naming.s3_bucket("ingestion")
        assert bucket_name == "dso-prod-data-ingestion-us-east-1"
        
        # Test with identifier
        bucket_name = self.naming.s3_bucket("ingestion", identifier="001")
        assert bucket_name == "dso-prod-data-ingestion-001-us-east-1"
    
    def test_lambda_function_naming(self):
        """Test Lambda function naming conventions."""
        function_name = self.naming.lambda_function("processor")
        assert function_name == "dso-prod-data-processor"
        
        # Test with identifier
        function_name = self.naming.lambda_function("processor", identifier="v2")
        assert function_name == "dso-prod-data-processor-v2"
    
    def test_dynamodb_table_naming(self):
        """Test DynamoDB table naming conventions."""
        table_name = self.naming.dynamodb_table("metadata")
        assert table_name == "dso-prod-data-metadata"
    
    def test_rds_instance_naming(self):
        """Test RDS instance naming conventions."""
        instance_name = self.naming.rds_instance("postgres")
        assert instance_name == "dso-prod-data-postgres-primary"
        
        # Test with custom role
        instance_name = self.naming.rds_instance("postgres", "replica")
        assert instance_name == "dso-prod-data-postgres-replica"
    
    def test_sqs_queue_naming(self):
        """Test SQS queue naming conventions."""
        queue_name = self.naming.sqs_queue("processing")
        assert queue_name == "dso-prod-data-processing"
        
        # Test FIFO queue
        fifo_queue_name = self.naming.sqs_queue("processing", is_fifo=True)
        assert fifo_queue_name == "dso-prod-data-processing.fifo"
    
    def test_sns_topic_naming(self):
        """Test SNS topic naming conventions."""
        topic_name = self.naming.sns_topic("alerts")
        assert topic_name == "dso-prod-data-alerts"
        
        # Test FIFO topic
        fifo_topic_name = self.naming.sns_topic("alerts", is_fifo=True)
        assert fifo_topic_name == "dso-prod-data-alerts.fifo"
    
    def test_iam_role_naming(self):
        """Test IAM role naming conventions."""
        role_name = self.naming.iam_role("lambda-execution")
        assert role_name == "dso-prod-data-lambda-execution-role"
    
    def test_kms_key_alias(self):
        """Test KMS key alias naming conventions."""
        alias_name = self.naming.kms_key_alias("encryption")
        assert alias_name == "alias/dso-prod-data-encryption-key"
    
    def test_invalid_project_name(self):
        """Test validation of invalid project names."""
        with pytest.raises(ValueError, match="Invalid project identifier"):
            ResourceNaming("INVALID_PROJECT", "prod", "data")
    
    def test_invalid_environment(self):
        """Test validation of invalid environments."""
        with pytest.raises(ValueError, match="Invalid environment"):
            ResourceNaming("dso", "invalid", "data")
    
    def test_invalid_service(self):
        """Test validation of invalid services."""
        with pytest.raises(ValueError, match="Invalid service"):
            ResourceNaming("dso", "prod", "invalid")
    
    def test_s3_bucket_name_too_long(self):
        """Test S3 bucket name length validation."""
        # This should fail at ResourceNaming creation due to invalid project name
        with pytest.raises(ValueError, match="Invalid project identifier"):
            ResourceNaming("verylongproject", "prod", "data", "us-east-1")


class TestResourceTagging:
    """Test cases for ResourceTagging utility."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.tagging = ResourceTagging(
            environment="prod",
            project="devsecops-platform",
            owner="platform-team",
            cost_center="CC-1234"
        )
    
    def test_required_tags(self):
        """Test required tags generation."""
        required_tags = self.tagging.get_required_tags()
        
        assert required_tags["Environment"] == "prod"
        assert required_tags["Project"] == "devsecops-platform"
        assert required_tags["Owner"] == "platform-team"
        assert required_tags["CostCenter"] == "CC-1234"
        assert required_tags["CreatedBy"] == "cdk"
        assert "CreatedDate" in required_tags
    
    def test_complete_tags(self):
        """Test complete tag set generation."""
        tags = self.tagging.get_tags(
            application="data-ingestion",
            component="lambda-processor",
            data_classification="confidential",
            pii_data=True,
            compliance_framework="gdpr"
        )
        
        # Check required tags
        assert tags["Environment"] == "prod"
        assert tags["Application"] == "data-ingestion"
        assert tags["Component"] == "lambda-processor"
        
        # Check optional tags
        assert tags["DataClassification"] == "confidential"
        assert tags["PIIData"] == "true"
        assert tags["ComplianceFramework"] == "gdpr"
    
    def test_tag_validation_missing_required(self):
        """Test validation of missing required tags."""
        incomplete_tags = {
            "Environment": "prod",
            "Project": "test"
            # Missing other required tags
        }
        
        results = self.tagging.validate_tags(incomplete_tags)
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        
        assert len(errors) > 0
        assert any("Owner" in error.message for error in errors)
    
    def test_tag_validation_invalid_environment(self):
        """Test validation of invalid environment values."""
        invalid_tags = {
            "Environment": "invalid",
            "Project": "test",
            "Owner": "team",
            "CostCenter": "CC-1234",
            "Application": "app",
            "Component": "comp",
            "CreatedBy": "cdk",
            "CreatedDate": "2024-01-01"
        }
        
        results = self.tagging.validate_tags(invalid_tags)
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        
        assert len(errors) > 0
        assert any("Invalid environment value" in error.message for error in errors)
    
    def test_tag_validation_invalid_cost_center(self):
        """Test validation of invalid cost center format."""
        invalid_tags = {
            "Environment": "prod",
            "Project": "test",
            "Owner": "team",
            "CostCenter": "INVALID",
            "Application": "app",
            "Component": "comp",
            "CreatedBy": "cdk",
            "CreatedDate": "2024-01-01"
        }
        
        results = self.tagging.validate_tags(invalid_tags)
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        
        assert len(errors) > 0
        assert any("Invalid cost center format" in error.message for error in errors)


class TestSecurityValidator:
    """Test cases for SecurityValidator utility."""
    
    def test_valid_cidr_block(self):
        """Test validation of valid CIDR blocks."""
        result = SecurityValidator.validate_cidr_block("10.0.0.0/24")
        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO
    
    def test_invalid_cidr_block(self):
        """Test validation of invalid CIDR blocks."""
        result = SecurityValidator.validate_cidr_block("invalid-cidr")
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
    
    def test_broad_cidr_block_warning(self):
        """Test warning for overly broad CIDR blocks."""
        result = SecurityValidator.validate_cidr_block("10.0.0.0/8")
        assert result.is_valid
        assert result.severity == ValidationSeverity.WARNING
        assert "very broad" in result.message
    
    def test_valid_port_number(self):
        """Test validation of valid port numbers."""
        result = SecurityValidator.validate_port_range(443)
        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO
    
    def test_invalid_port_number(self):
        """Test validation of invalid port numbers."""
        result = SecurityValidator.validate_port_range(70000)
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
    
    def test_insecure_port_warning(self):
        """Test warning for insecure ports."""
        result = SecurityValidator.validate_port_range(80)
        assert result.is_valid
        assert result.severity == ValidationSeverity.WARNING
        assert "HTTP" in result.message
    
    def test_encryption_required_prod(self):
        """Test encryption requirement for production."""
        result = SecurityValidator.validate_encryption_config(False, "prod")
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
    
    def test_encryption_warning_dev(self):
        """Test encryption warning for development."""
        result = SecurityValidator.validate_encryption_config(False, "dev")
        assert result.is_valid
        assert result.severity == ValidationSeverity.WARNING


class TestComplianceValidator:
    """Test cases for ComplianceValidator utility."""
    
    def test_gdpr_data_retention_valid(self):
        """Test valid GDPR data retention."""
        result = ComplianceValidator.validate_data_retention(365, "gdpr")
        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO
    
    def test_gdpr_data_retention_invalid(self):
        """Test invalid GDPR data retention."""
        result = ComplianceValidator.validate_data_retention(400, "gdpr")
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert "GDPR compliance" in result.message
    
    def test_hipaa_data_retention_valid(self):
        """Test valid HIPAA data retention."""
        result = ComplianceValidator.validate_data_retention(2555, "hipaa")
        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO
    
    def test_hipaa_data_retention_invalid(self):
        """Test invalid HIPAA data retention."""
        result = ComplianceValidator.validate_data_retention(365, "hipaa")
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert "HIPAA compliance" in result.message
    
    def test_backup_required_prod(self):
        """Test backup requirement for production."""
        result = ComplianceValidator.validate_backup_requirements(False, "prod")
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
    
    def test_backup_compliance_sox(self):
        """Test backup requirement for SOX compliance."""
        result = ComplianceValidator.validate_backup_requirements(False, "dev", "sox")
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert "SOX compliance" in result.message


class TestCostOptimizationValidator:
    """Test cases for CostOptimizationValidator utility."""
    
    def test_appropriate_instance_size_prod(self):
        """Test appropriate instance size for production."""
        result = CostOptimizationValidator.validate_instance_sizing("t3.medium", "prod")
        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO
    
    def test_oversized_instance_dev(self):
        """Test oversized instance warning for development."""
        result = CostOptimizationValidator.validate_instance_sizing("m5.xlarge", "dev")
        assert result.is_valid
        assert result.severity == ValidationSeverity.WARNING
        assert "may increase costs" in result.message
    
    def test_invalid_instance_type_format(self):
        """Test invalid instance type format."""
        result = CostOptimizationValidator.validate_instance_sizing("invalid", "prod")
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
    
    def test_storage_lifecycle_warning(self):
        """Test storage lifecycle policy warning."""
        result = CostOptimizationValidator.validate_storage_lifecycle(False, "s3")
        assert result.is_valid
        assert result.severity == ValidationSeverity.WARNING
        assert "lifecycle policies" in result.message
    
    def test_storage_lifecycle_optimal(self):
        """Test optimal storage lifecycle configuration."""
        result = CostOptimizationValidator.validate_storage_lifecycle(True, "s3")
        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO


class TestValidationFramework:
    """Test cases for the overall validation framework."""
    
    def test_validate_construct_props_success(self):
        """Test successful construct property validation."""
        
        class MockProps:
            environment = "prod"
            enable_encryption = True
            retention_days = 30
        
        def mock_validator(props):
            return [ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message="Validation passed"
            )]
        
        report = validate_construct_props(
            construct_name="TestConstruct",
            props=MockProps(),
            validators=[mock_validator]
        )
        
        assert report.overall_status
        assert report.construct_name == "TestConstruct"
        assert len(report.results) == 1
    
    def test_validate_construct_props_failure(self):
        """Test failed construct property validation."""
        
        class MockProps:
            environment = "prod"
            enable_encryption = False
        
        def mock_validator(props):
            return [ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Validation failed"
            )]
        
        report = validate_construct_props(
            construct_name="TestConstruct",
            props=MockProps(),
            validators=[mock_validator]
        )
        
        assert not report.overall_status
        assert len(report.get_errors()) == 1
    
    def test_validation_report_summary(self):
        """Test validation report summary generation."""
        from infrastructure.constructs.common.conventions import ValidationReport

        results = [
            ValidationResult(True, ValidationSeverity.INFO, "Info message"),
            ValidationResult(True, ValidationSeverity.WARNING, "Warning message"),
            ValidationResult(False, ValidationSeverity.ERROR, "Error message"),
            ValidationResult(False, ValidationSeverity.ERROR, "Another error")
        ]

        report = ValidationReport(
            construct_name="TestConstruct",
            overall_status=False,
            results=results
        )
        
        summary = report.summary
        assert summary["INFO"] == 1
        assert summary["WARNING"] == 1
        assert summary["ERROR"] == 2
        
        errors = report.get_errors()
        assert len(errors) == 2
        
        warnings = report.get_warnings()
        assert len(warnings) == 1


if __name__ == "__main__":
    pytest.main([__file__])
