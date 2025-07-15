"""
Unit tests for security scanner
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

from security.scanner import (
    scan_code,
    run_bandit,
    run_semgrep,
    scan_dependencies,
    run_safety,
    scan_secrets,
    calculate_summary,
    format_text_report
)


@pytest.fixture
def temp_project_path():
    """Create temporary project path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_bandit_output():
    """Mock Bandit output."""
    return {
        "metrics": {
            "high": 2,
            "medium": 3,
            "low": 1
        },
        "results": [
            {
                "filename": "test.py",
                "issue_severity": "HIGH",
                "issue_text": "Use of insecure MD5 hash function"
            }
        ]
    }


@pytest.fixture
def mock_semgrep_output():
    """Mock Semgrep output."""
    return {
        "results": [
            {
                "path": "test.py",
                "extra": {
                    "severity": "ERROR",
                    "message": "SQL injection vulnerability"
                }
            }
        ]
    }


def test_run_bandit_success(temp_project_path, mock_bandit_output):
    """Test successful Bandit scan."""
    with patch('subprocess.run') as mock_run, \
         patch('builtins.open', mock_open(read_data=json.dumps(mock_bandit_output))), \
         patch('os.unlink'):
        
        mock_run.return_value.returncode = 0
        
        result = run_bandit(temp_project_path)
        
        assert result["success"] is True
        assert result["issues_count"]["high"] == 2
        assert result["issues_count"]["medium"] == 3
        assert result["issues_count"]["low"] == 1


def test_run_bandit_failure(temp_project_path):
    """Test Bandit scan failure."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = Exception("Bandit not found")
        
        result = run_bandit(temp_project_path)
        
        assert result["success"] is False
        assert "Bandit not found" in result["error"]
        assert result["issues_count"]["high"] == 0


def test_run_semgrep_success(temp_project_path, mock_semgrep_output):
    """Test successful Semgrep scan."""
    with patch('subprocess.run') as mock_run, \
         patch('builtins.open', mock_open(read_data=json.dumps(mock_semgrep_output))), \
         patch('os.unlink'):
        
        mock_run.return_value.returncode = 0
        
        result = run_semgrep(temp_project_path)
        
        assert result["success"] is True
        assert result["issues_count"]["high"] == 1


def test_scan_code(temp_project_path):
    """Test code scanning."""
    with patch('security.scanner.run_bandit') as mock_bandit, \
         patch('security.scanner.run_semgrep') as mock_semgrep:
        
        mock_bandit.return_value = {
            "success": True,
            "issues_count": {"high": 1, "medium": 0, "low": 0}
        }
        mock_semgrep.return_value = {
            "success": True,
            "issues_count": {"high": 0, "medium": 1, "low": 0}
        }
        
        result = scan_code(temp_project_path)
        
        assert "bandit" in result
        assert "semgrep" in result
        mock_bandit.assert_called_once_with(temp_project_path, False)
        mock_semgrep.assert_called_once_with(temp_project_path, False)


def test_run_safety_success(temp_project_path):
    """Test successful Safety scan."""
    mock_output = [
        {
            "package": "requests",
            "installed_version": "2.25.1",
            "vulnerability": "CVE-2021-33503"
        }
    ]
    
    with patch('subprocess.run') as mock_run, \
         patch('builtins.open', mock_open(read_data=json.dumps(mock_output))), \
         patch('os.unlink'), \
         patch('os.chdir'), \
         patch('os.getcwd', return_value="/test"):
        
        mock_run.return_value.returncode = 0
        
        result = run_safety(temp_project_path)
        
        assert result["success"] is True
        assert result["issues_count"]["high"] == 1


def test_scan_dependencies(temp_project_path):
    """Test dependency scanning."""
    with patch('security.scanner.run_safety') as mock_safety, \
         patch('security.scanner.run_pip_audit') as mock_pip_audit:
        
        mock_safety.return_value = {
            "success": True,
            "issues_count": {"high": 1, "medium": 0, "low": 0}
        }
        mock_pip_audit.return_value = {
            "success": True,
            "issues_count": {"high": 0, "medium": 1, "low": 0}
        }
        
        result = scan_dependencies(temp_project_path)
        
        assert "safety" in result
        assert "pip_audit" in result


def test_scan_secrets(temp_project_path):
    """Test secrets scanning."""
    mock_output = {
        "results": {
            "test.py": [
                {
                    "type": "Secret Keyword",
                    "line_number": 10
                }
            ]
        }
    }
    
    with patch('subprocess.run') as mock_run, \
         patch('builtins.open', mock_open(read_data=json.dumps(mock_output))), \
         patch('os.unlink'):
        
        mock_run.return_value.returncode = 0
        
        result = scan_secrets(temp_project_path)
        
        assert result["success"] is True
        assert result["issues_count"]["high"] == 1


def test_calculate_summary():
    """Test summary calculation."""
    results = {
        "code": {
            "bandit": {
                "issues_count": {"high": 2, "medium": 1, "low": 0}
            },
            "semgrep": {
                "issues_count": {"high": 1, "medium": 2, "low": 1}
            }
        },
        "dependencies": {
            "safety": {
                "issues_count": {"high": 1, "medium": 0, "low": 0}
            }
        }
    }
    
    summary = calculate_summary(results)
    
    assert summary["total_issues"] == 7
    assert summary["high_severity"] == 4
    assert summary["medium_severity"] == 3
    assert summary["low_severity"] == 1
    assert summary["risk_level"] == "HIGH"


def test_calculate_summary_minimal_risk():
    """Test summary calculation with minimal risk."""
    results = {
        "code": {
            "bandit": {
                "issues_count": {"high": 0, "medium": 0, "low": 1}
            }
        }
    }
    
    summary = calculate_summary(results)
    
    assert summary["total_issues"] == 1
    assert summary["high_severity"] == 0
    assert summary["medium_severity"] == 0
    assert summary["low_severity"] == 1
    assert summary["risk_level"] == "MINIMAL"


def test_format_text_report():
    """Test text report formatting."""
    results = {
        "metadata": {
            "timestamp": "2024-01-01T00:00:00Z",
            "path": "/test/path",
            "scan_type": "all"
        },
        "summary": {
            "total_issues": 5,
            "high_severity": 2,
            "medium_severity": 2,
            "low_severity": 1,
            "risk_level": "HIGH"
        },
        "code": {
            "bandit": {
                "success": True,
                "issues_count": {"high": 2, "medium": 1, "low": 0}
            }
        }
    }
    
    report = format_text_report(results)
    
    assert "DevSecOps Security Scan Report" in report
    assert "2024-01-01T00:00:00Z" in report
    assert "/test/path" in report
    assert "Total Issues: 5" in report
    assert "Risk Level: HIGH" in report
    assert "CODE SCAN RESULTS" in report
    assert "bandit:" in report


@pytest.mark.parametrize("risk_level,expected_high,expected_medium", [
    ("HIGH", 1, 0),
    ("MEDIUM", 0, 6),
    ("LOW", 0, 3),
    ("MINIMAL", 0, 0)
])
def test_risk_level_calculation(risk_level, expected_high, expected_medium):
    """Test risk level calculation with different scenarios."""
    results = {
        "code": {
            "bandit": {
                "issues_count": {"high": expected_high, "medium": expected_medium, "low": 0}
            }
        }
    }
    
    summary = calculate_summary(results)
    assert summary["risk_level"] == risk_level
