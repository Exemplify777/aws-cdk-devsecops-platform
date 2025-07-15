# CLI API Reference

Complete reference for the DevSecOps Platform CLI (`ddk-cli`).

## Installation

```bash
pip install ddk-cli
# or
pip install -e .  # for development
```

## Global Options

All commands support these global options:

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--help` | `-h` | Show help message | |
| `--verbose` | `-v` | Enable verbose output | `False` |
| `--quiet` | `-q` | Suppress output | `False` |
| `--config` | `-c` | Configuration file path | `~/.ddk/config.yaml` |
| `--profile` | `-p` | AWS profile to use | `default` |

## Commands

### `ddk-cli init`

Initialize CLI configuration.

```bash
ddk-cli init [OPTIONS]
```

**Options:**
- `--interactive/--no-interactive`: Interactive setup (default: `True`)
- `--config PATH`: Configuration file path
- `--aws-region TEXT`: AWS region (default: `us-east-1`)
- `--github-org TEXT`: GitHub organization

**Examples:**
```bash
# Interactive setup
ddk-cli init

# Non-interactive setup
ddk-cli init --no-interactive --aws-region us-west-2 --github-org my-org
```

### `ddk-cli create-project`

Create a new project from a template.

```bash
ddk-cli create-project PROJECT_NAME [OPTIONS]
```

**Arguments:**
- `PROJECT_NAME`: Name of the project to create

**Options:**
- `--template TEXT`: Template to use (default: `data-pipeline`)
- `--env TEXT`: Environment to deploy to (default: `dev`)
- `--github/--no-github`: Create GitHub repository (default: `True`)
- `--deploy/--no-deploy`: Deploy after creation (default: `False`)
- `--output-dir PATH`: Output directory (default: current directory)

**Examples:**
```bash
# Create basic data pipeline
ddk-cli create-project my-pipeline --template data-pipeline

# Create ML workflow with GitHub repo and auto-deploy
ddk-cli create-project ml-model --template ml-workflow --github --deploy

# Create streaming pipeline in specific directory
ddk-cli create-project stream-processor --template streaming --output-dir ./projects
```

### `ddk-cli templates`

List available project templates.

```bash
ddk-cli templates [OPTIONS]
```

**Options:**
- `--format TEXT`: Output format (`table`, `json`, `yaml`) (default: `table`)
- `--filter TEXT`: Filter templates by name or type

**Examples:**
```bash
# List all templates
ddk-cli templates

# List templates in JSON format
ddk-cli templates --format json

# Filter ML templates
ddk-cli templates --filter ml
```

### `ddk-cli deploy`

Deploy a project to AWS.

```bash
ddk-cli deploy [PROJECT_NAME] [OPTIONS]
```

**Arguments:**
- `PROJECT_NAME`: Name of the project to deploy (optional if in project directory)

**Options:**
- `--env TEXT`: Environment to deploy to (default: `dev`)
- `--stack TEXT`: Specific stack to deploy
- `--approve/--no-approve`: Auto-approve deployment (default: `False`)
- `--rollback/--no-rollback`: Enable auto-rollback (default: `True`)

**Examples:**
```bash
# Deploy current project to dev
ddk-cli deploy --env dev

# Deploy specific project to staging with approval
ddk-cli deploy my-pipeline --env staging --approve

# Deploy specific stack
ddk-cli deploy --stack DataPipelineStack --env dev
```

### `ddk-cli status`

Check project deployment status.

```bash
ddk-cli status [PROJECT_NAME] [OPTIONS]
```

**Arguments:**
- `PROJECT_NAME`: Name of the project to check

**Options:**
- `--env TEXT`: Environment to check (default: `dev`)
- `--format TEXT`: Output format (`table`, `json`, `yaml`) (default: `table`)
- `--watch`: Watch for changes

**Examples:**
```bash
# Check project status
ddk-cli status my-pipeline --env dev

# Watch status changes
ddk-cli status my-pipeline --env dev --watch

# Get status in JSON format
ddk-cli status my-pipeline --env dev --format json
```

### `ddk-cli logs`

View project logs.

```bash
ddk-cli logs [PROJECT_NAME] [OPTIONS]
```

**Arguments:**
- `PROJECT_NAME`: Name of the project

**Options:**
- `--env TEXT`: Environment (default: `dev`)
- `--follow/--no-follow`: Follow log output (default: `False`)
- `--lines INTEGER`: Number of lines to show (default: `100`)
- `--level TEXT`: Log level filter (`DEBUG`, `INFO`, `WARN`, `ERROR`)
- `--service TEXT`: Filter by service name

**Examples:**
```bash
# View recent logs
ddk-cli logs my-pipeline --env dev

# Follow logs in real-time
ddk-cli logs my-pipeline --env dev --follow

# Show only errors
ddk-cli logs my-pipeline --env dev --level ERROR
```

### `ddk-cli list-projects`

List all projects.

```bash
ddk-cli list-projects [OPTIONS]
```

**Options:**
- `--env TEXT`: Filter by environment
- `--format TEXT`: Output format (`table`, `json`, `yaml`) (default: `table`)
- `--owner TEXT`: Filter by owner

**Examples:**
```bash
# List all projects
ddk-cli list-projects

