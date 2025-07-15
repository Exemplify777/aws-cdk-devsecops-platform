#!/usr/bin/env python3
"""
Platform Analysis and Testing Script
Comprehensive analysis of the DevSecOps platform implementation
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import importlib.util


class PlatformAnalyzer:
    """Analyzes the DevSecOps platform implementation."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues = []
        self.warnings = []
        self.successes = []
    
    def analyze(self) -> Dict[str, Any]:
        """Run comprehensive analysis."""
        print("🔍 Starting DevSecOps Platform Analysis...")
        
        # Check project structure
        self._check_project_structure()
        
        # Check required files
        self._check_required_files()
        
        # Check Python imports
        self._check_python_imports()
        
        # Check configuration files
        self._check_configuration_files()
        
        # Check GitHub Actions workflows
        self._check_github_workflows()
        
        # Check documentation
        self._check_documentation()
        
        # Check security components
        self._check_security_components()
        
        # Generate report
        return self._generate_report()
    
    def _check_project_structure(self):
        """Check project directory structure."""
        print("📁 Checking project structure...")
        
        required_dirs = [
            "infrastructure/stacks",
            "infrastructure/constructs", 
            "infrastructure/config",
            "platform/cli",
            "platform/portal",
            "security",
            "templates",
            "tests/unit",
            "tests/integration",
            "tests/infrastructure",
            "docs",
            ".github/workflows"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                self.successes.append(f"✅ Directory exists: {dir_path}")
            else:
                self.issues.append(f"❌ Missing directory: {dir_path}")
    
    def _check_required_files(self):
        """Check for required files."""
        print("📄 Checking required files...")
        
        required_files = [
            "README.md",
            "app.py",
            "cdk.json",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "pyproject.toml",
            "pytest.ini",
            ".pre-commit-config.yaml",
            "mkdocs.yml",
            ".github/workflows/ci.yml",
            ".github/workflows/cd.yml",
            ".github/workflows/security.yml",
            "infrastructure/stacks/core_infrastructure_stack.py",
            "infrastructure/stacks/security_stack.py",
            "infrastructure/stacks/data_pipeline_stack.py",
            "infrastructure/stacks/monitoring_stack.py",
            "infrastructure/stacks/portal_stack.py",
            "infrastructure/stacks/ai_tools_stack.py",
            "infrastructure/config/settings.py",
            "platform/cli/main.py",
            "platform/cli/config.py",
            "platform/cli/templates.py",
            "platform/cli/aws.py",
            "platform/cli/github.py",
            "security/scanner.py",
            "security/compliance.py",
            "security/rules/soc2.yaml",
            "security/rules/iso27001.yaml",
            "security/rules/gdpr.yaml",
            "templates/data-pipeline/cookiecutter.json",
            "tests/unit/test_core_infrastructure.py",
            "tests/smoke/test_basic_health.py"
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.successes.append(f"✅ File exists: {file_path}")
            else:
                self.issues.append(f"❌ Missing file: {file_path}")
    
    def _check_python_imports(self):
        """Check Python import issues."""
        print("🐍 Checking Python imports...")
        
        # Add project root to Python path
        sys.path.insert(0, str(self.project_root))
        
        modules_to_check = [
            "infrastructure.config.settings",
            "platform.cli.main",
            "platform.cli.config",
            "security.scanner",
            "security.compliance"
        ]
        
        for module_name in modules_to_check:
            try:
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    self.issues.append(f"❌ Module not found: {module_name}")
                else:
                    self.successes.append(f"✅ Module found: {module_name}")
            except Exception as e:
                self.issues.append(f"❌ Import error in {module_name}: {e}")
    
    def _check_configuration_files(self):
        """Check configuration files."""
        print("⚙️ Checking configuration files...")
        
        # Check cdk.json
        cdk_json_path = self.project_root / "cdk.json"
        if cdk_json_path.exists():
            try:
                with open(cdk_json_path) as f:
                    cdk_config = json.load(f)
                
                required_keys = ["app", "context"]
                for key in required_keys:
                    if key in cdk_config:
                        self.successes.append(f"✅ CDK config has {key}")
                    else:
                        self.issues.append(f"❌ CDK config missing {key}")
            except json.JSONDecodeError as e:
                self.issues.append(f"❌ Invalid JSON in cdk.json: {e}")
        
        # Check pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            self.successes.append("✅ pyproject.toml exists")
        else:
            self.warnings.append("⚠️ pyproject.toml missing (recommended)")
    
    def _check_github_workflows(self):
        """Check GitHub Actions workflows."""
        print("🔄 Checking GitHub Actions workflows...")
        
        workflows_dir = self.project_root / ".github/workflows"
        if workflows_dir.exists():
            workflow_files = list(workflows_dir.glob("*.yml"))
            
            expected_workflows = ["ci.yml", "cd.yml", "security.yml"]
            for workflow in expected_workflows:
                workflow_path = workflows_dir / workflow
                if workflow_path.exists():
                    self.successes.append(f"✅ Workflow exists: {workflow}")
                    
                    # Basic validation
                    try:
                        # Just check if the file exists and is not empty
                        if os.path.getsize(workflow_path) > 0:
                            self.successes.append(f"✅ Workflow {workflow} has content")
                        else:
                            self.issues.append(f"❌ Workflow {workflow} is empty")
                    except Exception as e:
                        self.issues.append(f"❌ Error checking workflow {workflow}: {e}")
                else:
                    self.issues.append(f"❌ Missing workflow: {workflow}")
    
    def _check_documentation(self):
        """Check documentation."""
        print("📚 Checking documentation...")
        
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            doc_files = list(docs_dir.rglob("*.md"))
            if doc_files:
                self.successes.append(f"✅ Found {len(doc_files)} documentation files")
            else:
                self.warnings.append("⚠️ No markdown files found in docs/")
        
        # Check mkdocs.yml
        mkdocs_path = self.project_root / "mkdocs.yml"
        if mkdocs_path.exists():
            self.successes.append("✅ MkDocs configuration exists")
        else:
            self.warnings.append("⚠️ MkDocs configuration missing")
    
    def _check_security_components(self):
        """Check security components."""
        print("🛡️ Checking security components...")
        
        security_dir = self.project_root / "security"
        if security_dir.exists():
            # Check security scripts
            security_files = ["scanner.py", "compliance.py"]
            for file_name in security_files:
                file_path = security_dir / file_name
                if file_path.exists():
                    self.successes.append(f"✅ Security component: {file_name}")
                else:
                    self.issues.append(f"❌ Missing security component: {file_name}")
            
            # Check compliance rules
            rules_dir = security_dir / "rules"
            if rules_dir.exists():
                rule_files = list(rules_dir.glob("*.yaml"))
                if rule_files:
                    self.successes.append(f"✅ Found {len(rule_files)} compliance rule files")
                else:
                    self.warnings.append("⚠️ No compliance rule files found")
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate analysis report."""
        total_checks = len(self.successes) + len(self.issues) + len(self.warnings)
        success_rate = len(self.successes) / total_checks * 100 if total_checks > 0 else 0
        
        return {
            "summary": {
                "total_checks": total_checks,
                "successes": len(self.successes),
                "issues": len(self.issues),
                "warnings": len(self.warnings),
                "success_rate": round(success_rate, 2)
            },
            "successes": self.successes,
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if self.issues:
            recommendations.append("🔧 Fix critical issues before deployment")
        
        if len(self.warnings) > 5:
            recommendations.append("⚠️ Address warnings to improve platform quality")
        
        if not any("test" in item for item in self.successes):
            recommendations.append("🧪 Add comprehensive test coverage")
        
        recommendations.extend([
            "📦 Install dependencies: pip install -r requirements.txt",
            "🔍 Run security scans: python security/scanner.py scan .",
            "✅ Run compliance checks: python security/compliance.py check",
            "🧪 Run tests: pytest",
            "📚 Build documentation: mkdocs build",
            "🚀 Deploy to dev: cdk deploy --context environment=dev"
        ])
        
        return recommendations


def main():
    """Main function."""
    project_root = Path(__file__).parent.parent
    analyzer = PlatformAnalyzer(project_root)
    
    report = analyzer.analyze()
    
    print("\n" + "="*60)
    print("📊 ANALYSIS REPORT")
    print("="*60)
    
    summary = report["summary"]
    print(f"Total Checks: {summary['total_checks']}")
    print(f"✅ Successes: {summary['successes']}")
    print(f"❌ Issues: {summary['issues']}")
    print(f"⚠️ Warnings: {summary['warnings']}")
    print(f"Success Rate: {summary['success_rate']}%")
    
    if report["issues"]:
        print(f"\n❌ CRITICAL ISSUES ({len(report['issues'])})")
        for issue in report["issues"]:
            print(f"  {issue}")
    
    if report["warnings"]:
        print(f"\n⚠️ WARNINGS ({len(report['warnings'])})")
        for warning in report["warnings"]:
            print(f"  {warning}")
    
    print(f"\n🔧 RECOMMENDATIONS")
    for rec in report["recommendations"]:
        print(f"  {rec}")
    
    # Save detailed report
    report_path = project_root / "analysis_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    # Exit with appropriate code
    if report["issues"]:
        print("\n❌ Analysis completed with critical issues")
        sys.exit(1)
    else:
        print("\n✅ Analysis completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
