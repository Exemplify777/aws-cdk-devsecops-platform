# Validation Framework

This document defines the comprehensive validation framework for the DevSecOps Platform, ensuring all constructs and resources meet enterprise-grade standards for security, compliance, performance, and operational excellence.

## Overview

The validation framework provides:
- **Input Validation**: Comprehensive validation of all construct properties
- **Security Validation**: Security best practices and compliance checks
- **Compliance Validation**: Regulatory framework adherence
- **Cost Optimization**: Resource efficiency and cost management
- **Operational Validation**: Performance and reliability standards

## Validation Layers

### 1. Input Validation Layer

Validates all construct properties before resource creation.

#### Property Type Validation

```python
@dataclass
class ValidationRule:
    property_name: str
    data_type: type
    required: bool = True
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[Callable] = None
```

#### Common Validation Rules

| Property Type | Validation Rules | Example |
|---------------|------------------|---------|
| `environment` | `^(dev\|staging\|prod\|sandbox\|dr)$` | `prod` |
| `instance_type` | AWS instance type pattern | `t3.medium` |
| `port_number` | Range: 1-65535 | `443` |
| `cidr_block` | Valid CIDR notation | `10.0.0.0/16` |
| `retention_days` | Range: 1-3653 | `30` |
| `memory_size` | Range: 128-10240 MB | `1024` |
| `timeout_seconds` | Range: 1-900 | `300` |

#### String Validation Examples

```python
# Environment validation
environment_rule = ValidationRule(
    property_name="environment",
    data_type=str,
    required=True,
    pattern=r"^(dev|staging|prod|sandbox|dr)$",
    allowed_values=["dev", "staging", "prod", "sandbox", "dr"]
)

# Instance type validation
instance_type_rule = ValidationRule(
    property_name="instance_type",
    data_type=str,
    required=True,
    pattern=r"^[a-z][0-9]+[a-z]*\.[a-z0-9]+$"
)

# CIDR block validation
cidr_rule = ValidationRule(
    property_name="cidr_block",
    data_type=str,
    required=True,
    custom_validator=validate_cidr_block
)
```

#### Numeric Validation Examples

```python
# Port number validation
port_rule = ValidationRule(
    property_name="port",
    data_type=int,
    required=True,
    min_value=1,
    max_value=65535
)

# Memory size validation
memory_rule = ValidationRule(
    property_name="memory_size",
    data_type=int,
    required=True,
    min_value=128,
    max_value=10240
)

# Retention period validation
retention_rule = ValidationRule(
    property_name="retention_days",
    data_type=int,
    required=True,
    min_value=1,
    max_value=3653  # 10 years
)
```

### 2. Security Validation Layer

Ensures all resources follow security best practices.

#### Encryption Validation

```python
class EncryptionValidator:
    def validate_encryption_at_rest(self, resource_config: Dict) -> ValidationResult:
        """Validate encryption at rest configuration."""
        checks = [
            self._check_kms_encryption_enabled(resource_config),
            self._check_customer_managed_keys(resource_config),
            self._check_key_rotation_enabled(resource_config)
        ]
        return self._aggregate_results(checks)
    
    def validate_encryption_in_transit(self, resource_config: Dict) -> ValidationResult:
        """Validate encryption in transit configuration."""
        checks = [
            self._check_tls_version(resource_config),
            self._check_ssl_certificate(resource_config),
            self._check_secure_protocols(resource_config)
        ]
        return self._aggregate_results(checks)
```

#### IAM Policy Validation

```python
class IAMValidator:
    def validate_policy_document(self, policy: Dict) -> ValidationResult:
        """Validate IAM policy document."""
        checks = [
            self._check_least_privilege(policy),
            self._check_wildcard_resources(policy),
            self._check_admin_permissions(policy),
            self._check_cross_account_access(policy),
            self._check_condition_statements(policy)
        ]
        return self._aggregate_results(checks)
    
    def validate_role_trust_policy(self, trust_policy: Dict) -> ValidationResult:
        """Validate IAM role trust policy."""
        checks = [
            self._check_trusted_principals(trust_policy),
            self._check_external_id_requirement(trust_policy),
            self._check_mfa_requirement(trust_policy)
        ]
        return self._aggregate_results(checks)
```

