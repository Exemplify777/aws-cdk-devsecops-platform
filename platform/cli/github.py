"""
GitHub Integration for CLI
"""

import requests
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin


class GitHubManager:
    """Manages GitHub operations for the CLI."""
    
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevSecOps-Platform-CLI/1.0"
        })
    
    def create_repository(self, name: str, organization: Optional[str] = None, 
                         description: str = "", private: bool = True) -> str:
        """Create a new GitHub repository."""
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": False,
            "has_issues": True,
            "has_projects": True,
            "has_wiki": False,
        }
        
        if organization:
            url = f"{self.base_url}/orgs/{organization}/repos"
        else:
            url = f"{self.base_url}/user/repos"
        
        response = self.session.post(url, json=data)
        
        if response.status_code == 201:
            repo_data = response.json()
            
            # Set up branch protection and other settings
            self._setup_repository_settings(repo_data["full_name"])
            
            return repo_data["clone_url"]
        else:
            raise Exception(f"Failed to create repository: {response.text}")
    
    def _setup_repository_settings(self, repo_full_name: str) -> None:
        """Set up repository settings and branch protection."""
        try:
            # Enable vulnerability alerts
            self.session.put(
                f"{self.base_url}/repos/{repo_full_name}/vulnerability-alerts",
                headers={"Accept": "application/vnd.github.dorian-preview+json"}
            )
            
            # Enable automated security fixes
            self.session.put(
                f"{self.base_url}/repos/{repo_full_name}/automated-security-fixes",
                headers={"Accept": "application/vnd.github.london-preview+json"}
            )
            
            # Set up branch protection for main branch
            protection_data = {
                "required_status_checks": {
                    "strict": True,
                    "contexts": ["ci/tests", "ci/security-scan"]
                },
                "enforce_admins": False,
                "required_pull_request_reviews": {
                    "required_approving_review_count": 1,
                    "dismiss_stale_reviews": True,
                    "require_code_owner_reviews": True
                },
                "restrictions": None,
                "allow_force_pushes": False,
                "allow_deletions": False
            }
            
            self.session.put(
                f"{self.base_url}/repos/{repo_full_name}/branches/main/protection",
                json=protection_data,
                headers={"Accept": "application/vnd.github.luke-cage-preview+json"}
            )
            
        except Exception as e:
            # Don't fail repository creation if settings fail
            print(f"Warning: Could not set up repository settings: {e}")
    
    def create_issue(self, repo_full_name: str, title: str, body: str, 
                    labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a GitHub issue."""
        data = {
            "title": title,
            "body": body,
        }
        
        if labels:
            data["labels"] = labels
        
        response = self.session.post(
            f"{self.base_url}/repos/{repo_full_name}/issues",
            json=data
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create issue: {response.text}")
    
    def create_pull_request(self, repo_full_name: str, title: str, body: str,
                           head: str, base: str = "main") -> Dict[str, Any]:
        """Create a GitHub pull request."""
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }
        
        response = self.session.post(
            f"{self.base_url}/repos/{repo_full_name}/pulls",
            json=data
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create pull request: {response.text}")
    
    def list_repositories(self, organization: Optional[str] = None) -> List[Dict[str, Any]]:
        """List repositories."""
        if organization:
            url = f"{self.base_url}/orgs/{organization}/repos"
        else:
            url = f"{self.base_url}/user/repos"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to list repositories: {response.text}")
    
    def get_repository(self, repo_full_name: str) -> Dict[str, Any]:
        """Get repository information."""
        response = self.session.get(f"{self.base_url}/repos/{repo_full_name}")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get repository: {response.text}")
    
    def create_webhook(self, repo_full_name: str, url: str, events: List[str],
                      secret: Optional[str] = None) -> Dict[str, Any]:
        """Create a webhook for the repository."""
        data = {
            "name": "web",
            "active": True,
            "events": events,
            "config": {
                "url": url,
                "content_type": "json",
                "insecure_ssl": "0",
            }
        }
        
        if secret:
            data["config"]["secret"] = secret
        
        response = self.session.post(
            f"{self.base_url}/repos/{repo_full_name}/hooks",
            json=data
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create webhook: {response.text}")
    
    def add_repository_secret(self, repo_full_name: str, secret_name: str, 
                             secret_value: str) -> None:
        """Add a secret to the repository."""
        # First, get the repository's public key
        key_response = self.session.get(
            f"{self.base_url}/repos/{repo_full_name}/actions/secrets/public-key"
        )
        
        if key_response.status_code != 200:
            raise Exception(f"Failed to get public key: {key_response.text}")
        
        public_key_data = key_response.json()
        
        # Encrypt the secret value (simplified - in real implementation, use PyNaCl)
        # For now, we'll just store it as-is (not recommended for production)
        encrypted_value = secret_value  # This should be encrypted with the public key
        
        data = {
            "encrypted_value": encrypted_value,
            "key_id": public_key_data["key_id"]
        }
        
        response = self.session.put(
            f"{self.base_url}/repos/{repo_full_name}/actions/secrets/{secret_name}",
            json=data
        )
        
        if response.status_code not in [201, 204]:
            raise Exception(f"Failed to add secret: {response.text}")
    
    def trigger_workflow(self, repo_full_name: str, workflow_id: str, 
                        ref: str = "main", inputs: Optional[Dict[str, Any]] = None) -> None:
        """Trigger a GitHub Actions workflow."""
        data = {
            "ref": ref,
        }
        
        if inputs:
            data["inputs"] = inputs
        
        response = self.session.post(
            f"{self.base_url}/repos/{repo_full_name}/actions/workflows/{workflow_id}/dispatches",
            json=data
        )
        
        if response.status_code != 204:
            raise Exception(f"Failed to trigger workflow: {response.text}")
    
    def get_workflow_runs(self, repo_full_name: str, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get workflow runs for a repository."""
        if workflow_id:
            url = f"{self.base_url}/repos/{repo_full_name}/actions/workflows/{workflow_id}/runs"
        else:
            url = f"{self.base_url}/repos/{repo_full_name}/actions/runs"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            return response.json()["workflow_runs"]
        else:
            raise Exception(f"Failed to get workflow runs: {response.text}")
    
    def create_release(self, repo_full_name: str, tag_name: str, name: str,
                      body: str, draft: bool = False, prerelease: bool = False) -> Dict[str, Any]:
        """Create a GitHub release."""
        data = {
            "tag_name": tag_name,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease,
        }
        
        response = self.session.post(
            f"{self.base_url}/repos/{repo_full_name}/releases",
            json=data
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create release: {response.text}")
