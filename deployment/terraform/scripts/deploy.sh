#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${1:-"dev"}
ACTION=${2:-"apply"}
TERRAFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Help function
show_help() {
    echo "Usage: $0 [environment] [action]"
    echo ""
    echo "Environments: dev, staging, prod"
    echo "Actions: plan, apply, destroy, refresh"
    echo ""
    echo "Examples:"
    echo "  $0 dev plan"
    echo "  $0 staging apply"
    echo "  $0 prod apply"
}

# Validate environment
case $ENVIRONMENT in
    dev|staging|prod)
        echo -e "${GREEN}Environment: $ENVIRONMENT${NC}"
        ;;
    *)
        echo -e "${RED}Invalid environment. Use dev, staging, or prod.${NC}"
        show_help
        exit 1
        ;;
esac

# Validate action
case $ACTION in
    plan|apply|destroy|refresh)
        echo -e "${GREEN}Action: $ACTION${NC}"
        ;;
    *)
        echo -e "${RED}Invalid action. Use plan, apply, destroy, or refresh.${NC}"
        show_help
        exit 1
        ;;
esac

# Check for required tools
check_requirements() {
    echo -e "${YELLOW}Checking requirements...${NC}"
    
    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}Terraform is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}kubectl is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    if ! command -v helm &> /dev/null; then
        echo -e "${RED}Helm is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}All requirements satisfied.${NC}"
}

# Check Kubernetes connection
check_k8s_connection() {
    echo -e "${YELLOW}Checking Kubernetes connection...${NC}"
    
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}Cannot connect to Kubernetes cluster. Please check your kubeconfig.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Kubernetes connection successful.${NC}"
}

# Initialize Terraform
init_terraform() {
    echo -e "${YELLOW}Initializing Terraform...${NC}"
    
    cd "$TERRAFORM_DIR/environments/$ENVIRONMENT"
    
    terraform init \
        -backend-config="key=parking-management-${ENVIRONMENT}/terraform.tfstate" \
        -reconfigure
    
    echo -e "${GREEN}Terraform initialized.${NC}"
}

# Plan Terraform changes
plan_terraform() {
    echo -e "${YELLOW}Planning Terraform changes...${NC}"
    
    cd "$TERRAFORM_DIR/environments/$ENVIRONMENT"
    
    terraform plan \
        -var-file="terraform.tfvars" \
        -out="tfplan"
    
    echo -e "${GREEN}Terraform plan completed.${NC}"
}

# Apply Terraform changes
apply_terraform() {
    echo -e "${YELLOW}Applying Terraform changes...${NC}"
    
    cd "$TERRAFORM_DIR/environments/$ENVIRONMENT"
    
    if [ -f "tfplan" ]; then
        terraform apply "tfplan"
    else
        terraform apply \
            -var-file="terraform.tfvars" \
            -auto-approve
    fi
    
    echo -e "${GREEN}Terraform apply completed.${NC}"
}

# Destroy Terraform resources
destroy_terraform() {
    echo -e "${RED}WARNING: This will destroy all resources in $ENVIRONMENT environment.${NC}"
    read -p "Are you sure you want to continue? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Destroying Terraform resources...${NC}"
        
        cd "$TERRAFORM_DIR/environments/$ENVIRONMENT"
        
        terraform destroy \
            -var-file="terraform.tfvars" \
            -auto-approve
        
        echo -e "${GREEN}Terraform destroy completed.${NC}"
    else
        echo -e "${YELLOW}Destroy cancelled.${NC}"
    fi
}

# Refresh Terraform state
refresh_terraform() {
    echo -e "${YELLOW}Refreshing Terraform state...${NC}"
    
    cd "$TERRAFORM_DIR/environments/$ENVIRONMENT"
    
    terraform refresh \
        -var-file="terraform.tfvars"
    
    echo -e "${GREEN}Terraform refresh completed.${NC}"
}

# Show outputs
show_outputs() {
    echo -e "${YELLOW}Getting Terraform outputs...${NC}"
    
    cd "$TERRAFORM_DIR/environments/$ENVIRONMENT"
    
    terraform output
    
    echo -e "${GREEN}Outputs displayed.${NC}"
}

# Main deployment function
deploy() {
    check_requirements
    check_k8s_connection
    init_terraform
    
    case $ACTION in
        plan)
            plan_terraform
            ;;
        apply)
            plan_terraform
            apply_terraform
            show_outputs
            ;;
        destroy)
            destroy_terraform
            ;;
        refresh)
            refresh_terraform
            show_outputs
            ;;
    esac
}

# Run deployment
deploy

exit 0