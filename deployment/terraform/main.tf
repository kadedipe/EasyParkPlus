# Create Kubernetes Namespaces
resource "kubernetes_namespace" "system" {
  metadata {
    name = "${var.namespace_prefix}-system"
    labels = merge(var.tags, {
      name       = "${var.namespace_prefix}-system"
      environment = var.environment
    })
  }
}

resource "kubernetes_namespace" "monitoring" {
  count = var.monitoring_enabled ? 1 : 0
  metadata {
    name = "${var.namespace_prefix}-monitoring"
    labels = merge(var.tags, {
      name       = "${var.namespace_prefix}-monitoring"
      environment = var.environment
    })
  }
}

resource "kubernetes_namespace" "database" {
  metadata {
    name = "${var.namespace_prefix}-database"
    labels = merge(var.tags, {
      name       = "${var.namespace_prefix}-database"
      environment = var.environment
    })
  }
}

# Networking Module
module "networking" {
  source = "./modules/networking"
  
  namespace        = kubernetes_namespace.system.metadata[0].name
  environment      = var.environment
  project_name     = var.project_name
  enable_network_policies = var.enable_network_policies
  enable_service_mesh    = var.enable_service_mesh
  tags             = var.tags
}

# Database Module
module "databases" {
  source = "./modules/databases"
  
  namespace         = kubernetes_namespace.database.metadata[0].name
  environment       = var.environment
  project_name      = var.project_name
  postgresql_config = var.postgresql_config
  redis_config      = var.redis_config
  backup_enabled    = var.backup_enabled
  backup_config     = var.backup_config
  tags              = var.tags
}

# Backend Services Module
module "backend_services" {
  source = "./modules/backend-services"
  
  namespace        = kubernetes_namespace.system.metadata[0].name
  environment      = var.environment
  project_name     = var.project_name
  service_configs  = var.service_configs
  enable_hpa       = var.enable_hpa
  enable_pdb       = var.enable_pdb
  resource_limits_enabled = var.resource_limits_enabled
  postgresql_config = var.postgresql_config
  redis_config      = var.redis_config
  tags             = var.tags
  
  depends_on = [
    module.databases
  ]
}

# Monitoring Module
module "monitoring" {
  count = var.monitoring_enabled ? 1 : 0
  source = "./modules/monitoring"
  
  namespace         = kubernetes_namespace.monitoring[0].metadata[0].name
  environment       = var.environment
  project_name      = var.project_name
  monitoring_config = var.monitoring_config
  tags              = var.tags
  
  depends_on = [
    module.backend_services
  ]
}

# Ingress Module
module "ingress" {
  count = var.ingress_enabled ? 1 : 0
  source = "./modules/ingress"
  
  namespace        = kubernetes_namespace.system.metadata[0].name
  environment      = var.environment
  project_name     = var.project_name
  ingress_config   = var.ingress_config
  service_configs  = var.service_configs
  tags             = var.tags
  
  depends_on = [
    module.backend_services
  ]
}

# Cloud Provider Specific Resources (Optional)
resource "aws_s3_bucket" "backup" {
  count = var.cloud_provider == "aws" && var.backup_enabled ? 1 : 0
  
  bucket = "${var.project_name}-${var.environment}-backups"
  tags   = var.tags
}

resource "azurerm_storage_account" "backup" {
  count = var.cloud_provider == "azure" && var.backup_enabled ? 1 : 0
  
  name                     = "${var.project_name}${var.environment}backup"
  resource_group_name      = "parking-management-${var.environment}"
  location                 = var.azure_region
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = var.tags
}

resource "google_storage_bucket" "backup" {
  count = var.cloud_provider == "gcp" && var.backup_enabled ? 1 : 0
  
  name     = "${var.project_name}-${var.environment}-backups"
  location = var.gcp_region
  labels   = var.tags
}