# List projects in production
ddk-cli list-projects --env prod

# List projects owned by user
ddk-cli list-projects --owner john.doe
```

### `ddk-cli destroy`

Destroy project infrastructure.

```bash
ddk-cli destroy [PROJECT_NAME] [OPTIONS]
```

**Arguments:**
- `PROJECT_NAME`: Name of the project to destroy

**Options:**
- `--env TEXT`: Environment (default: `dev`)
- `--force/--no-force`: Force destruction without confirmation (default: `False`)
- `--retain-data/--no-retain-data`: Retain data resources (default: `True`)

**Examples:**
```bash
# Destroy project with confirmation
ddk-cli destroy my-pipeline --env dev

# Force destroy without confirmation
ddk-cli destroy my-pipeline --env dev --force

# Destroy but retain data
ddk-cli destroy my-pipeline --env dev --retain-data
```

### `ddk-cli config`

Manage CLI configuration.

```bash
ddk-cli config [COMMAND] [OPTIONS]
```

**Commands:**
- `show`: Show current configuration
- `set KEY VALUE`: Set configuration value
- `get KEY`: Get configuration value
- `reset`: Reset configuration to defaults

**Examples:**
```bash
# Show current configuration
ddk-cli config show

# Set AWS region
ddk-cli config set aws.region us-west-2

# Get GitHub organization
ddk-cli config get github.organization

# Reset configuration
ddk-cli config reset
```

### `ddk-cli validate`

Validate project configuration and infrastructure.

```bash
ddk-cli validate [PROJECT_NAME] [OPTIONS]
```

**Arguments:**
- `PROJECT_NAME`: Name of the project to validate

**Options:**
- `--env TEXT`: Environment to validate (default: `dev`)
- `--type TEXT`: Validation type (`config`, `infra`, `security`, `all`) (default: `all`)

**Examples:**
```bash
# Validate everything
ddk-cli validate my-pipeline --env dev

# Validate only infrastructure
ddk-cli validate my-pipeline --env dev --type infra

# Validate security configuration
ddk-cli validate my-pipeline --env dev --type security
```

## Configuration

### Configuration File

The CLI configuration is stored in `~/.ddk/config.yaml`:

```yaml
aws:
  region: us-east-1
  profile: default
  dev_account_id: "123456789012"
  staging_account_id: "123456789013"
  prod_account_id: "123456789014"

github:
  organization: my-org
  token: ghp_xxxxxxxxxxxx

templates:
  default_template: data-pipeline
  template_repository: https://github.com/my-org/ddk-templates

security:
  enable_scanning: true
  scan_on_deploy: true
  compliance_frameworks:
    - SOC2
    - ISO27001
    - GDPR

monitoring:
  enable_detailed_monitoring: true
  log_retention_days: 30
  cost_alert_threshold: 100.0
```

### Environment Variables

The CLI also supports environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DDK_AWS_REGION` | AWS region | `us-east-1` |
| `DDK_AWS_PROFILE` | AWS profile | `default` |
| `DDK_CONFIG_PATH` | Configuration file path | `~/.ddk/config.yaml` |
| `DDK_GITHUB_TOKEN` | GitHub token | |
| `DDK_VERBOSE` | Enable verbose output | `false` |

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | General error |
| `2` | Configuration error |
| `3` | AWS error |
| `4` | GitHub error |
| `5` | Validation error |

## Error Handling

The CLI provides detailed error messages and suggestions:

```bash
$ ddk-cli deploy non-existent-project
Error: Project 'non-existent-project' not found.

Suggestions:
  - Check the project name spelling
  - Use 'ddk-cli list-projects' to see available projects
  - Create the project with 'ddk-cli create-project'
```

## Debugging

Enable verbose output for debugging:

```bash
# Enable verbose output
ddk-cli --verbose deploy my-pipeline

# Enable debug logging
DDK_LOG_LEVEL=DEBUG ddk-cli deploy my-pipeline
```

## Shell Completion

Enable shell completion for better CLI experience:

```bash
# Bash
eval "$(_DDK_CLI_COMPLETE=bash_source ddk-cli)"

# Zsh
eval "$(_DDK_CLI_COMPLETE=zsh_source ddk-cli)"

# Fish
eval (env _DDK_CLI_COMPLETE=fish_source ddk-cli)
```

## Examples

### Complete Workflow

```bash
# 1. Initialize CLI
ddk-cli init

# 2. Create a new data pipeline project
ddk-cli create-project sales-analytics --template data-pipeline

# 3. Navigate to project directory
cd sales-analytics

# 4. Deploy to development
ddk-cli deploy --env dev

# 5. Check deployment status
ddk-cli status --env dev

# 6. View logs
ddk-cli logs --env dev --follow

# 7. Deploy to staging
ddk-cli deploy --env staging --approve

# 8. List all projects
ddk-cli list-projects

# 9. Clean up development environment
ddk-cli destroy --env dev --force
```
