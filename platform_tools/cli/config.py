"""
CLI Configuration Management
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class CLIConfig:
    """Manages CLI configuration."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file) if config_file else self._get_default_config_path()
        self.data = self._load_config()
    
    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        config_dir = Path.home() / ".ddk"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "config.json"
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.config_file.exists():
            return self._get_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "aws": {
                "region": os.environ.get("AWS_REGION", "us-east-1"),
                "profile": os.environ.get("AWS_PROFILE", "default"),
            },
            "github": {
                "organization": os.environ.get("GITHUB_ORG", ""),
                "token": os.environ.get("GITHUB_TOKEN", ""),
            },
            "project": {
                "prefix": "data-platform",
                "default_environment": "dev",
            },
            "cli": {
                "output_format": "table",
                "verbose": False,
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split('.')
        data = self.data
        
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        
        data[keys[-1]] = value
    
    def update(self, config: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        self._deep_update(self.data, config)
    
    def _deep_update(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Deep update dictionary."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    def save(self) -> None:
        """Save configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self.data = self._get_default_config()
        self.save()
    
    def validate(self) -> bool:
        """Validate configuration."""
        required_keys = [
            "aws.region",
            "project.prefix",
        ]
        
        for key in required_keys:
            if not self.get(key):
                return False
        
        return True
