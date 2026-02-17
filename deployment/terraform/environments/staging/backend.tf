# Terraform Backend Configuration for Staging Environment
terraform {
  # Backend type: S3 (AWS) - Recommended for staging/production
  # This provides state locking, versioning, and remote storage
  backend "s3" {
    # S3 Bucket Configuration
    bucket         = "parking-management-terraform-state"
    key            = "staging/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:123456789012:key/terraform-state-key"
    
    # DynamoDB Table for State Locking (prevents concurrent modifications)
    dynamodb_table = "terraform-state-lock"
    
    # Access Control
    acl              = "private"
    
    # Versioning (enabled at bucket level)
    versioning = true
    
    # Server-side encryption
    server_side_encryption_configuration {
      rule {
        apply_server_side_encryption_by_default {
          sse_algorithm = "AES256"
        }
      }
    }
    
    # Lifecycle Rules
    lifecycle_rule {
      enabled = true
      noncurrent_version_expiration {
        days = 90
      }
      abort_incomplete_multipart_upload_days = 7
    }
    
    # Tags for cost tracking
    tags = {
      Name        = "terraform-state-staging"
      Environment = "staging"
      Project     = "parking-management"
      ManagedBy   = "Terraform"
      CostCenter  = "platform-staging"
    }
  }
  
  # Alternative Backend Configurations (commented out)
  
  # Azure Backend Configuration
  # backend "azurerm" {
  #   storage_account_name = "parkingmanagementtfstate"
  #   container_name       = "tfstate"
  #   key                  = "staging/terraform.tfstate"
  #   access_key           = "" # Use environment variable ARM_ACCESS_KEY
  #   
  #   # Features
  #   features {
  #     key_vault {
  #       purge_soft_delete_on_destroy = true
  #       recover_soft_deleted_key_vaults = true
  #     }
  #   }
  # }
  
  # GCS Backend Configuration
  # backend "gcs" {
  #   bucket = "parking-management-terraform-state"
  #   prefix = "staging"
  #   encryption_key = "" # Use environment variable GOOGLE_ENCRYPTION_KEY
  #   
  #   # Retention Policy
  #   retention_policy {
  #     is_locked        = true
  #     retention_period = 7776000 # 90 days in seconds
  #   }
  #   
  #   # Versioning enabled by default on GCS
  #   versioning = true
  # }
  
  # Local Backend (for development only - not recommended for staging)
  # backend "local" {
  #   path = "../../../terraform.tfstate.staging"
  # }
  
  # Required Terraform Version
  required_version = ">= 1.0.0"
  
  # Required Providers with versions
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11.0"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = "~> 1.14.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9.0"
    }
  }
}

# Additional configuration for the backend
# This is not part of the terraform block but provides additional context

# Backend Configuration Notes:
# 1. The S3 bucket must be created before initializing Terraform
# 2. DynamoDB table must have a primary key named "LockID" (string)
# 3. IAM permissions required:
#    - s3:GetObject, s3:PutObject, s3:DeleteObject
#    - s3:ListBucket
#    - dynamodb:GetItem, dynamodb:PutItem, dynamodb:DeleteItem
#    - kms:Decrypt, kms:Encrypt (if using KMS)

# Environment variables that need to be set:
# export AWS_ACCESS_KEY_ID="your-access-key"
# export AWS_SECRET_ACCESS_KEY="your-secret-key"
# export AWS_DEFAULT_REGION="us-east-1"
# export TF_VAR_grafana_admin_password="your-password"

# To initialize with this backend:
# cd environments/staging
# terraform init \
#   -backend-config="bucket=parking-management-terraform-state" \
#   -backend-config="key=staging/terraform.tfstate" \
#   -backend-config="region=us-east-1" \
#   -backend-config="dynamodb_table=terraform-state-lock" \
#   -backend-config="encrypt=true"

# Or simply:
# cd environments/staging
# terraform init

# To migrate from local to remote backend:
# terraform init -migrate-state

# To force-copy state (use with caution):
# terraform init -force-copy

# For CI/CD pipelines, use:
# terraform init \
#   -backend-config="access_key=${AWS_ACCESS_KEY_ID}" \
#   -backend-config="secret_key=${AWS_SECRET_ACCESS_KEY}"

# State Management Commands:
# terraform state list                    # List all resources in state
# terraform state show <resource>         # Show details of a resource
# terraform state mv <source> <destination> # Move resources in state
# terraform state rm <resource>           # Remove resource from state
# terraform state pull > backup.tfstate   # Pull and backup state locally
# terraform state push backup.tfstate     # Push state (use with caution)

# Remote State Data Source (for other configurations to consume)
# This can be used by other Terraform configurations or CI/CD pipelines
data "terraform_remote_state" "staging" {
  backend = "s3"
  config = {
    bucket = "parking-management-terraform-state"
    key    = "staging/terraform.tfstate"
    region = "us-east-1"
  }
}

# Output the remote state location for reference
output "remote_state_info" {
  description = "Information about the remote state location"
  value = {
    backend_type = "s3"
    bucket       = "parking-management-terraform-state"
    key          = "staging/terraform.tfstate"
    region       = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypted    = true
  }
}

# Backend health check - can be used in CI/CD
resource "null_resource" "backend_health_check" {
  provisioner "local-exec" {
    command = <<-EOT
      echo "Checking backend connectivity..."
      aws s3 ls s3://parking-management-terraform-state/staging/ || exit 1
      aws dynamodb describe-table --table-name terraform-state-lock --region us-east-1 || exit 1
      echo "Backend is healthy"
    EOT
    interpreter = ["/bin/bash", "-c"]
  }
  
  triggers = {
    always_run = timestamp()
  }
}

# State versioning information
resource "null_resource" "state_version_info" {
  provisioner "local-exec" {
    command = <<-EOT
      echo "State File Information:"
      echo "Location: s3://parking-management-terraform-state/staging/terraform.tfstate"
      echo "Last Modified: $(aws s3 ls s3://parking-management-terraform-state/staging/terraform.tfstate --region us-east-1 | awk '{print $1" "$2}')"
      echo "Size: $(aws s3 ls s3://parking-management-terraform-state/staging/terraform.tfstate --region us-east-1 | awk '{print $3}') bytes"
      echo "Versions available: $(aws s3api list-object-versions --bucket parking-management-terraform-state --prefix staging/terraform.tfstate --region us-east-1 --query 'Versions | length(@)')"
    EOT
    interpreter = ["/bin/bash", "-c"]
  }
  
  triggers = {
    always_run = timestamp()
  }
}