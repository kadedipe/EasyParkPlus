#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${1:-"dev"}
TERRAFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Help function
show_help() {
    echo "Usage: $0 [environment]"
    echo ""
    echo "Environments: dev, staging, prod"
    echo ""
    echo "Examples:"
    echo "  $0 dev"
    echo "  $0 staging"
    echo "  $0 prod"
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

# Confirmation
echo -e "${RED}WARNING: This will destroy all resources in $ENVIRONMENT environment.${NC}"
echo -e "${RED}This action cannot be undone.${NC}"
read -p "Are you sure you want to continue? (y/n) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Destroy cancelled.${NC}"
    exit 0
fi

# Double confirmation for production
if [ "$ENVIRONMENT" = "prod" ]; then
    echo -e "${RED}PRODUCTION ENVIRONMENT DETECTED!${NC}"
    read -p "Type 'destroy-prod' to confirm: " confirmation
    
    if [ "$confirmation" != "destroy-prod" ]; then
        echo -e "${YELLOW}Destroy cancelled.${NC}"
        exit 0
    fi
fi

# Initialize and destroy
cd "$TERRAFORM_DIR/environments/$ENVIRONMENT"

echo -e "${YELLOW}Initializing Terraform...${NC}"
terraform init -reconfigure

echo -e "${YELLOW}Destroying resources...${NC}"
terraform destroy \
    -var-file="terraform.tfvars" \
    -auto-approve

echo -e "${GREEN}Destroy completed for $ENVIRONMENT environment.${NC}"
exit 0