"""
Security Scanner
Provides comprehensive security scanning capabilities for code, infrastructure, and dependencies
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

app = typer.Typer(
    name="security-scanner",
    help="Security scanning tool for DevSecOps platform",
    add_completion=False,
)
console = Console()


@app.command()
def scan(
    path: str = typer.Argument(".", help="Path to scan"),
    scan_type: str = typer.Option("all", "--type", "-t", help="Scan type (code, infra, deps, secrets, all)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json, text, html)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run security scans on code, infrastructure, and dependencies."""
    console.print(Panel.fit("🔒 DevSecOps Security Scanner", style="bold blue"))
    
    if not os.path.exists(path):
        console.print(f"❌ Path not found: {path}")
        raise typer.Exit(1)
    
    scan_path = Path(path).absolute()
    console.print(f"Scanning: [bold]{scan_path}[/bold]")
    
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        if scan_type in ["code", "all"]:
            task = progress.add_task("Running code security scan...", total=None)
            results["code"] = scan_code(scan_path, verbose)
            progress.update(task, description="✅ Code security scan complete")
        
        if scan_type in ["infra", "all"]:
            task = progress.add_task("Running infrastructure security scan...", total=None)
            results["infrastructure"] = scan_infrastructure(scan_path, verbose)
            progress.update(task, description="✅ Infrastructure security scan complete")
        
        if scan_type in ["deps", "all"]:
            task = progress.add_task("Running dependency security scan...", total=None)
            results["dependencies"] = scan_dependencies(scan_path, verbose)
            progress.update(task, description="✅ Dependency security scan complete")
        
        if scan_type in ["secrets", "all"]:
            task = progress.add_task("Running secrets scan...", total=None)
            results["secrets"] = scan_secrets(scan_path, verbose)
            progress.update(task, description="✅ Secrets scan complete")
        
        if scan_type in ["compliance", "all"]:
            task = progress.add_task("Running compliance scan...", total=None)
            results["compliance"] = scan_compliance(scan_path, verbose)
            progress.update(task, description="✅ Compliance scan complete")
    
    # Add metadata
    results["metadata"] = {
        "timestamp": datetime.now().isoformat(),
        "path": str(scan_path),
        "scan_type": scan_type,
        "version": "1.0.0",
    }
    
    # Calculate summary
    results["summary"] = calculate_summary(results)
    
    # Output results
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            if format == "json":
                json.dump(results, f, indent=2)
            elif format == "text":
                f.write(format_text_report(results))
            elif format == "html":
                f.write(format_html_report(results))
        
        console.print(f"\n📄 Report saved to: [bold]{output_path}[/bold]")
    
    # Print summary
    print_summary(results["summary"])


