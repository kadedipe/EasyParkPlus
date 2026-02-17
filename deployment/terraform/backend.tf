# This file is typically overridden in environment-specific directories
# It's kept here as a template

terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
  
  # Example for S3 backend (AWS)
  # backend "s3" {
  #   bucket = "parking-management-terraform-state"
  #   key    = "parking-management/terraform.tfstate"
  #   region = "us-east-1"
  #   encrypt = true
  # }
  
  # Example for Azure backend
  # backend "azurerm" {
  #   storage_account_name = "parkingmanagementtfstate"
  #   container_name       = "tfstate"
  #   key                  = "terraform.tfstate"
  # }
  
  # Example for GCS backend (GCP)
  # backend "gcs" {
  #   bucket = "parking-management-terraform-state"
  #   prefix = "terraform/state"
  # }
}