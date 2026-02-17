module "parking_management" {
  source = "../../"
  
  # Environment Configuration
  environment = "dev"
  region      = "us-east-1"
  
  # Kubernetes Connection
  kubeconfig_path = "~/.kube/config"
  
  # Database Configuration
  postgresql_config = {
    enabled         = true
    version         = "15"
    storage_size    = "10Gi"
    storage_class   = "standard"
    replicas        = 1
    max_connections = 100
    shared_buffers  = "128MB"
  }
  
  redis_config = {
    enabled       = true
    version       = "7.0"
    storage_size  = "5Gi"
    storage_class = "standard"
    replicas      = 1
    maxmemory     = "512mb"
  }
  
  # Service Configurations
  service_configs = {
    parking-api = {
      replicas         = 1
      min_replicas_hpa = 1
      max_replicas_hpa = 5
      cpu_request      = "250m"
      memory_request   = "512Mi"
      cpu_limit        = "500m"
      memory_limit     = "1Gi"
      image_tag        = "dev-latest"
      enable_hpa       = true
    }
    user-service = {
      replicas         = 1
      min_replicas_hpa = 1
      max_replicas_hpa = 3
      cpu_request      = "150m"
      memory_request   = "256Mi"
      cpu_limit        = "300m"
      memory_limit     = "512Mi"
      image_tag        = "dev-latest"
      enable_hpa       = true
    }
    payment-service = {
      replicas         = 1
      min_replicas_hpa = 1
      max_replicas_hpa = 5
      cpu_request      = "200m"
      memory_request   = "384Mi"
      cpu_limit        = "400m"
      memory_limit     = "768Mi"
      image_tag        = "dev-latest"
      enable_hpa       = true
    }
    notification-service = {
      replicas         = 1
      min_replicas_hpa = 1
      max_replicas_hpa = 3
      cpu_request      = "100m"
      memory_request   = "128Mi"
      cpu_limit        = "200m"
      memory_limit     = "256Mi"
      image_tag        = "dev-latest"
      enable_hpa       = true
    }
  }
  
  # Monitoring Configuration (reduced for dev)
  monitoring_enabled = true
  monitoring_config = {
    prometheus_storage_size   = "20Gi"
    prometheus_retention_days = 7
    grafana_admin_password    = "admin123"
    grafana_storage_size      = "5Gi"
    alertmanager_enabled      = false
    node_exporter_enabled     = true
  }
  
  # Ingress Configuration
  ingress_enabled = true
  ingress_config = {
    domain              = "dev.parking.local"
    tls_enabled         = false
    tls_secret_name     = ""
    cert_manager_enabled = false
    ingress_class       = "nginx"
    enable_cors         = true
  }
  
  # Feature Flags
  enable_hpa              = true
  enable_pdb              = false
  enable_network_policies = false
  enable_service_mesh     = false
  resource_limits_enabled = true
  
  # Backup Configuration
  backup_enabled = false
  
  # Tags
  tags = {
    ManagedBy   = "Terraform"
    Project     = "ParkingManagement"
    Environment = "dev"
  }
}