def scan_code(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run code security scan using Bandit and Semgrep."""
    results = {
        "bandit": run_bandit(path, verbose),
        "semgrep": run_semgrep(path, verbose),
    }
    
    return results


def run_bandit(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run Bandit security scanner."""
    try:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        output_file.close()
        
        cmd = [
            "bandit",
            "-r", str(path),
            "-f", "json",
            "-o", output_file.name,
        ]
        
        if verbose:
            console.print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        with open(output_file.name, "r") as f:
            try:
                scan_results = json.load(f)
            except json.JSONDecodeError:
                scan_results = {"error": "Failed to parse Bandit output"}
        
        os.unlink(output_file.name)
        
        return {
            "success": result.returncode == 0,
            "results": scan_results,
            "issues_count": {
                "high": scan_results.get("metrics", {}).get("high", 0),
                "medium": scan_results.get("metrics", {}).get("medium", 0),
                "low": scan_results.get("metrics", {}).get("low", 0),
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "issues_count": {"high": 0, "medium": 0, "low": 0}
        }


def run_semgrep(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run Semgrep security scanner."""
    try:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        output_file.close()
        
        cmd = [
            "semgrep",
            "--config=auto",
            str(path),
            "--json",
            "--output", output_file.name,
        ]
        
        if verbose:
            console.print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        with open(output_file.name, "r") as f:
            try:
                scan_results = json.load(f)
            except json.JSONDecodeError:
                scan_results = {"error": "Failed to parse Semgrep output"}
        
        os.unlink(output_file.name)
        
        # Count issues by severity
        high = 0
        medium = 0
        low = 0
        
        for result in scan_results.get("results", []):
            severity = result.get("extra", {}).get("severity", "").lower()
            if severity == "high" or severity == "error":
                high += 1
            elif severity == "medium" or severity == "warning":
                medium += 1
            else:
                low += 1
        
        return {
            "success": result.returncode == 0,
            "results": scan_results,
            "issues_count": {
                "high": high,
                "medium": medium,
                "low": low,
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "issues_count": {"high": 0, "medium": 0, "low": 0}
        }


def scan_infrastructure(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run infrastructure security scan using Checkov and cfn-lint."""
    results = {
        "checkov": run_checkov(path, verbose),
        "cfn_lint": run_cfn_lint(path, verbose),
    }
    
    return results


def run_checkov(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run Checkov infrastructure scanner."""
    try:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        output_file.close()
        
        cmd = [
            "checkov",
            "-d", str(path),
            "--output", "json",
            "--output-file", output_file.name,
        ]
        
        if verbose:
            console.print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        with open(output_file.name, "r") as f:
            try:
                scan_results = json.load(f)
            except json.JSONDecodeError:
                scan_results = {"error": "Failed to parse Checkov output"}
        
        os.unlink(output_file.name)
        
        # Count issues by severity
        high = 0
        medium = 0
        low = 0
        
        for check_type, checks in scan_results.get("results", {}).get("failed_checks", {}).items():
            for check in checks:
                severity = check.get("severity", "").lower()
                if severity == "high" or severity == "critical":
                    high += 1
                elif severity == "medium":
                    medium += 1
                else:
                    low += 1
        
        return {
            "success": result.returncode == 0,
            "results": scan_results,
            "issues_count": {
                "high": high,
                "medium": medium,
                "low": low,
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "issues_count": {"high": 0, "medium": 0, "low": 0}
        }


def run_cfn_lint(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run cfn-lint for CloudFormation templates."""
    try:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        output_file.close()
        
        cmd = [
            "cfn-lint",
            str(path) + "/**/*.template.json",
            "--format", "json",
            "--output-file", output_file.name,
        ]
        
        if verbose:
            console.print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,  # Use shell for glob pattern
        )
        
        try:
            with open(output_file.name, "r") as f:
                try:
                    scan_results = json.load(f)
                except json.JSONDecodeError:
                    scan_results = []
        except FileNotFoundError:
            scan_results = []
        
        try:
            os.unlink(output_file.name)
        except:
            pass
        
        # Count issues by severity
        high = 0
        medium = 0
        low = 0
        
        for issue in scan_results:
            level = issue.get("Level", "").lower()
            if level == "error":
                high += 1
            elif level == "warning":
                medium += 1
            else:
                low += 1
        
        return {
            "success": result.returncode == 0,
            "results": scan_results,
            "issues_count": {
                "high": high,
                "medium": medium,
                "low": low,
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "issues_count": {"high": 0, "medium": 0, "low": 0}
        }


def scan_dependencies(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run dependency security scan using Safety and pip-audit."""
    results = {
        "safety": run_safety(path, verbose),
        "pip_audit": run_pip_audit(path, verbose),
    }

    return results


def run_safety(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run Safety dependency scanner."""
    try:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        output_file.close()

        cmd = [
            "safety",
            "check",
            "--json",
            "--output", output_file.name,
        ]

        if verbose:
            console.print(f"Running: {' '.join(cmd)}")

        # Change to the target directory
        original_cwd = os.getcwd()
        os.chdir(path)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        os.chdir(original_cwd)

        with open(output_file.name, "r") as f:
            try:
                scan_results = json.load(f)
            except json.JSONDecodeError:
                scan_results = {"error": "Failed to parse Safety output"}

        os.unlink(output_file.name)

        # Count vulnerabilities
        vuln_count = len(scan_results) if isinstance(scan_results, list) else 0

        return {
            "success": result.returncode == 0,
            "results": scan_results,
            "issues_count": {
                "high": vuln_count,  # Safety doesn't categorize by severity
                "medium": 0,
                "low": 0,
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "issues_count": {"high": 0, "medium": 0, "low": 0}
        }


def run_pip_audit(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run pip-audit dependency scanner."""
    try:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        output_file.close()

        cmd = [
            "pip-audit",
            "--format=json",
            "--output", output_file.name,
        ]

        if verbose:
            console.print(f"Running: {' '.join(cmd)}")

        # Change to the target directory
        original_cwd = os.getcwd()
        os.chdir(path)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        os.chdir(original_cwd)

        with open(output_file.name, "r") as f:
            try:
                scan_results = json.load(f)
            except json.JSONDecodeError:
                scan_results = {"error": "Failed to parse pip-audit output"}

        os.unlink(output_file.name)

        # Count vulnerabilities
        vuln_count = len(scan_results.get("vulnerabilities", [])) if isinstance(scan_results, dict) else 0

        return {
            "success": result.returncode == 0,
            "results": scan_results,
            "issues_count": {
                "high": vuln_count,  # pip-audit doesn't categorize by severity
                "medium": 0,
                "low": 0,
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "issues_count": {"high": 0, "medium": 0, "low": 0}
        }


def scan_secrets(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run secrets scan using detect-secrets."""
    try:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        output_file.close()

        cmd = [
            "detect-secrets",
            "scan",
            str(path),
            "--output", output_file.name,
        ]

        if verbose:
            console.print(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        with open(output_file.name, "r") as f:
            try:
                scan_results = json.load(f)
            except json.JSONDecodeError:
                scan_results = {"error": "Failed to parse detect-secrets output"}

        os.unlink(output_file.name)

        # Count secrets
        secrets_count = 0
        for file_path, secrets in scan_results.get("results", {}).items():
            secrets_count += len(secrets)

        return {
            "success": result.returncode == 0,
            "results": scan_results,
            "issues_count": {
                "high": secrets_count,  # All secrets are high severity
                "medium": 0,
                "low": 0,
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "issues_count": {"high": 0, "medium": 0, "low": 0}
        }


def scan_compliance(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run compliance checks."""
    results = {
        "license_check": check_licenses(path, verbose),
        "security_policies": check_security_policies(path, verbose),
        "data_governance": check_data_governance(path, verbose),
    }

    return results


def check_licenses(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Check license compliance."""
    try:
        cmd = [
            "pip-licenses",
            "--format=json",
        ]

        if verbose:
            console.print(f"Running: {' '.join(cmd)}")

        # Change to the target directory
        original_cwd = os.getcwd()
        os.chdir(path)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        os.chdir(original_cwd)

        if result.returncode == 0:
            try:
                licenses = json.loads(result.stdout)
            except json.JSONDecodeError:
                licenses = []
        else:
            licenses = []

        # Check for problematic licenses
        problematic_licenses = ["GPL", "AGPL", "LGPL"]
        issues = []

        for license_info in licenses:
            license_name = license_info.get("License", "").upper()
            for problematic in problematic_licenses:
                if problematic in license_name:
                    issues.append({
                        "package": license_info.get("Name"),
                        "license": license_name,
                        "issue": f"Potentially problematic license: {license_name}"
                    })

        return {
            "success": True,
            "results": {
                "licenses": licenses,
                "issues": issues,
            },
            "issues_count": {
                "high": len(issues),
                "medium": 0,
                "low": 0,
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "issues_count": {"high": 0, "medium": 0, "low": 0}
        }


def check_security_policies(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Check for security policy compliance."""
    issues = []

    # Check for required security files
    required_files = [
        "SECURITY.md",
        ".github/SECURITY.md",
        "security.md",
    ]

    security_file_found = False
    for file_name in required_files:
        if (path / file_name).exists():
            security_file_found = True
            break

    if not security_file_found:
        issues.append({
            "type": "missing_security_policy",
            "message": "No security policy file found",
            "severity": "medium"
        })

    # Check for .gitignore
    if not (path / ".gitignore").exists():
        issues.append({
            "type": "missing_gitignore",
            "message": "No .gitignore file found",
            "severity": "low"
        })

    # Check for secrets in .gitignore
    if (path / ".gitignore").exists():
        with open(path / ".gitignore", "r") as f:
            gitignore_content = f.read()

        secret_patterns = ["*.key", "*.pem", "secrets", ".env"]
        missing_patterns = []

        for pattern in secret_patterns:
            if pattern not in gitignore_content:
                missing_patterns.append(pattern)

        if missing_patterns:
            issues.append({
                "type": "gitignore_secrets",
                "message": f"Missing secret patterns in .gitignore: {', '.join(missing_patterns)}",
                "severity": "medium"
            })

    return {
        "success": True,
        "results": {
            "issues": issues,
        },
        "issues_count": {
            "high": len([i for i in issues if i.get("severity") == "high"]),
            "medium": len([i for i in issues if i.get("severity") == "medium"]),
            "low": len([i for i in issues if i.get("severity") == "low"]),
        }
    }


def check_data_governance(path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Check for data governance compliance."""
    issues = []

    # Check for data classification
    data_files = list(path.glob("**/*.csv")) + list(path.glob("**/*.json")) + list(path.glob("**/*.parquet"))

    if data_files:
        # Check for data classification documentation
        classification_files = [
            "DATA_CLASSIFICATION.md",
            "data-classification.md",
            "docs/data-classification.md",
        ]

        classification_found = False
        for file_name in classification_files:
            if (path / file_name).exists():
                classification_found = True
                break

        if not classification_found:
            issues.append({
                "type": "missing_data_classification",
                "message": "Data files found but no data classification documentation",
                "severity": "medium"
            })

    return {
        "success": True,
        "results": {
            "issues": issues,
        },
        "issues_count": {
            "high": len([i for i in issues if i.get("severity") == "high"]),
            "medium": len([i for i in issues if i.get("severity") == "medium"]),
            "low": len([i for i in issues if i.get("severity") == "low"]),
        }
    }


def calculate_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate summary statistics from scan results."""
    total_high = 0
    total_medium = 0
    total_low = 0

    for scan_type, scan_results in results.items():
        if scan_type == "metadata":
            continue

        if isinstance(scan_results, dict):
            for tool, tool_results in scan_results.items():
                if isinstance(tool_results, dict) and "issues_count" in tool_results:
                    counts = tool_results["issues_count"]
                    total_high += counts.get("high", 0)
                    total_medium += counts.get("medium", 0)
                    total_low += counts.get("low", 0)

    total_issues = total_high + total_medium + total_low

    # Determine overall risk level
    if total_high > 0:
        risk_level = "HIGH"
    elif total_medium > 5:
        risk_level = "MEDIUM"
    elif total_low > 10:
        risk_level = "LOW"
    else:
        risk_level = "MINIMAL"

    return {
        "total_issues": total_issues,
        "high_severity": total_high,
        "medium_severity": total_medium,
        "low_severity": total_low,
        "risk_level": risk_level,
    }


def print_summary(summary: Dict[str, Any]) -> None:
    """Print scan summary."""
    console.print("\n" + "="*50)
    console.print(Panel.fit("📊 Security Scan Summary", style="bold blue"))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="white")

    table.add_row("Total Issues", str(summary["total_issues"]))
    table.add_row("High Severity", f"[red]{summary['high_severity']}[/red]")
    table.add_row("Medium Severity", f"[yellow]{summary['medium_severity']}[/yellow]")
    table.add_row("Low Severity", f"[green]{summary['low_severity']}[/green]")
    table.add_row("Risk Level", f"[bold]{summary['risk_level']}[/bold]")

    console.print(table)

    # Risk level indicator
    if summary["risk_level"] == "HIGH":
        console.print("\n🚨 [bold red]HIGH RISK[/bold red] - Immediate action required!")
    elif summary["risk_level"] == "MEDIUM":
        console.print("\n⚠️  [bold yellow]MEDIUM RISK[/bold yellow] - Review and address issues")
    elif summary["risk_level"] == "LOW":
        console.print("\n🟡 [bold blue]LOW RISK[/bold blue] - Monitor and improve")
    else:
        console.print("\n✅ [bold green]MINIMAL RISK[/bold green] - Good security posture")


def format_text_report(results: Dict[str, Any]) -> str:
    """Format results as text report."""
    report = []
    report.append("DevSecOps Security Scan Report")
    report.append("=" * 40)
    report.append(f"Timestamp: {results['metadata']['timestamp']}")
    report.append(f"Path: {results['metadata']['path']}")
    report.append(f"Scan Type: {results['metadata']['scan_type']}")
    report.append("")

    # Summary
    summary = results["summary"]
    report.append("SUMMARY")
    report.append("-" * 20)
    report.append(f"Total Issues: {summary['total_issues']}")
    report.append(f"High Severity: {summary['high_severity']}")
    report.append(f"Medium Severity: {summary['medium_severity']}")
    report.append(f"Low Severity: {summary['low_severity']}")
    report.append(f"Risk Level: {summary['risk_level']}")
    report.append("")

    # Detailed results
    for scan_type, scan_results in results.items():
        if scan_type in ["metadata", "summary"]:
            continue

        report.append(f"{scan_type.upper()} SCAN RESULTS")
        report.append("-" * 30)

        if isinstance(scan_results, dict):
            for tool, tool_results in scan_results.items():
                report.append(f"  {tool}:")
                if isinstance(tool_results, dict):
                    if "success" in tool_results:
                        report.append(f"    Success: {tool_results['success']}")
                    if "issues_count" in tool_results:
                        counts = tool_results["issues_count"]
                        report.append(f"    Issues: H:{counts.get('high', 0)} M:{counts.get('medium', 0)} L:{counts.get('low', 0)}")
                    if "error" in tool_results:
                        report.append(f"    Error: {tool_results['error']}")

        report.append("")

    return "\n".join(report)


def format_html_report(results: Dict[str, Any]) -> str:
    """Format results as HTML report."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>DevSecOps Security Scan Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
            .summary {{ background-color: #e8f4fd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .high {{ color: #d32f2f; }}
            .medium {{ color: #f57c00; }}
            .low {{ color: #388e3c; }}
            .section {{ margin: 20px 0; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>DevSecOps Security Scan Report</h1>
            <p><strong>Timestamp:</strong> {results['metadata']['timestamp']}</p>
            <p><strong>Path:</strong> {results['metadata']['path']}</p>
            <p><strong>Scan Type:</strong> {results['metadata']['scan_type']}</p>
        </div>

        <div class="summary">
            <h2>Summary</h2>
            <table>
                <tr><th>Metric</th><th>Count</th></tr>
                <tr><td>Total Issues</td><td>{results['summary']['total_issues']}</td></tr>
                <tr><td>High Severity</td><td class="high">{results['summary']['high_severity']}</td></tr>
                <tr><td>Medium Severity</td><td class="medium">{results['summary']['medium_severity']}</td></tr>
                <tr><td>Low Severity</td><td class="low">{results['summary']['low_severity']}</td></tr>
                <tr><td>Risk Level</td><td><strong>{results['summary']['risk_level']}</strong></td></tr>
            </table>
        </div>
    """

    # Add detailed results
    for scan_type, scan_results in results.items():
        if scan_type in ["metadata", "summary"]:
            continue

        html += f"""
        <div class="section">
            <h2>{scan_type.title()} Scan Results</h2>
            <table>
                <tr><th>Tool</th><th>Success</th><th>High</th><th>Medium</th><th>Low</th></tr>
        """

        if isinstance(scan_results, dict):
            for tool, tool_results in scan_results.items():
                if isinstance(tool_results, dict):
                    success = tool_results.get("success", False)
                    counts = tool_results.get("issues_count", {})
                    html += f"""
                    <tr>
                        <td>{tool}</td>
                        <td>{'✅' if success else '❌'}</td>
                        <td class="high">{counts.get('high', 0)}</td>
                        <td class="medium">{counts.get('medium', 0)}</td>
                        <td class="low">{counts.get('low', 0)}</td>
                    </tr>
                    """

        html += "</table></div>"

    html += """
    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    app()
