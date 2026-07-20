# parking-management/terraform/variables.tf
variable "aws_region" {
  description = "AWS region"
  type = string
  default = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type = string
  default = "production"
}

variable "domain_name" {
  description = "Domain name"
  type = string
  default = "yourdomain.com"
}

variable "zone_id" {
  description = "Route53 zone ID"
  type = string
}

variable "ecr_repository_name" {
  description = "ECR repository name"
  type = string
  default = "parking-frontend"
}