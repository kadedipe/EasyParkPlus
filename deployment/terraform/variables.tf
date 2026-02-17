# Kubernetes Connection Variables
variable "kubeconfig_path" {
  description = "Path to kubeconfig file"
  type        = string
  default     = ""
}

variable "kubernetes_host" {
  description = "Kubernetes API server host"
  type        = string
  default     = ""
}

variable "kubernetes_cluster_ca_certificate" {
  description = "Kubernetes cluster CA certificate"
  type        = string
  default     = ""
  sensitive   = true
}

variable "kubernetes_client_certificate" {
  description = "Kubernetes client certificate"
  type        = string
  default     = ""
  sensitive   = true
}

variable "kubernetes_client_key" {
  description = "Kubernetes client key"
  type        = string
  default     = ""
  sensitive   = true
}

# Environment Variables
variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "region" {
  description = "Deployment region"
  type        = string
  default     = "us-east-1"
}

# Application Configuration
variable "project_name" {
  description = "Project name"
  type        = string
  default     = "parking-management"
}

variable "namespace_prefix" {
  description = "Prefix for Kubernetes namespaces"
  type        = string
  default     = "parking"
}

variable "resource_limits_enabled" {
  description = "Enable resource limits for pods"
  type        = bool
  default     = true
}

# Database Variables
variable "postgresql_config" {
  description = "PostgreSQL configuration"
  type = object({
    enabled          = bool
    version          = string
    storage_size     = string
    storage_class    = string
    replicas         = number
    max_connections  = number
    shared_buffers   = string
  })
  default = {
    enabled         = true
    version         = "15"
    storage_size    = "10Gi"
    storage_class   = "standard"
    replicas        = 1
    max_connections = 200
    shared_buffers  = "256MB"
  }
}

variable "redis_config" {
  description = "Redis configuration"
  type = object({
    enabled       = bool
    version       = string
    storage_size  = string
    storage_class = string
    replicas      = number
    maxmemory     = string
  })
  default = {
    enabled       = true
    version       = "7.0"
    storage_size  = "5Gi"
    storage_class = "standard"
    replicas      = 1
    maxmemory     = "1gb"
  }
}

# Service Configuration
variable "service_configs" {
  description = "Configuration for microservices"
  type = map(object({
    replicas          = number
    min_replicas_hpa  = number
    max_replicas_hpa  = number
    cpu_request       = string
    memory_request    = string
    cpu_limit         = string
    memory_limit      = string
    image_tag         = string
    enable_hpa        = bool
  }))
  default = {
    parking-api = {
      replicas         = 2
      min_replicas_hpa = 2
      max_replicas_hpa = 10
      cpu_request      = "500m"
      memory_request   = "1Gi"
      cpu_limit        = "1000m"
      memory_limit     = "2Gi"
      image_tag        = "latest"
      enable_hpa       = true
    }
    user-service = {
      replicas         = 2
      min_replicas_hpa = 2
      max_replicas_hpa = 8
      cpu_request      = "300m"
      memory_request   = "512Mi"
      cpu_limit        = "600m"
      memory_limit     = "1Gi"
      image_tag        = "latest"
      enable_hpa       = true
    }
    payment-service = {
      replicas         = 3
      min_replicas_hpa = 3
      max_replicas_hpa = 15
      cpu_request      = "400m"
      memory_request   = "768Mi"
      cpu_limit        = "800m"
      memory_limit     = "1.5Gi"
      image_tag        = "latest"
      enable_hpa       = true
    }
    notification-service = {
      replicas         = 1
      min_replicas_hpa = 1
      max_replicas_hpa = 5
      cpu_request      = "200m"
      memory_request   = "256Mi"
      cpu_limit        = "400m"
      memory_limit     = "512Mi"
      image_tag        = "latest"
      enable_hpa       = true
    }
  }
}

# Monitoring Configuration
variable "monitoring_enabled" {
  description = "Enable monitoring stack"
  type        = bool
  default     = true
}

variable "monitoring_config" {
  description = "Monitoring stack configuration"
  type = object({
    prometheus_storage_size   = string
    prometheus_retention_days = number
    grafana_admin_password    = string
    grafana_storage_size      = string
    alertmanager_enabled      = bool
    node_exporter_enabled     = bool
  })
  default = {
    prometheus_storage_size   = "50Gi"
    prometheus_retention_days = 30
    grafana_admin_password    = "admin"
    grafana_storage_size      = "10Gi"
    alertmanager_enabled      = true
    node_exporter_enabled     = true
  }
  sensitive = {
    grafana_admin_password = true
  }
}

# Ingress Configuration
variable "ingress_enabled" {
  description = "Enable ingress"
  type        = bool
  default     = true
}

variable "ingress_config" {
  description = "Ingress configuration"
  type = object({
    domain              = string
    tls_enabled         = bool
    tls_secret_name     = string
    cert_manager_enabled = bool
    ingress_class       = string
    enable_cors         = bool
  })
  default = {
    domain               = "parking.local"
    tls_enabled          = false
    tls_secret_name      = ""
    cert_manager_enabled = false
    ingress_class        = "nginx"
    enable_cors          = true
  }
}

# Cloud Provider Variables (optional)
variable "cloud_provider" {
  description = "Cloud provider (aws, azure, gcp, or none)"
  type        = string
  default     = "none"
  validation {
    condition     = contains(["aws", "azure", "gcp", "none"], var.cloud_provider)
    error_message = "Cloud provider must be aws, azure, gcp, or none."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS profile"
  type        = string
  default     = "default"
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = ""
}

variable "azure_tenant_id" {
  description = "Azure tenant ID"
  type        = string
  default     = ""
}

variable "gcp_project" {
  description = "GCP project ID"
  type        = string
  default     = ""
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

# Feature Flags
variable "enable_hpa" {
  description = "Enable Horizontal Pod Autoscaling"
  type        = bool
  default     = true
}

variable "enable_pdb" {
  description = "Enable Pod Disruption Budgets"
  type        = bool
  default     = true
}

variable "enable_network_policies" {
  description = "Enable Network Policies"
  type        = bool
  default     = true
}

variable "enable_service_mesh" {
  description = "Enable Service Mesh (Istio/Linkerd)"
  type        = bool
  default     = false
}

# Backup Configuration
variable "backup_enabled" {
  description = "Enable backups"
  type        = bool
  default     = false
}

variable "backup_config" {
  description = "Backup configuration"
  type = object({
    schedule           = string
    retention_days     = number
    storage_location   = string
    cloud_storage_bucket = string
  })
  default = {
    schedule           = "0 2 * * *"
    retention_days     = 30
    storage_location   = "/backups"
    cloud_storage_bucket = ""
  }
}

# Tags and Labels
variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    ManagedBy   = "Terraform"
    Project     = "ParkingManagement"
    Environment = "dev"
  }
}