#### Network Security Validation

```python
class NetworkSecurityValidator:
    def validate_security_group(self, sg_config: Dict) -> ValidationResult:
        """Validate security group configuration."""
        checks = [
            self._check_ingress_rules(sg_config),
            self._check_egress_rules(sg_config),
            self._check_port_ranges(sg_config),
            self._check_source_restrictions(sg_config)
        ]
        return self._aggregate_results(checks)
    
    def validate_vpc_configuration(self, vpc_config: Dict) -> ValidationResult:
        """Validate VPC configuration."""
        checks = [
            self._check_private_subnets(vpc_config),
            self._check_nat_gateways(vpc_config),
            self._check_flow_logs(vpc_config),
            self._check_dns_settings(vpc_config)
        ]
        return self._aggregate_results(checks)
```

### 3. Compliance Validation Layer

Validates adherence to regulatory frameworks.

#### SOC 2 Compliance Validation

```python
class SOC2Validator:
    def validate_security_controls(self, resource_config: Dict) -> ValidationResult:
        """Validate SOC 2 security controls."""
        checks = [
            self._check_access_controls(resource_config),
            self._check_encryption_requirements(resource_config),
            self._check_monitoring_controls(resource_config),
            self._check_backup_controls(resource_config),
            self._check_incident_response(resource_config)
        ]
        return self._aggregate_results(checks)
    
    def validate_availability_controls(self, resource_config: Dict) -> ValidationResult:
        """Validate SOC 2 availability controls."""
        checks = [
            self._check_redundancy(resource_config),
            self._check_disaster_recovery(resource_config),
            self._check_capacity_planning(resource_config),
            self._check_performance_monitoring(resource_config)
        ]
        return self._aggregate_results(checks)
```

#### GDPR Compliance Validation

```python
class GDPRValidator:
    def validate_data_protection(self, resource_config: Dict) -> ValidationResult:
        """Validate GDPR data protection requirements."""
        checks = [
            self._check_data_encryption(resource_config),
            self._check_data_retention(resource_config),
            self._check_data_portability(resource_config),
            self._check_right_to_erasure(resource_config),
            self._check_consent_management(resource_config)
        ]
        return self._aggregate_results(checks)
    
    def validate_privacy_by_design(self, resource_config: Dict) -> ValidationResult:
        """Validate privacy by design principles."""
        checks = [
            self._check_data_minimization(resource_config),
            self._check_purpose_limitation(resource_config),
            self._check_storage_limitation(resource_config),
            self._check_transparency(resource_config)
        ]
        return self._aggregate_results(checks)
```

#### HIPAA Compliance Validation

```python
class HIPAAValidator:
    def validate_safeguards(self, resource_config: Dict) -> ValidationResult:
        """Validate HIPAA safeguards."""
        checks = [
            self._check_administrative_safeguards(resource_config),
            self._check_physical_safeguards(resource_config),
            self._check_technical_safeguards(resource_config),
            self._check_audit_controls(resource_config)
        ]
        return self._aggregate_results(checks)
```

### 4. Cost Optimization Validation Layer

Ensures resources are cost-optimized.

#### Resource Sizing Validation

```python
class CostOptimizationValidator:
    def validate_resource_sizing(self, resource_config: Dict) -> ValidationResult:
        """Validate resource sizing for cost optimization."""
        checks = [
            self._check_instance_right_sizing(resource_config),
            self._check_storage_optimization(resource_config),
            self._check_reserved_capacity(resource_config),
            self._check_spot_instance_usage(resource_config)
        ]
        return self._aggregate_results(checks)
    
    def validate_lifecycle_policies(self, resource_config: Dict) -> ValidationResult:
        """Validate lifecycle policies for cost optimization."""
        checks = [
            self._check_s3_lifecycle_rules(resource_config),
            self._check_log_retention_policies(resource_config),
            self._check_backup_retention(resource_config),
            self._check_auto_scaling_policies(resource_config)
        ]
        return self._aggregate_results(checks)
```

### 5. Operational Validation Layer

Validates operational excellence requirements.

#### Monitoring Validation

