module "parking_management" {
  source = "../../"
  
  # Environment Configuration
  environment = "staging"
  region      = "us-east-1"
  
  # Kubernetes Connection
  kubeconfig_path = "~/.kube/config"
  
  # Database Configuration
  postgresql_config = {
    enabled         = true
    version         = "15"
    storage_size    = "20Gi"
    storage_class   = "standard"
    replicas        = 1
    max_connections = 200
    shared_buffers  = "256MB"
  }
  
  redis_config = {
    enabled       = true
    version       = "7.0"
    storage_size  = "10Gi"
    storage_class = "standard"
    replicas      = 1
    maxmemory     = "1gb"
  }
  
  # Service Configurations
  service_configs = {
    parking-api = {
      replicas         = 2
      min_replicas_hpa = 2
      max_replicas_hpa = 8
      cpu_request      = "500m"
      memory_request   = "1Gi"
      cpu_limit        = "1000m"
      memory_limit     = "2Gi"
      image_tag        = "staging-latest"
      enable_hpa       = true
    }
    user-service = {
      replicas         = 2
      min_replicas_hpa = 2
      max_replicas_hpa = 6
      cpu_request      = "300m"
      memory_request   = "512Mi"
      cpu_limit        = "600m"
      memory_limit     = "1Gi"
      image_tag        = "staging-latest"
      enable_hpa       = true
    }
    payment-service = {
      replicas         = 2
      min_replicas_hpa = 2
      max_replicas_hpa = 10
      cpu_request      = "400m"
      memory_request   = "768Mi"
      cpu_limit        = "800m"
      memory_limit     = "1.5Gi"
      image_tag        = "staging-latest"
      enable_hpa       = true
    }
    notification-service = {
      replicas         = 1
      min_replicas_hpa = 1
      max_replicas_hpa = 4
      cpu_request      = "200m"
      memory_request   = "256Mi"
      cpu_limit        = "400m"
      memory_limit     = "512Mi"
      image_tag        = "staging-latest"
      enable_hpa       = true
    }
  }
  
  # Monitoring Configuration
  monitoring_enabled = true
  monitoring_config = {
    prometheus_storage_size   = "50Gi"
    prometheus_retention_days = 15
    grafana_admin_password    = "staging-admin"
    grafana_storage_size      = "10Gi"
    alertmanager_enabled      = true
    node_exporter_enabled     = true
  }
  
  # Ingress Configuration
  ingress_enabled = true
  ingress_config = {
    domain              = "staging.parking.local"
    tls_enabled         = true
    tls_secret_name     = "staging-tls"
    cert_manager_enabled = true
    ingress_class       = "nginx"
    enable_cors         = true
  }
  
  # Feature Flags
  enable_hpa              = true
  enable_pdb              = true
  enable_network_policies = true
  enable_service_mesh     = false
  resource_limits_enabled = true
  
  # Backup Configuration
  backup_enabled = true
  backup_config = {
    schedule            = "0 2 * * *"
    retention_days      = 14
    storage_location    = "/backups"
    cloud_storage_bucket = "s3://parking-staging-backups"
  }
  
  # Tags
  tags = {
    ManagedBy   = "Terraform"
    Project     = "ParkingManagement"
    Environment = "staging"
  }
}