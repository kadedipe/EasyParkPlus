output "endpoints" {
  description = "Monitoring endpoints"
  value = {
    prometheus = {
      service   = kubernetes_service.prometheus.metadata[0].name
      port      = 9090
      url       = "http://prometheus:9090"
      namespace = var.namespace
    }
    grafana = {
      service   = kubernetes_service.grafana.metadata[0].name
      port      = 80
      url       = "http://grafana:80"
      namespace = var.namespace
      admin_user = "admin"
      admin_password = var.monitoring_config.grafana_admin_password != "" ? var.monitoring_config.grafana_admin_password : random_password.grafana_password.result
    }
    node_exporter = var.monitoring_config.node_exporter_enabled ? {
      service   = kubernetes_service.node_exporter[0].metadata[0].name
      port      = 9100
      namespace = var.namespace
    } : null
    alertmanager = var.monitoring_config.alertmanager_enabled ? {
      service   = kubernetes_service.alertmanager[0].metadata[0].name
      port      = 9093
      namespace = var.namespace
    } : null
  }
}

output "grafana_credentials" {
  description = "Grafana admin credentials"
  value = {
    username = "admin"
    password = var.monitoring_config.grafana_admin_password != "" ? var.monitoring_config.grafana_admin_password : random_password.grafana_password.result
  }
  sensitive = true
}

output "prometheus_config" {
  description = "Prometheus configuration"
  value = {
    config_map = kubernetes_config_map.prometheus_config.metadata[0].name
    rules_map  = kubernetes_config_map.prometheus_rules.metadata[0].name
    retention  = var.monitoring_config.prometheus_retention_days
    storage    = var.monitoring_config.prometheus_storage_size
  }
}