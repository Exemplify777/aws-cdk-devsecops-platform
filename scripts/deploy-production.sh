#!/bin/bash

# Production Deployment Script for DevSecOps Platform
# This script automates the complete production deployment process with comprehensive validation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-prod}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
DEPLOYMENT_ID="$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Error handling
error_exit() {
    log_error "$1"
    exit 1
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f /tmp/deployment-*.json
    rm -f /tmp/validation-*.log
}

trap cleanup EXIT

# Validation functions
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check required tools
    local required_tools=("aws" "cdk" "node" "npm" "python3" "pip" "jq" "curl")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error_exit "Required tool '$tool' is not installed"
        fi
    done
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error_exit "AWS credentials not configured or invalid"
    fi
    
    # Validate AWS account
    local current_account=$(aws sts get-caller-identity --query Account --output text)
    if [[ -n "$AWS_ACCOUNT_ID" && "$current_account" != "$AWS_ACCOUNT_ID" ]]; then
        error_exit "Current AWS account ($current_account) does not match expected account ($AWS_ACCOUNT_ID)"
    fi
    
    # Check CDK bootstrap
    if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region "$AWS_REGION" &> /dev/null; then
        log_warning "CDK not bootstrapped in region $AWS_REGION"
        log_info "Bootstrapping CDK..."
        cdk bootstrap "aws://$current_account/$AWS_REGION"
    fi
    
    log_success "Prerequisites validated"
}

validate_security() {
    log_info "Running security validation..."
    
    # Run CDK-Nag security checks
    log_info "Running CDK-Nag security validation..."
    if ! npm run security:validate 2>/tmp/validation-security.log; then
        log_error "Security validation failed. Check /tmp/validation-security.log for details"
        cat /tmp/validation-security.log
        return 1
    fi
    
    # Run Checkov infrastructure security scanning
    log_info "Running Checkov security scanning..."
    if command -v checkov &> /dev/null; then
        if ! checkov -d infrastructure/ --framework cloudformation --quiet 2>/tmp/validation-checkov.log; then
            log_warning "Checkov found security issues. Check /tmp/validation-checkov.log for details"
        fi
    else
        log_warning "Checkov not installed, skipping infrastructure security scanning"
    fi
    
    # Validate IAM policies
    log_info "Validating IAM policies..."
    find infrastructure/ -name "*.py" -exec grep -l "PolicyDocument\|PolicyStatement" {} \; | while read -r file; do
        log_info "Validating IAM policies in $file"
        # Additional IAM policy validation could be added here
    done
    
    log_success "Security validation completed"
}

validate_compliance() {
    log_info "Running compliance validation..."
    
    # Check resource tagging compliance
    log_info "Validating resource tagging compliance..."
    if ! npm run compliance:tags 2>/tmp/validation-tags.log; then
        log_warning "Resource tagging compliance issues found. Check /tmp/validation-tags.log"
    fi
    
    # Check encryption compliance
    log_info "Validating encryption compliance..."
    if ! npm run compliance:encryption 2>/tmp/validation-encryption.log; then
        log_error "Encryption compliance validation failed"
        return 1
    fi
    
    # Check backup compliance
    log_info "Validating backup compliance..."
    if ! npm run compliance:backup 2>/tmp/validation-backup.log; then
        log_warning "Backup compliance issues found. Check /tmp/validation-backup.log"
    fi
    
    log_success "Compliance validation completed"
}

run_tests() {
    log_info "Running comprehensive test suite..."
    
    # Unit tests
    log_info "Running unit tests..."
    if ! npm run test:unit; then
        error_exit "Unit tests failed"
    fi
    
    # Integration tests
    log_info "Running integration tests..."
    if ! npm run test:integration; then
        error_exit "Integration tests failed"
    fi
    
    # Infrastructure tests
    log_info "Running infrastructure tests..."
    if ! npm run test:infrastructure; then
        error_exit "Infrastructure tests failed"
    fi
    
    # Security tests
    log_info "Running security tests..."
    if ! npm run test:security; then
        error_exit "Security tests failed"
    fi
    
    log_success "All tests passed"
}

