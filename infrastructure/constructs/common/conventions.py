"""
Convention Enforcement Utilities for DevSecOps Platform.

This module provides utilities for enforcing naming conventions, tagging strategies,
and validation rules across all constructs in the platform.
"""

import re
import ipaddress
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ValidationSeverity(Enum):
    """Validation result severity levels."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    severity: ValidationSeverity
    message: str
    property_name: Optional[str] = None
    suggested_fix: Optional[str] = None
    documentation_link: Optional[str] = None


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    construct_name: str
    overall_status: bool
    results: List[ValidationResult]
    
    @property
    def summary(self) -> Dict[str, int]:
        """Get summary count by severity."""
        return {
            "ERROR": len([r for r in self.results if r.severity == ValidationSeverity.ERROR]),
            "WARNING": len([r for r in self.results if r.severity == ValidationSeverity.WARNING]),
            "INFO": len([r for r in self.results if r.severity == ValidationSeverity.INFO])
        }
    
    def get_errors(self) -> List[ValidationResult]:
        """Get all error-level validation results."""
        return [r for r in self.results if r.severity == ValidationSeverity.ERROR]
    
    def get_warnings(self) -> List[ValidationResult]:
        """Get all warning-level validation results."""
        return [r for r in self.results if r.severity == ValidationSeverity.WARNING]


class ResourceNaming:
    """Utility class for generating standardized AWS resource names."""
    
    def __init__(self, project: str, environment: str, service: str, region: Optional[str] = None):
        """
        Initialize resource naming utility.
        
        Args:
            project: Project identifier (3-8 chars)
            environment: Environment (dev, staging, prod, sandbox, dr)
            service: Service category (data, ml, api, infra, msg, sec, mon)
            region: AWS region (optional, used for global resources)
        """
        self.project = self._validate_project(project)
        self.environment = self._validate_environment(environment)
        self.service = self._validate_service(service)
        self.region = region
    
    def _validate_project(self, project: str) -> str:
        """Validate project identifier."""
        if not re.match(r"^[a-z0-9-]{3,8}$", project):
            raise ValueError(f"Invalid project identifier: {project}. Must be 3-8 chars, lowercase letters, numbers, hyphens only.")
        return project
    
    def _validate_environment(self, environment: str) -> str:
        """Validate environment identifier."""
        valid_environments = ["dev", "staging", "prod", "sandbox", "dr"]
        if environment not in valid_environments:
            raise ValueError(f"Invalid environment: {environment}. Must be one of {valid_environments}")
        return environment
    
    def _validate_service(self, service: str) -> str:
        """Validate service identifier."""
        valid_services = ["data", "ml", "api", "infra", "msg", "sec", "mon"]
        if service not in valid_services:
            raise ValueError(f"Invalid service: {service}. Must be one of {valid_services}")
        return service
    
    def _generate_base_name(self, component: str, identifier: Optional[str] = None) -> str:
        """Generate base resource name."""
        parts = [self.project, self.environment, self.service, component]
        if identifier:
            parts.append(identifier)
        return "-".join(parts)
    
    def s3_bucket(self, component: str, region: Optional[str] = None, identifier: Optional[str] = None) -> str:
        """Generate S3 bucket name."""
        base_name = self._generate_base_name(component, identifier)
        if region or self.region:
            base_name += f"-{region or self.region}"
        
        # Validate S3 naming rules
        if len(base_name) > 63:
            raise ValueError(f"S3 bucket name too long: {base_name} (max 63 chars)")
        if not re.match(r"^[a-z0-9-]+$", base_name):
            raise ValueError(f"Invalid S3 bucket name: {base_name}")
        if base_name.startswith("-") or base_name.endswith("-"):
            raise ValueError(f"S3 bucket name cannot start or end with hyphen: {base_name}")
        
        return base_name
    
    def lambda_function(self, function_name: str, identifier: Optional[str] = None) -> str:
        """Generate Lambda function name."""
        name = self._generate_base_name(function_name, identifier)
        
        # Validate Lambda naming rules
        if len(name) > 64:
            raise ValueError(f"Lambda function name too long: {name} (max 64 chars)")
        if not re.match(r"^[a-zA-Z0-9-_]+$", name):
            raise ValueError(f"Invalid Lambda function name: {name}")
        
        return name
    
    def dynamodb_table(self, table_purpose: str, identifier: Optional[str] = None) -> str:
        """Generate DynamoDB table name."""
        name = self._generate_base_name(table_purpose, identifier)
        
        # Validate DynamoDB naming rules
        if len(name) > 255:
            raise ValueError(f"DynamoDB table name too long: {name} (max 255 chars)")
        if not re.match(r"^[a-zA-Z0-9-_.]+$", name):
            raise ValueError(f"Invalid DynamoDB table name: {name}")
        
        return name
    
    def rds_instance(self, db_type: str, role: str = "primary") -> str:
        """Generate RDS instance identifier."""
        name = self._generate_base_name(db_type, role)
        
        # Validate RDS naming rules
        if len(name) > 63:
            raise ValueError(f"RDS instance name too long: {name} (max 63 chars)")
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9-]*$", name):
            raise ValueError(f"Invalid RDS instance name: {name}")
        if name.endswith("-"):
            raise ValueError(f"RDS instance name cannot end with hyphen: {name}")
        
        return name
    
    def ecs_service(self, component: str, identifier: Optional[str] = None) -> str:
        """Generate ECS service name."""
        name = self._generate_base_name(component, identifier)
        
        # Validate ECS naming rules
        if len(name) > 255:
            raise ValueError(f"ECS service name too long: {name} (max 255 chars)")
        if not re.match(r"^[a-zA-Z0-9-_]+$", name):
            raise ValueError(f"Invalid ECS service name: {name}")
        
        return name
    
    def kinesis_stream(self, stream_purpose: str, identifier: Optional[str] = None) -> str:
        """Generate Kinesis stream name."""
        name = self._generate_base_name(stream_purpose, identifier)
        
        # Validate Kinesis naming rules
        if len(name) > 128:
            raise ValueError(f"Kinesis stream name too long: {name} (max 128 chars)")
        if not re.match(r"^[a-zA-Z0-9-_.]+$", name):
            raise ValueError(f"Invalid Kinesis stream name: {name}")
        
        return name
    
    def sqs_queue(self, queue_purpose: str, is_fifo: bool = False, identifier: Optional[str] = None) -> str:
        """Generate SQS queue name."""
        name = self._generate_base_name(queue_purpose, identifier)
        if is_fifo:
            name += ".fifo"
        
        # Validate SQS naming rules
        if len(name) > 80:
            raise ValueError(f"SQS queue name too long: {name} (max 80 chars)")
        if not re.match(r"^[a-zA-Z0-9-_]+(\\.fifo)?$", name):
            raise ValueError(f"Invalid SQS queue name: {name}")
        
        return name
    
    def sns_topic(self, topic_purpose: str, is_fifo: bool = False, identifier: Optional[str] = None) -> str:
        """Generate SNS topic name."""
        name = self._generate_base_name(topic_purpose, identifier)
        if is_fifo:
            name += ".fifo"
        
        # Validate SNS naming rules
        if len(name) > 256:
            raise ValueError(f"SNS topic name too long: {name} (max 256 chars)")
        if not re.match(r"^[a-zA-Z0-9-_]+(\\.fifo)?$", name):
            raise ValueError(f"Invalid SNS topic name: {name}")
        
        return name
    
    def cloudwatch_log_group(self, service_type: str, component: str) -> str:
        """Generate CloudWatch log group name."""
        name = f"/aws/{service_type}/{self._generate_base_name(component)}"
        
        # Validate CloudWatch log group naming rules
        if len(name) > 512:
            raise ValueError(f"CloudWatch log group name too long: {name} (max 512 chars)")
        if not re.match(r"^[a-zA-Z0-9-_./]+$", name):
            raise ValueError(f"Invalid CloudWatch log group name: {name}")
        
        return name
    
    def iam_role(self, role_purpose: str, identifier: Optional[str] = None) -> str:
        """Generate IAM role name."""
        name = self._generate_base_name(role_purpose, identifier) + "-role"
        
        # Validate IAM role naming rules
        if len(name) > 64:
            raise ValueError(f"IAM role name too long: {name} (max 64 chars)")
        if not re.match(r"^[a-zA-Z0-9+=,.@-]+$", name):
            raise ValueError(f"Invalid IAM role name: {name}")
        
        return name
    
    def kms_key_alias(self, purpose: str, identifier: Optional[str] = None) -> str:
        """Generate KMS key alias."""
        name = f"alias/{self._generate_base_name(purpose, identifier)}-key"
        
        # Validate KMS alias naming rules
        if len(name) > 256:
            raise ValueError(f"KMS key alias too long: {name} (max 256 chars)")
        if not re.match(r"^alias/[a-zA-Z0-9-_/]+$", name):
            raise ValueError(f"Invalid KMS key alias: {name}")
        
        return name


class ResourceTagging:
    """Utility class for applying standardized resource tags."""
    
    def __init__(self, environment: str, project: str, owner: str, cost_center: str):
        """
        Initialize resource tagging utility.
        
        Args:
            environment: Environment identifier
            project: Project identifier
            owner: Resource owner (team or email)
            cost_center: Cost center code
        """
        self.environment = environment
        self.project = project
        self.owner = owner
        self.cost_center = cost_center
        self.created_date = datetime.now().strftime("%Y-%m-%d")
    
    def get_required_tags(self) -> Dict[str, str]:
        """Get required tags for all resources."""
        return {
            "Environment": self.environment,
            "Project": self.project,
            "Owner": self.owner,
            "CostCenter": self.cost_center,
            "CreatedBy": "cdk",
            "CreatedDate": self.created_date
        }
    
    def get_tags(self, 
                 application: str,
                 component: str,
                 data_classification: Optional[str] = None,
                 pii_data: Optional[bool] = None,
                 compliance_framework: Optional[str] = None,
                 backup_schedule: Optional[str] = None,
                 monitoring_level: Optional[str] = None,
                 **additional_tags) -> Dict[str, str]:
        """
        Get complete tag set for a resource.
        
        Args:
            application: Application name
            component: Component type
            data_classification: Data sensitivity level
            pii_data: Contains PII data
            compliance_framework: Compliance requirements
            backup_schedule: Backup frequency
            monitoring_level: Monitoring intensity
            **additional_tags: Additional custom tags
        """
        tags = self.get_required_tags()
        tags.update({
            "Application": application,
            "Component": component
        })
        
        # Add conditional tags
        if data_classification:
            tags["DataClassification"] = data_classification
        if pii_data is not None:
            tags["PIIData"] = str(pii_data).lower()
        if compliance_framework:
            tags["ComplianceFramework"] = compliance_framework
        if backup_schedule:
            tags["BackupSchedule"] = backup_schedule
        if monitoring_level:
            tags["MonitoringLevel"] = monitoring_level
        
        # Add additional tags
        tags.update(additional_tags)
        
        return tags
    
    def validate_tags(self, tags: Dict[str, str]) -> List[ValidationResult]:
        """Validate tag compliance."""
        results = []
        required_tags = ["Environment", "Project", "Owner", "CostCenter", "Application", "Component", "CreatedBy", "CreatedDate"]
        
        # Check required tags
        for tag in required_tags:
            if tag not in tags:
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Required tag '{tag}' is missing",
                    property_name=tag,
                    suggested_fix=f"Add {tag} tag with appropriate value"
                ))
        
        # Validate tag values
        if "Environment" in tags:
            valid_environments = ["dev", "staging", "prod", "sandbox", "dr"]
            if tags["Environment"] not in valid_environments:
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid environment value: {tags['Environment']}",
                    property_name="Environment",
                    suggested_fix=f"Use one of: {valid_environments}"
                ))
        
        if "CostCenter" in tags:
            if not re.match(r"^CC-[0-9]{4}$", tags["CostCenter"]):
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid cost center format: {tags['CostCenter']}",
                    property_name="CostCenter",
                    suggested_fix="Use format: CC-XXXX (e.g., CC-1234)"
                ))
        
        return results


class SecurityValidator:
    """Utility class for security validation."""
    
    @staticmethod
    def validate_cidr_block(cidr: str) -> ValidationResult:
        """Validate CIDR block format and security."""
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            
            # Check for overly broad CIDR blocks
            if network.num_addresses > 65536:  # /16 or larger
                return ValidationResult(
                    is_valid=True,
                    severity=ValidationSeverity.WARNING,
                    message=f"CIDR block {cidr} is very broad ({network.num_addresses} addresses)",
                    suggested_fix="Consider using a smaller CIDR block for better security"
                )
            
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message=f"Valid CIDR block: {cidr}"
            )
            
        except ValueError as e:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid CIDR block: {cidr} - {str(e)}",
                suggested_fix="Use valid CIDR notation (e.g., 10.0.0.0/16)"
            )
    
    @staticmethod
    def validate_port_range(port: int, protocol: str = "tcp") -> ValidationResult:
        """Validate port number and security implications."""
        if port < 1 or port > 65535:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid port number: {port}",
                suggested_fix="Use port number between 1 and 65535"
            )
        
        # Check for well-known insecure ports
        insecure_ports = {21: "FTP", 23: "Telnet", 80: "HTTP", 135: "RPC", 139: "NetBIOS", 445: "SMB"}
        if port in insecure_ports:
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.WARNING,
                message=f"Port {port} ({insecure_ports[port]}) may have security implications",
                suggested_fix="Consider using secure alternatives (e.g., HTTPS instead of HTTP)"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message=f"Valid port: {port}"
        )
    
    @staticmethod
    def validate_encryption_config(encryption_enabled: bool, environment: str) -> ValidationResult:
        """Validate encryption configuration."""
        if not encryption_enabled:
            severity = ValidationSeverity.ERROR if environment == "prod" else ValidationSeverity.WARNING
            return ValidationResult(
                is_valid=environment != "prod",
                severity=severity,
                message="Encryption is not enabled",
                suggested_fix="Enable encryption for security compliance"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="Encryption is properly configured"
        )


class ComplianceValidator:
    """Utility class for compliance validation."""
    
    @staticmethod
    def validate_data_retention(retention_days: int, compliance_framework: Optional[str] = None) -> ValidationResult:
        """Validate data retention policy."""
        if compliance_framework == "gdpr" and retention_days > 365:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"GDPR compliance requires data retention <= 365 days, got {retention_days}",
                suggested_fix="Reduce retention period to comply with GDPR requirements"
            )
        
        if compliance_framework == "hipaa" and retention_days < 2555:  # 7 years
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"HIPAA compliance requires data retention >= 7 years, got {retention_days} days",
                suggested_fix="Increase retention period to comply with HIPAA requirements"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message=f"Data retention policy compliant: {retention_days} days"
        )
    
    @staticmethod
    def validate_backup_requirements(backup_enabled: bool, environment: str, compliance_framework: Optional[str] = None) -> ValidationResult:
        """Validate backup requirements."""
        if not backup_enabled and environment == "prod":
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Backup is required for production resources",
                suggested_fix="Enable backup for production environment"
            )
        
        if compliance_framework in ["sox", "hipaa"] and not backup_enabled:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{compliance_framework.upper()} compliance requires backup to be enabled",
                suggested_fix="Enable backup for compliance requirements"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="Backup requirements satisfied"
        )


class CostOptimizationValidator:
    """Utility class for cost optimization validation."""
    
    @staticmethod
    def validate_instance_sizing(instance_type: str, environment: str) -> ValidationResult:
        """Validate instance sizing for cost optimization."""
        # Extract instance family and size
        parts = instance_type.split(".")
        if len(parts) != 2:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid instance type format: {instance_type}",
                suggested_fix="Use valid AWS instance type format (e.g., t3.medium)"
            )
        
        family, size = parts
        large_sizes = ["large", "xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge", "16xlarge", "24xlarge"]
        
        if environment in ["dev", "staging"] and size in large_sizes:
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.WARNING,
                message=f"Large instance type {instance_type} in {environment} environment may increase costs",
                suggested_fix="Consider using smaller instance types for non-production environments"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message=f"Instance type {instance_type} is appropriate for {environment}"
        )
    
    @staticmethod
    def validate_storage_lifecycle(lifecycle_enabled: bool, storage_type: str) -> ValidationResult:
        """Validate storage lifecycle policies."""
        if storage_type in ["s3", "efs"] and not lifecycle_enabled:
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.WARNING,
                message="Storage lifecycle policies not configured",
                suggested_fix="Configure lifecycle policies to optimize storage costs"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="Storage lifecycle configuration is optimal"
        )


def validate_construct_props(construct_name: str, props: Any, validators: List[Callable] = None) -> ValidationReport:
    """
    Validate construct properties using multiple validators.
    
    Args:
        construct_name: Name of the construct being validated
        props: Construct properties to validate
        validators: List of validator functions
    
    Returns:
        ValidationReport with all validation results
    """
    if validators is None:
        validators = []
    
    results = []
    
    # Run all validators
    for validator in validators:
        try:
            validator_results = validator(props)
            if isinstance(validator_results, list):
                results.extend(validator_results)
            else:
                results.append(validator_results)
        except Exception as e:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Validator error: {str(e)}",
                suggested_fix="Check validator implementation"
            ))
    
    # Determine overall status (no errors)
    overall_status = all(r.is_valid for r in results if r.severity == ValidationSeverity.ERROR)
    
    return ValidationReport(
        construct_name=construct_name,
        overall_status=overall_status,
        results=results
    )