```python
class MonitoringValidator:
    def validate_monitoring_configuration(self, resource_config: Dict) -> ValidationResult:
        """Validate monitoring configuration."""
        checks = [
            self._check_cloudwatch_metrics(resource_config),
            self._check_alarm_configuration(resource_config),
            self._check_log_aggregation(resource_config),
            self._check_distributed_tracing(resource_config)
        ]
        return self._aggregate_results(checks)
    
    def validate_alerting_configuration(self, resource_config: Dict) -> ValidationResult:
        """Validate alerting configuration."""
        checks = [
            self._check_alert_thresholds(resource_config),
            self._check_notification_channels(resource_config),
            self._check_escalation_policies(resource_config),
            self._check_alert_suppression(resource_config)
        ]
        return self._aggregate_results(checks)
```

#### Backup and Recovery Validation

```python
class BackupValidator:
    def validate_backup_strategy(self, resource_config: Dict) -> ValidationResult:
        """Validate backup strategy."""
        checks = [
            self._check_backup_frequency(resource_config),
            self._check_backup_retention(resource_config),
            self._check_cross_region_backup(resource_config),
            self._check_backup_encryption(resource_config),
            self._check_restore_testing(resource_config)
        ]
        return self._aggregate_results(checks)
```

## Validation Result Structure

```python
@dataclass
class ValidationResult:
    is_valid: bool
    severity: str  # ERROR, WARNING, INFO
    message: str
    property_name: Optional[str] = None
    suggested_fix: Optional[str] = None
    documentation_link: Optional[str] = None
    
@dataclass
class ValidationReport:
    construct_name: str
    overall_status: bool
    results: List[ValidationResult]
    summary: Dict[str, int]  # Count by severity
    
    def get_errors(self) -> List[ValidationResult]:
        return [r for r in self.results if r.severity == "ERROR"]
    
    def get_warnings(self) -> List[ValidationResult]:
        return [r for r in self.results if r.severity == "WARNING"]
```

## Validation Examples

### S3 Bucket Validation

```python
def validate_s3_bucket_config(props: S3ConstructProps) -> ValidationReport:
    """Validate S3 bucket configuration."""
    validators = [
        InputValidator(),
        EncryptionValidator(),
        ComplianceValidator(),
        CostOptimizationValidator()
    ]
    
    results = []
    for validator in validators:
        results.extend(validator.validate(props))
    
    return ValidationReport(
        construct_name="S3Bucket",
        overall_status=all(r.is_valid for r in results if r.severity == "ERROR"),
        results=results,
        summary={
            "ERROR": len([r for r in results if r.severity == "ERROR"]),
            "WARNING": len([r for r in results if r.severity == "WARNING"]),
            "INFO": len([r for r in results if r.severity == "INFO"])
        }
    )
```

### Lambda Function Validation

```python
def validate_lambda_config(props: LambdaConstructProps) -> ValidationReport:
    """Validate Lambda function configuration."""
    results = []
    
    # Input validation
    if props.memory_size < 128 or props.memory_size > 10240:
        results.append(ValidationResult(
            is_valid=False,
            severity="ERROR",
            message="Memory size must be between 128 and 10240 MB",
            property_name="memory_size",
            suggested_fix="Set memory_size to a value between 128 and 10240"
        ))
    
    # Security validation
    if not props.enable_encryption:
        results.append(ValidationResult(
            is_valid=False,
            severity="ERROR",
            message="Encryption must be enabled for Lambda functions",
            property_name="enable_encryption",
            suggested_fix="Set enable_encryption=True"
        ))
    
    # Cost optimization validation
    if props.timeout_seconds > 300 and props.memory_size > 1024:
        results.append(ValidationResult(
            is_valid=True,
            severity="WARNING",
            message="High memory and timeout combination may increase costs",
            property_name="timeout_seconds",
            suggested_fix="Consider optimizing function performance or reducing timeout"
        ))
    
    return ValidationReport(
        construct_name="LambdaFunction",
        overall_status=all(r.is_valid for r in results if r.severity == "ERROR"),
        results=results,
        summary={"ERROR": 1, "WARNING": 1, "INFO": 0}
    )
```