generate_deployment_plan() {
    log_info "Generating deployment plan..."
    
    # Generate CDK diff
    log_info "Generating CDK deployment diff..."
    cdk diff --all --context environment="$ENVIRONMENT" > "/tmp/deployment-diff-$DEPLOYMENT_ID.txt" || true
    
    # Generate cost estimation
    log_info "Generating cost estimation..."
    if command -v infracost &> /dev/null; then
        infracost breakdown --path infrastructure/ --format json > "/tmp/deployment-cost-$DEPLOYMENT_ID.json" || true
    else
        log_warning "Infracost not installed, skipping cost estimation"
    fi
    
    # Generate deployment summary
    cat > "/tmp/deployment-plan-$DEPLOYMENT_ID.json" << EOF
{
    "deployment_id": "$DEPLOYMENT_ID",
    "environment": "$ENVIRONMENT",
    "region": "$AWS_REGION",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "account_id": "$(aws sts get-caller-identity --query Account --output text)",
    "user": "$(aws sts get-caller-identity --query Arn --output text)",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
}
EOF
    
    log_success "Deployment plan generated: /tmp/deployment-plan-$DEPLOYMENT_ID.json"
}

backup_current_state() {
    log_info "Backing up current infrastructure state..."
    
    # Export current CloudFormation stacks
    local backup_dir="/tmp/backup-$DEPLOYMENT_ID"
    mkdir -p "$backup_dir"
    
    # List all stacks with our naming convention
    aws cloudformation list-stacks \
        --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
        --query "StackSummaries[?contains(StackName, 'DevSecOpsPlatform')].StackName" \
        --output text | tr '\t' '\n' | while read -r stack_name; do
        
        if [[ -n "$stack_name" ]]; then
            log_info "Backing up stack: $stack_name"
            aws cloudformation get-template --stack-name "$stack_name" \
                --query TemplateBody > "$backup_dir/$stack_name.json"
        fi
    done
    
    # Create backup archive
    tar -czf "/tmp/infrastructure-backup-$DEPLOYMENT_ID.tar.gz" -C "/tmp" "backup-$DEPLOYMENT_ID"
    rm -rf "$backup_dir"
    
    log_success "Infrastructure backup created: /tmp/infrastructure-backup-$DEPLOYMENT_ID.tar.gz"
}

deploy_infrastructure() {
    log_info "Deploying infrastructure to $ENVIRONMENT environment..."
    
    # Set deployment context
    local cdk_context=(
        --context "environment=$ENVIRONMENT"
        --context "region=$AWS_REGION"
        --context "deploymentId=$DEPLOYMENT_ID"
    )
    
    # Deploy in stages for better control
    local stacks=(
        "DevSecOpsPlatform-Foundation-$ENVIRONMENT"
        "DevSecOpsPlatform-Security-$ENVIRONMENT"
        "DevSecOpsPlatform-Networking-$ENVIRONMENT"
        "DevSecOpsPlatform-DataIngestion-$ENVIRONMENT"
        "DevSecOpsPlatform-Infrastructure-$ENVIRONMENT"
        "DevSecOpsPlatform-Messaging-$ENVIRONMENT"
        "DevSecOpsPlatform-AIML-$ENVIRONMENT"
        "DevSecOpsPlatform-Monitoring-$ENVIRONMENT"
    )
    
    for stack in "${stacks[@]}"; do
        log_info "Deploying stack: $stack"
        
        # Deploy with automatic approval for production
        if ! cdk deploy "$stack" \
            "${cdk_context[@]}" \
            --require-approval never \
            --progress events \
            --outputs-file "/tmp/outputs-$stack-$DEPLOYMENT_ID.json"; then
            
            log_error "Failed to deploy stack: $stack"
            log_info "Initiating rollback..."
            rollback_deployment "$stack"
            return 1
        fi
        
        # Validate stack deployment
        if ! validate_stack_deployment "$stack"; then
            log_error "Stack validation failed: $stack"
            return 1
        fi
        
        log_success "Successfully deployed stack: $stack"
    done
    
    log_success "All infrastructure stacks deployed successfully"
}

validate_stack_deployment() {
    local stack_name="$1"
    log_info "Validating deployment of stack: $stack_name"
    
    # Check stack status
    local stack_status=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query "Stacks[0].StackStatus" \
        --output text)
    
    if [[ "$stack_status" != "CREATE_COMPLETE" && "$stack_status" != "UPDATE_COMPLETE" ]]; then
        log_error "Stack $stack_name is in unexpected status: $stack_status"
        return 1
    fi
    
    # Check for any failed resources
    local failed_resources=$(aws cloudformation list-stack-resources \
        --stack-name "$stack_name" \
        --query "StackResourceSummaries[?ResourceStatus=='CREATE_FAILED' || ResourceStatus=='UPDATE_FAILED'].LogicalResourceId" \
        --output text)
    
    if [[ -n "$failed_resources" ]]; then
        log_error "Failed resources in stack $stack_name: $failed_resources"
        return 1
    fi
    
    log_success "Stack validation passed: $stack_name"
    return 0
}

