module "parking_management" {
  source = "../../"
  
  # Environment Configuration
  environment = "prod"
  region      = "us-east-1"
  
  # Kubernetes Connection
  kubeconfig_path = "~/.kube/config"
  
  # Database Configuration
  postgresql_config = {
    enabled         = true
    version         = "15"
    storage_size    = "100Gi"
    storage_class   = "premium"
    replicas        = 3
    max_connections = 500
    shared_buffers  = "1GB"
  }
  
  redis_config = {
    enabled       = true
    version       = "7.0"
    storage_size  = "20Gi"
    storage_class = "premium"
    replicas      = 3
    maxmemory     = "4gb"
  }
  
  # Service Configurations
  service_configs = {
    parking-api = {
      replicas         = 5
      min_replicas_hpa = 3
      max_replicas_hpa = 20
      cpu_request      = "1000m"
      memory_request   = "2Gi"
      cpu_limit        = "2000m"
      memory_limit     = "4Gi"
      image_tag        = "prod-${var.release_version}"
      enable_hpa       = true
    }
    user-service = {
      replicas         = 3
      min_replicas_hpa = 3
      max_replicas_hpa = 15
      cpu_request      = "500m"
      memory_request   = "1Gi"
      cpu_limit        = "1000m"
      memory_limit     = "2Gi"
      image_tag        = "prod-${var.release_version}"
      enable_hpa       = true
    }
    payment-service = {
      replicas         = 5
      min_replicas_hpa = 3
      max_replicas_hpa = 25
      cpu_request      = "800m"
      memory_request   = "1.5Gi"
      cpu_limit        = "1600m"
      memory_limit     = "3Gi"
      image_tag        = "prod-${var.release_version}"
      enable_hpa       = true
    }
    notification-service = {
      replicas         = 2
      min_replicas_hpa = 2
      max_replicas_hpa = 10
      cpu_request      = "300m"
      memory_request   = "512Mi"
      cpu_limit        = "600m"
      memory_limit     = "1Gi"
      image_tag        = "prod-${var.release_version}"
      enable_hpa       = true
    }
  }
  
  # Monitoring Configuration
  monitoring_enabled = true
  monitoring_config = {
    prometheus_storage_size   = "200Gi"
    prometheus_retention_days = 60
    grafana_admin_password    = var.grafana_admin_password  # Should be set via environment variable
    grafana_storage_size      = "50Gi"
    alertmanager_enabled      = true
    node_exporter_enabled     = true
  }
  
  # Ingress Configuration
  ingress_enabled = true
  ingress_config = {
    domain              = "parking.example.com"
    tls_enabled         = true
    tls_secret_name     = "parking-tls"
    cert_manager_enabled = true
    ingress_class       = "nginx"
    enable_cors         = true
  }
  
  # Feature Flags
  enable_hpa              = true
  enable_pdb              = true
  enable_network_policies = true
  enable_service_mesh     = true
  resource_limits_enabled = true
  
  # Backup Configuration
  backup_enabled = true
  backup_config = {
    schedule            = "0 1 * * *"
    retention_days      = 90
    storage_location    = "/backups"
    cloud_storage_bucket = "s3://parking-prod-backups"
  }
  
  # Tags
  tags = {
    ManagedBy   = "Terraform"
    Project     = "ParkingManagement"
    Environment = "prod"
    CostCenter  = "platform"
    DataClassification = "confidential"
  }
}

variable "release_version" {
  description = "Release version tag for images"
  type        = string
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
}