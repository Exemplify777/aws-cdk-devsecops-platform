"""
Type definitions and data classes for DevSecOps Platform constructs.

This module provides comprehensive type definitions, data classes, and enums
used throughout the construct library for type safety and validation.
"""

from typing import Dict, Any, Optional, List, Union, Literal
from dataclasses import dataclass, field
from enum import Enum
import json

from aws_cdk import Duration


class Environment(str, Enum):
    """Supported deployment environments."""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class SecurityLevel(str, Enum):
    """Security levels for different environments and use cases."""
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"


class DataClassification(str, Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class MonitoringLevel(str, Enum):
    """Monitoring levels for different environments."""
    BASIC = "basic"
    STANDARD = "standard"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


@dataclass
class SecurityConfig:
    """Security configuration for constructs."""
    level: SecurityLevel = SecurityLevel.STANDARD
    encryption_enabled: bool = True
    encryption_key_rotation: bool = True
    vpc_enabled: bool = True
    security_groups_enabled: bool = True
    iam_least_privilege: bool = True
    audit_logging: bool = True
    compliance_frameworks: List[ComplianceFramework] = field(default_factory=list)
    data_classification: DataClassification = DataClassification.INTERNAL
    secrets_encryption: bool = True
    network_isolation: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "level": self.level.value,
            "encryption_enabled": self.encryption_enabled,
            "encryption_key_rotation": self.encryption_key_rotation,
            "vpc_enabled": self.vpc_enabled,
            "security_groups_enabled": self.security_groups_enabled,
            "iam_least_privilege": self.iam_least_privilege,
            "audit_logging": self.audit_logging,
            "compliance_frameworks": [f.value for f in self.compliance_frameworks],
            "data_classification": self.data_classification.value,
            "secrets_encryption": self.secrets_encryption,
            "network_isolation": self.network_isolation
        }


@dataclass
class MonitoringConfig:
    """Monitoring configuration for constructs."""
    level: MonitoringLevel = MonitoringLevel.STANDARD
    metrics_enabled: bool = True
    logging_enabled: bool = True
    tracing_enabled: bool = True
    alerting_enabled: bool = True
    dashboards_enabled: bool = True
    log_retention_days: int = 30
    metric_retention_days: int = 90
    custom_metrics: List[str] = field(default_factory=list)
    alert_channels: List[str] = field(default_factory=list)
    health_checks_enabled: bool = True
    cost_monitoring_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "level": self.level.value,
            "metrics_enabled": self.metrics_enabled,
            "logging_enabled": self.logging_enabled,
            "tracing_enabled": self.tracing_enabled,
            "alerting_enabled": self.alerting_enabled,
            "dashboards_enabled": self.dashboards_enabled,
            "log_retention_days": self.log_retention_days,
            "metric_retention_days": self.metric_retention_days,
            "custom_metrics": self.custom_metrics,
            "alert_channels": self.alert_channels,
            "health_checks_enabled": self.health_checks_enabled,
            "cost_monitoring_enabled": self.cost_monitoring_enabled
        }


@dataclass
class BackupConfig:
    """Backup configuration for constructs."""
    enabled: bool = True
    retention_days: int = 30
    cross_region_backup: bool = False
    backup_schedule: str = "cron(0 2 * * ? *)"  # Daily at 2 AM
    point_in_time_recovery: bool = True
    backup_encryption: bool = True
    backup_tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "enabled": self.enabled,
            "retention_days": self.retention_days,
            "cross_region_backup": self.cross_region_backup,
            "backup_schedule": self.backup_schedule,
            "point_in_time_recovery": self.point_in_time_recovery,
            "backup_encryption": self.backup_encryption,
            "backup_tags": self.backup_tags
        }


@dataclass
class DisasterRecoveryConfig:
    """Disaster recovery configuration for constructs."""
    enabled: bool = False
    rto_minutes: int = 240  # Recovery Time Objective: 4 hours
    rpo_minutes: int = 60   # Recovery Point Objective: 1 hour
    multi_region: bool = False
    failover_region: Optional[str] = None
    automated_failover: bool = False
    dr_testing_enabled: bool = True
    dr_testing_schedule: str = "cron(0 6 ? * SUN *)"  # Weekly on Sunday at 6 AM
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "enabled": self.enabled,
            "rto_minutes": self.rto_minutes,
            "rpo_minutes": self.rpo_minutes,
            "multi_region": self.multi_region,
            "failover_region": self.failover_region,
            "automated_failover": self.automated_failover,
            "dr_testing_enabled": self.dr_testing_enabled,
            "dr_testing_schedule": self.dr_testing_schedule
        }