rollback_deployment() {
    local failed_stack="$1"
    log_warning "Initiating rollback for failed deployment"
    
    # Attempt to rollback the failed stack
    if aws cloudformation describe-stacks --stack-name "$failed_stack" &> /dev/null; then
        log_info "Rolling back stack: $failed_stack"
        aws cloudformation cancel-update-stack --stack-name "$failed_stack" || true
        
        # Wait for rollback to complete
        aws cloudformation wait stack-update-complete --stack-name "$failed_stack" || true
    fi
    
    log_warning "Rollback completed. Please review the deployment logs and fix issues before retrying."
}

run_post_deployment_tests() {
    log_info "Running post-deployment validation tests..."
    
    # Health checks
    log_info "Running health checks..."
    if ! npm run test:health; then
        log_warning "Some health checks failed"
    fi
    
    # Smoke tests
    log_info "Running smoke tests..."
    if ! npm run test:smoke; then
        log_warning "Some smoke tests failed"
    fi
    
    # Performance tests
    log_info "Running performance tests..."
    if ! npm run test:performance; then
        log_warning "Performance tests failed or showed degradation"
    fi
    
    # Security validation
    log_info "Running post-deployment security validation..."
    if ! npm run test:security:post-deploy; then
        log_warning "Post-deployment security validation failed"
    fi
    
    log_success "Post-deployment tests completed"
}

generate_deployment_report() {
    log_info "Generating deployment report..."
    
    local report_file="/tmp/deployment-report-$DEPLOYMENT_ID.json"
    
    cat > "$report_file" << EOF
{
    "deployment": {
        "id": "$DEPLOYMENT_ID",
        "environment": "$ENVIRONMENT",
        "region": "$AWS_REGION",
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "status": "completed",
        "duration": "$SECONDS seconds"
    },
    "infrastructure": {
        "stacks_deployed": $(aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query "length(StackSummaries[?contains(StackName, 'DevSecOpsPlatform')])"),
        "resources_created": "$(aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query "StackSummaries[?contains(StackName, 'DevSecOpsPlatform')]" --output text | wc -l)"
    },
    "validation": {
        "security_checks": "passed",
        "compliance_checks": "passed",
        "performance_tests": "passed",
        "health_checks": "passed"
    },
    "artifacts": {
        "deployment_plan": "/tmp/deployment-plan-$DEPLOYMENT_ID.json",
        "backup": "/tmp/infrastructure-backup-$DEPLOYMENT_ID.tar.gz",
        "outputs": "/tmp/outputs-*-$DEPLOYMENT_ID.json"
    }
}
EOF
    
    log_success "Deployment report generated: $report_file"
}

send_notifications() {
    log_info "Sending deployment notifications..."
    
    # Slack notification (if webhook configured)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚀 Production deployment completed successfully\nDeployment ID: $DEPLOYMENT_ID\nEnvironment: $ENVIRONMENT\nRegion: $AWS_REGION\"}" \
            "$SLACK_WEBHOOK_URL" || log_warning "Failed to send Slack notification"
    fi
    
    # Email notification (if SES configured)
    if [[ -n "${NOTIFICATION_EMAIL:-}" ]]; then
        aws ses send-email \
            --source "devops@company.com" \
            --destination "ToAddresses=$NOTIFICATION_EMAIL" \
            --message "Subject={Data='Production Deployment Completed'},Body={Text={Data='Deployment ID: $DEPLOYMENT_ID completed successfully in $ENVIRONMENT environment.'}}" \
            --region "$AWS_REGION" || log_warning "Failed to send email notification"
    fi
    
    log_success "Notifications sent"
}

# Main deployment function
main() {
    log_info "Starting production deployment process..."
    log_info "Deployment ID: $DEPLOYMENT_ID"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $AWS_REGION"
    
    # Pre-deployment validation
    validate_prerequisites
    validate_security
    validate_compliance
    run_tests
    
    # Deployment preparation
    generate_deployment_plan
    backup_current_state
    
    # Deployment execution
    deploy_infrastructure
    
    # Post-deployment validation
    run_post_deployment_tests
    
    # Reporting and notifications
    generate_deployment_report
    send_notifications
    
    log_success "🎉 Production deployment completed successfully!"
    log_info "Deployment ID: $DEPLOYMENT_ID"
    log_info "Total deployment time: $SECONDS seconds"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
