"""
Compliance Automation
Provides automated compliance checking and reporting for various frameworks
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="compliance-checker",
    help="Compliance automation tool for DevSecOps platform",
    add_completion=False,
)
console = Console()


@dataclass
class ComplianceRule:
    """Represents a compliance rule."""
    id: str
    name: str
    description: str
    framework: str
    category: str
    severity: str
    check_type: str
    parameters: Dict[str, Any]
    remediation: str


@dataclass
class ComplianceResult:
    """Represents a compliance check result."""
    rule_id: str
    status: str  # PASS, FAIL, WARNING, NOT_APPLICABLE
    message: str
    evidence: Optional[Dict[str, Any]] = None
    remediation_steps: Optional[List[str]] = None


class ComplianceChecker:
    """Main compliance checker class."""
    
    def __init__(self, rules_path: Optional[Path] = None):
        self.rules_path = rules_path or self._get_default_rules_path()
        self.rules = self._load_rules()
        self.results: List[ComplianceResult] = []
    
    def _get_default_rules_path(self) -> Path:
        """Get default rules directory."""
        return Path(__file__).parent / "rules"
    
    def _load_rules(self) -> List[ComplianceRule]:
        """Load compliance rules from YAML files."""
        rules = []
        
        if not self.rules_path.exists():
            console.print(f"⚠️  Rules directory not found: {self.rules_path}")
            return rules
        
        for rule_file in self.rules_path.glob("*.yaml"):
            try:
                with open(rule_file, 'r') as f:
                    rule_data = yaml.safe_load(f)
                
                for rule_dict in rule_data.get("rules", []):
                    rule = ComplianceRule(**rule_dict)
                    rules.append(rule)
            
            except Exception as e:
                console.print(f"⚠️  Error loading rules from {rule_file}: {e}")
        
        return rules
    
    def check_compliance(self, path: Path, frameworks: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run compliance checks."""
        self.results = []
        
        # Filter rules by framework if specified
        rules_to_check = self.rules
        if frameworks:
            rules_to_check = [r for r in self.rules if r.framework in frameworks]
        
        console.print(f"Running {len(rules_to_check)} compliance checks...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            for rule in rules_to_check:
                task = progress.add_task(f"Checking {rule.name}...", total=None)
                
                try:
                    result = self._check_rule(rule, path)
                    self.results.append(result)
                    
                    status_icon = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⚠️"
                    progress.update(task, description=f"{status_icon} {rule.name}")
                
                except Exception as e:
                    result = ComplianceResult(
                        rule_id=rule.id,
                        status="ERROR",
                        message=f"Error checking rule: {e}"
                    )
                    self.results.append(result)
                    progress.update(task, description=f"❌ {rule.name} (Error)")
        
        return self._generate_report()
    
    def _check_rule(self, rule: ComplianceRule, path: Path) -> ComplianceResult:
        """Check a specific compliance rule."""
        if rule.check_type == "file_exists":
            return self._check_file_exists(rule, path)
        elif rule.check_type == "file_content":
            return self._check_file_content(rule, path)
        elif rule.check_type == "directory_structure":
            return self._check_directory_structure(rule, path)
        elif rule.check_type == "configuration":
            return self._check_configuration(rule, path)
        elif rule.check_type == "security_policy":
            return self._check_security_policy(rule, path)
        elif rule.check_type == "data_governance":
            return self._check_data_governance(rule, path)
        else:
            return ComplianceResult(
                rule_id=rule.id,
                status="NOT_APPLICABLE",
                message=f"Unknown check type: {rule.check_type}"
            )
    
    def _check_file_exists(self, rule: ComplianceRule, path: Path) -> ComplianceResult:
        """Check if required files exist."""
        required_files = rule.parameters.get("files", [])
        missing_files = []
        
        for file_path in required_files:
            if not (path / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            return ComplianceResult(
                rule_id=rule.id,
                status="FAIL",
                message=f"Missing required files: {', '.join(missing_files)}",
                evidence={"missing_files": missing_files},
                remediation_steps=[f"Create file: {f}" for f in missing_files]
            )
        else:
            return ComplianceResult(
                rule_id=rule.id,
                status="PASS",
                message="All required files exist"
            )
    
    def _check_file_content(self, rule: ComplianceRule, path: Path) -> ComplianceResult:
        """Check file content for required patterns."""
        file_path = path / rule.parameters.get("file")
        required_patterns = rule.parameters.get("patterns", [])
        
        if not file_path.exists():
            return ComplianceResult(
                rule_id=rule.id,
                status="FAIL",
                message=f"File not found: {file_path}",
                remediation_steps=[f"Create file: {file_path}"]
            )
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            missing_patterns = []
            for pattern in required_patterns:
                if pattern not in content:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                return ComplianceResult(
                    rule_id=rule.id,
                    status="FAIL",
                    message=f"Missing required patterns in {file_path}: {', '.join(missing_patterns)}",
                    evidence={"missing_patterns": missing_patterns},
                    remediation_steps=[f"Add pattern to {file_path}: {p}" for p in missing_patterns]
                )
            else:
                return ComplianceResult(
                    rule_id=rule.id,
                    status="PASS",
                    message=f"All required patterns found in {file_path}"
                )
        
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.id,
                status="ERROR",
                message=f"Error reading file {file_path}: {e}"
            )
    
    def _check_directory_structure(self, rule: ComplianceRule, path: Path) -> ComplianceResult:
        """Check directory structure compliance."""
        required_dirs = rule.parameters.get("directories", [])
        missing_dirs = []
        
        for dir_path in required_dirs:
            if not (path / dir_path).is_dir():
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            return ComplianceResult(
                rule_id=rule.id,
                status="FAIL",
                message=f"Missing required directories: {', '.join(missing_dirs)}",
                evidence={"missing_directories": missing_dirs},
                remediation_steps=[f"Create directory: {d}" for d in missing_dirs]
            )
        else:
            return ComplianceResult(
                rule_id=rule.id,
                status="PASS",
                message="All required directories exist"
            )
    
    def _check_configuration(self, rule: ComplianceRule, path: Path) -> ComplianceResult:
        """Check configuration file compliance."""
        config_file = path / rule.parameters.get("file")
        required_settings = rule.parameters.get("settings", {})
        
        if not config_file.exists():
            return ComplianceResult(
                rule_id=rule.id,
                status="FAIL",
                message=f"Configuration file not found: {config_file}",
                remediation_steps=[f"Create configuration file: {config_file}"]
            )
        
        try:
            if config_file.suffix in ['.yaml', '.yml']:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
            elif config_file.suffix == '.json':
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                return ComplianceResult(
                    rule_id=rule.id,
                    status="NOT_APPLICABLE",
                    message=f"Unsupported configuration file format: {config_file.suffix}"
                )
            
            missing_settings = []
            for key, expected_value in required_settings.items():
                if self._get_nested_value(config, key) != expected_value:
                    missing_settings.append(f"{key}={expected_value}")
            
            if missing_settings:
                return ComplianceResult(
                    rule_id=rule.id,
                    status="FAIL",
                    message=f"Missing or incorrect settings in {config_file}: {', '.join(missing_settings)}",
                    evidence={"missing_settings": missing_settings},
                    remediation_steps=[f"Set {s} in {config_file}" for s in missing_settings]
                )
            else:
                return ComplianceResult(
                    rule_id=rule.id,
                    status="PASS",
                    message=f"Configuration in {config_file} is compliant"
                )
        
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.id,
                status="ERROR",
                message=f"Error reading configuration {config_file}: {e}"
            )
    
    def _check_security_policy(self, rule: ComplianceRule, path: Path) -> ComplianceResult:
        """Check security policy compliance."""
        # Check for security documentation
        security_files = [
            "SECURITY.md",
            ".github/SECURITY.md",
            "docs/security.md",
            "security/README.md"
        ]
        
        security_file_found = False
        for file_name in security_files:
            if (path / file_name).exists():
                security_file_found = True
                break
        
        issues = []
        
        if not security_file_found:
            issues.append("No security policy documentation found")
        
        # Check for .gitignore with security patterns
        gitignore_path = path / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
            
            required_patterns = ["*.key", "*.pem", "secrets", ".env", "*.p12", "*.pfx"]
            missing_patterns = [p for p in required_patterns if p not in gitignore_content]
            
            if missing_patterns:
                issues.append(f"Missing security patterns in .gitignore: {', '.join(missing_patterns)}")
        else:
            issues.append("No .gitignore file found")
        
        # Check for pre-commit hooks
        precommit_path = path / ".pre-commit-config.yaml"
        if not precommit_path.exists():
            issues.append("No pre-commit configuration found")
        
        if issues:
            return ComplianceResult(
                rule_id=rule.id,
                status="FAIL",
                message=f"Security policy issues: {'; '.join(issues)}",
                evidence={"issues": issues},
                remediation_steps=issues
            )
        else:
            return ComplianceResult(
                rule_id=rule.id,
                status="PASS",
                message="Security policy compliance verified"
            )
    
    def _check_data_governance(self, rule: ComplianceRule, path: Path) -> ComplianceResult:
        """Check data governance compliance."""
        issues = []
        
        # Check for data files
        data_extensions = [".csv", ".json", ".parquet", ".avro", ".orc"]
        data_files = []
        
        for ext in data_extensions:
            data_files.extend(list(path.glob(f"**/*{ext}")))
        
        if data_files:
            # Check for data classification
            classification_files = [
                "DATA_CLASSIFICATION.md",
                "data-classification.md",
                "docs/data-classification.md",
                "docs/data-governance.md"
            ]
            
            classification_found = False
            for file_name in classification_files:
                if (path / file_name).exists():
                    classification_found = True
                    break
            
            if not classification_found:
                issues.append("Data files found but no data classification documentation")
            
            # Check for data retention policy
            retention_files = [
                "DATA_RETENTION.md",
                "data-retention.md",
                "docs/data-retention.md"
            ]
            
            retention_found = False
            for file_name in retention_files:
                if (path / file_name).exists():
                    retention_found = True
                    break
            
            if not retention_found:
                issues.append("No data retention policy documentation found")
        
        if issues:
            return ComplianceResult(
                rule_id=rule.id,
                status="FAIL",
                message=f"Data governance issues: {'; '.join(issues)}",
                evidence={"issues": issues, "data_files_count": len(data_files)},
                remediation_steps=issues
            )
        else:
            return ComplianceResult(
                rule_id=rule.id,
                status="PASS",
                message="Data governance compliance verified"
            )
    
    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = key.split('.')
        value = data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate compliance report."""
        total_checks = len(self.results)
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        warnings = len([r for r in self.results if r.status == "WARNING"])
        errors = len([r for r in self.results if r.status == "ERROR"])
        
        compliance_score = (passed / total_checks * 100) if total_checks > 0 else 0
        
        # Group results by framework
        by_framework = {}
        for result in self.results:
            rule = next((r for r in self.rules if r.id == result.rule_id), None)
            if rule:
                framework = rule.framework
                if framework not in by_framework:
                    by_framework[framework] = []
                by_framework[framework].append(result)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": total_checks,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "errors": errors,
                "compliance_score": round(compliance_score, 2),
            },
            "by_framework": by_framework,
            "results": [asdict(r) for r in self.results],
        }


@app.command()
def check(
    path: str = typer.Argument(".", help="Path to check"),
    frameworks: Optional[List[str]] = typer.Option(None, "--framework", "-f", help="Frameworks to check"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", help="Output format (json, text, html)"),
):
    """Run compliance checks."""
    console.print(Panel.fit("📋 Compliance Checker", style="bold blue"))
    
    checker = ComplianceChecker()
    report = checker.check_compliance(Path(path), frameworks)
    
    # Print summary
    summary = report["summary"]
    console.print(f"\n📊 Compliance Score: [bold]{summary['compliance_score']}%[/bold]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", style="cyan")
    table.add_column("Count", style="white")
    
    table.add_row("✅ Passed", str(summary["passed"]))
    table.add_row("❌ Failed", str(summary["failed"]))
    table.add_row("⚠️  Warnings", str(summary["warnings"]))
    table.add_row("🔥 Errors", str(summary["errors"]))
    
    console.print(table)
    
    # Save report if requested
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            if format == "json":
                json.dump(report, f, indent=2)
            elif format == "text":
                f.write(format_text_report(report))
            elif format == "html":
                f.write(format_html_report(report))
        
        console.print(f"\n📄 Report saved to: [bold]{output_path}[/bold]")


def format_text_report(report: Dict[str, Any]) -> str:
    """Format compliance report as text."""
    lines = []
    lines.append("Compliance Report")
    lines.append("=" * 50)
    lines.append(f"Timestamp: {report['timestamp']}")
    lines.append("")
    
    summary = report["summary"]
    lines.append("Summary:")
    lines.append(f"  Total Checks: {summary['total_checks']}")
    lines.append(f"  Passed: {summary['passed']}")
    lines.append(f"  Failed: {summary['failed']}")
    lines.append(f"  Warnings: {summary['warnings']}")
    lines.append(f"  Errors: {summary['errors']}")
    lines.append(f"  Compliance Score: {summary['compliance_score']}%")
    lines.append("")
    
    # Results by framework
    for framework, results in report["by_framework"].items():
        lines.append(f"{framework} Framework:")
        lines.append("-" * 30)
        
        for result in results:
            status_icon = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️", "ERROR": "🔥"}.get(result["status"], "❓")
            lines.append(f"  {status_icon} {result['rule_id']}: {result['message']}")
        
        lines.append("")
    
    return "\n".join(lines)


def format_html_report(report: Dict[str, Any]) -> str:
    """Format compliance report as HTML."""
    summary = report["summary"]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Compliance Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
            .summary {{ background-color: #e8f4fd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .pass {{ color: #4caf50; }}
            .fail {{ color: #f44336; }}
            .warning {{ color: #ff9800; }}
            .error {{ color: #9c27b0; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Compliance Report</h1>
            <p><strong>Timestamp:</strong> {report['timestamp']}</p>
            <p><strong>Compliance Score:</strong> {summary['compliance_score']}%</p>
        </div>
        
        <div class="summary">
            <h2>Summary</h2>
            <table>
                <tr><th>Status</th><th>Count</th></tr>
                <tr><td class="pass">Passed</td><td>{summary['passed']}</td></tr>
                <tr><td class="fail">Failed</td><td>{summary['failed']}</td></tr>
                <tr><td class="warning">Warnings</td><td>{summary['warnings']}</td></tr>
                <tr><td class="error">Errors</td><td>{summary['errors']}</td></tr>
            </table>
        </div>
    """
    
    # Add framework results
    for framework, results in report["by_framework"].items():
        html += f"""
        <h2>{framework} Framework</h2>
        <table>
            <tr><th>Rule ID</th><th>Status</th><th>Message</th></tr>
        """
        
        for result in results:
            status_class = result["status"].lower()
            html += f"""
            <tr>
                <td>{result['rule_id']}</td>
                <td class="{status_class}">{result['status']}</td>
                <td>{result['message']}</td>
            </tr>
            """
        
        html += "</table>"
    
    html += """
    </body>
    </html>
    """
    
    return html


if __name__ == "__main__":
    app()