@dataclass
class CostConfig:
    """Cost configuration and optimization settings."""
    budget_enabled: bool = True
    monthly_budget_usd: Optional[float] = None
    cost_alerts_enabled: bool = True
    cost_optimization_enabled: bool = True
    reserved_instances_enabled: bool = False
    spot_instances_enabled: bool = False
    lifecycle_policies_enabled: bool = True
    cost_allocation_tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "budget_enabled": self.budget_enabled,
            "monthly_budget_usd": self.monthly_budget_usd,
            "cost_alerts_enabled": self.cost_alerts_enabled,
            "cost_optimization_enabled": self.cost_optimization_enabled,
            "reserved_instances_enabled": self.reserved_instances_enabled,
            "spot_instances_enabled": self.spot_instances_enabled,
            "lifecycle_policies_enabled": self.lifecycle_policies_enabled,
            "cost_allocation_tags": self.cost_allocation_tags
        }


@dataclass
class ConstructProps:
    """Base properties for all DevSecOps Platform constructs."""
    project_name: str
    environment: Environment
    security_config: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring_config: MonitoringConfig = field(default_factory=MonitoringConfig)
    backup_config: BackupConfig = field(default_factory=BackupConfig)
    disaster_recovery_config: DisasterRecoveryConfig = field(default_factory=DisasterRecoveryConfig)
    cost_config: CostConfig = field(default_factory=CostConfig)
    tags: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Ensure environment is an Environment enum
        if isinstance(self.environment, str):
            self.environment = Environment(self.environment)
        
        # Set environment-specific defaults
        self._set_environment_defaults()
    
    def _set_environment_defaults(self):
        """Set environment-specific default configurations."""
        if self.environment == Environment.PROD:
            # Production defaults
            self.security_config.level = SecurityLevel.HIGH
            self.monitoring_config.level = MonitoringLevel.COMPREHENSIVE
            self.backup_config.retention_days = 90
            self.backup_config.cross_region_backup = True
            self.disaster_recovery_config.enabled = True
            self.cost_config.reserved_instances_enabled = True
            
        elif self.environment == Environment.STAGING:
            # Staging defaults
            self.security_config.level = SecurityLevel.STANDARD
            self.monitoring_config.level = MonitoringLevel.DETAILED
            self.backup_config.retention_days = 30
            self.disaster_recovery_config.enabled = False
            
        else:  # Development
            # Development defaults
            self.security_config.level = SecurityLevel.BASIC
            self.monitoring_config.level = MonitoringLevel.BASIC
            self.backup_config.retention_days = 7
            self.backup_config.enabled = False
            self.disaster_recovery_config.enabled = False
            self.cost_config.spot_instances_enabled = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "project_name": self.project_name,
            "environment": self.environment.value,
            "security_config": self.security_config.to_dict(),
            "monitoring_config": self.monitoring_config.to_dict(),
            "backup_config": self.backup_config.to_dict(),
            "disaster_recovery_config": self.disaster_recovery_config.to_dict(),
            "cost_config": self.cost_config.to_dict(),
            "tags": self.tags,
            "description": self.description
        }
    
    def to_json(self) -> str:
        """Convert to JSON string representation."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConstructProps':
        """Create instance from dictionary."""
        # Extract nested configs
        security_config = SecurityConfig(**data.get('security_config', {}))
        monitoring_config = MonitoringConfig(**data.get('monitoring_config', {}))
        backup_config = BackupConfig(**data.get('backup_config', {}))
        disaster_recovery_config = DisasterRecoveryConfig(**data.get('disaster_recovery_config', {}))
        cost_config = CostConfig(**data.get('cost_config', {}))
        
        return cls(
            project_name=data['project_name'],
            environment=Environment(data['environment']),
            security_config=security_config,
            monitoring_config=monitoring_config,
            backup_config=backup_config,
            disaster_recovery_config=disaster_recovery_config,
            cost_config=cost_config,
            tags=data.get('tags', {}),
            description=data.get('description')
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ConstructProps':
        """Create instance from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


# Type aliases for common use cases
EnvironmentType = Literal["dev", "staging", "prod"]
SecurityLevelType = Literal["basic", "standard", "high", "critical"]
MonitoringLevelType = Literal["basic", "standard", "detailed", "comprehensive"]
DataClassificationType = Literal["public", "internal", "confidential", "restricted"]

# Common type unions
ConfigValue = Union[str, int, float, bool, List[str], Dict[str, Any]]
TagsType = Dict[str, str]
MetricsType = List[str]
