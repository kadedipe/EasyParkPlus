# Namespace Outputs
output "namespaces" {
  description = "Created Kubernetes namespaces"
  value = {
    system     = kubernetes_namespace.system.metadata[0].name
    monitoring = var.monitoring_enabled ? kubernetes_namespace.monitoring[0].metadata[0].name : null
    database   = kubernetes_namespace.database.metadata[0].name
  }
}

# Service Endpoints
output "service_endpoints" {
  description = "Service endpoints"
  value = module.backend_services.service_endpoints
}

# Database Connection Information
output "database_connections" {
  description = "Database connection information"
  value = module.databases.connection_info
  sensitive = true
}

# Monitoring Endpoints
output "monitoring_endpoints" {
  description = "Monitoring endpoints"
  value = var.monitoring_enabled ? module.monitoring[0].endpoints : null
}

# Ingress Information
output "ingress_info" {
  description = "Ingress information"
  value = var.ingress_enabled ? module.ingress[0].ingress_info : null
}

# Kubernetes Configuration
output "kubernetes_config" {
  description = "Kubernetes configuration summary"
  value = {
    environment = var.environment
    region      = var.region
    cloud_provider = var.cloud_provider
  }
}

# Service Status
output "service_status" {
  description = "Deployment status of services"
  value = {
    total_services = length(var.service_configs)
    hpa_enabled    = var.enable_hpa
    monitoring     = var.monitoring_enabled
    ingress        = var.ingress_enabled
  }
}

# Backup Information
output "backup_info" {
  description = "Backup configuration information"
  value = var.backup_enabled ? {
    schedule       = var.backup_config.schedule
    retention_days = var.backup_config.retention_days
    location       = var.backup_config.storage_location
  } : null
}

# Connection Commands
output "connection_commands" {
  description = "Useful connection commands"
  value = {
    port_forward_api = "kubectl port-forward -n ${kubernetes_namespace.system.metadata[0].name} svc/parking-api 8080:80"
    port_forward_grafana = var.monitoring_enabled ? "kubectl port-forward -n ${kubernetes_namespace.monitoring[0].metadata[0].name} svc/grafana 3000:80" : null
    get_all_pods = "kubectl get pods --all-namespaces -l part-of=parking-management-system"
  }
}