## Common Validation Failures and Resolutions

### Security Validation Failures

#### Unencrypted Resources

**Error**: `Encryption not enabled for S3 bucket`
**Resolution**:
```python
# Before (invalid)
bucket = s3.Bucket(self, "Bucket")

# After (valid)
bucket = s3.Bucket(
    self, "Bucket",
    encryption=s3.BucketEncryption.KMS,
    encryption_key=self.encryption_key
)
```

#### Overly Permissive IAM Policies

**Error**: `IAM policy grants excessive permissions`
**Resolution**:
```python
# Before (invalid)
policy = iam.PolicyStatement(
    actions=["*"],
    resources=["*"]
)

# After (valid)
policy = iam.PolicyStatement(
    actions=["s3:GetObject", "s3:PutObject"],
    resources=["arn:aws:s3:::my-bucket/*"]
)
```

### Compliance Validation Failures

#### Missing Required Tags

**Error**: `Required tag 'Environment' not found`
**Resolution**:
```python
# Apply required tags
resource.apply_tags({
    "Environment": "prod",
    "Project": "devsecops-platform",
    "Owner": "platform-team",
    "CostCenter": "CC-1234"
})
```

#### Data Retention Policy Missing

**Error**: `Data retention policy not configured for GDPR compliance`
**Resolution**:
```python
# Configure lifecycle policy
bucket.add_lifecycle_rule(
    id="DataRetentionPolicy",
    enabled=True,
    expiration=Duration.days(365)  # 1 year retention
)
```

### Cost Optimization Failures

#### Oversized Resources

**Warning**: `Instance type may be oversized for workload`
**Resolution**:
```python
# Review and right-size instance
instance_type = "t3.medium"  # Instead of "m5.xlarge"
```

#### Missing Lifecycle Policies

**Warning**: `S3 bucket missing lifecycle policies`
**Resolution**:
```python
bucket.add_lifecycle_rule(
    id="CostOptimization",
    enabled=True,
    transitions=[
        s3.Transition(
            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
            transition_after=Duration.days(30)
        ),
        s3.Transition(
            storage_class=s3.StorageClass.GLACIER,
            transition_after=Duration.days(90)
        )
    ]
)
```

## Integration with CDK Constructs

### Automatic Validation

```python
class BaseConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, props: ConstructProps):
        super().__init__(scope, construct_id)
        
        # Automatic validation
        validation_report = self._validate_props(props)
        
        if not validation_report.overall_status:
            errors = validation_report.get_errors()
            raise ValueError(f"Validation failed: {[e.message for e in errors]}")
        
        # Log warnings
        warnings = validation_report.get_warnings()
        for warning in warnings:
            print(f"WARNING: {warning.message}")
```

### Custom Validators

```python
def custom_database_validator(props: RdsConstructProps) -> List[ValidationResult]:
    """Custom validator for database configurations."""
    results = []
    
    if props.environment == "prod" and not props.multi_az:
        results.append(ValidationResult(
            is_valid=False,
            severity="ERROR",
            message="Production databases must be multi-AZ",
            property_name="multi_az",
            suggested_fix="Set multi_az=True for production environment"
        ))
    
    return results
```

## Validation Tools and CLI

### Command Line Interface

```bash
# Validate all constructs
cdk-validate --all

# Validate specific construct
cdk-validate --construct S3Construct

# Validate with specific framework
cdk-validate --compliance gdpr

# Generate validation report
cdk-validate --report validation-report.json

# Fix auto-fixable issues
cdk-validate --auto-fix
```

### CI/CD Integration

```yaml
# GitHub Actions validation
- name: Validate CDK Constructs
  run: |
    npm run validate:constructs
    npm run validate:security
    npm run validate:compliance
```

## Best Practices

1. **Early Validation**: Validate during development, not deployment
2. **Comprehensive Coverage**: Validate all aspects (security, compliance, cost)
3. **Clear Messages**: Provide actionable error messages and fixes
4. **Automated Remediation**: Auto-fix common issues where possible
5. **Continuous Monitoring**: Regular validation of deployed resources
6. **Documentation**: Keep validation rules documented and updated
7. **Training**: Ensure team understands validation requirements
