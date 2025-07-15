"""
DevSecOps Platform - Enterprise CDK Constructs Library

A comprehensive library of reusable AWS CDK constructs designed to accelerate
development by 70% and standardize common patterns across engineering teams.

This library provides:
- AI-powered development assistance with MCP integration
- Comprehensive quality assurance with CDK-Nag and Checkov
- Multi-environment deployment support
- Enterprise-grade security and compliance
- Disaster recovery and business continuity
- Complete observability and monitoring

Author: DevSecOps Platform Team
Version: 1.0.0
License: MIT
"""

from .common import *
from .data_ingestion import *
from .ml_ai import *
from .data_processing import *
from .analytics import *
from .security_compliance import *
from .monitoring import *
from .disaster_recovery import *

__version__ = "1.0.0"
__author__ = "DevSecOps Platform Team"
__email__ = "platform-team@company.com"
