output "ingress_info" {
  description = "Ingress information"
  value = {
    main_ingress = var.ingress_enabled ? {
      name      = kubernetes_ingress_v1.main_ingress[0].metadata[0].name
      host      = var.ingress_config.domain
      addresses = kubernetes_ingress_v1.main_ingress[0].status[0].load_balancer[0].ingress
    } : null
    
    api_gateway = var.ingress_enabled ? {
      name      = kubernetes_ingress_v1.api_gateway[0].metadata[0].name
      host      = "api.${var.ingress_config.domain}"
    } : null
    
    grafana = var.monitoring_enabled ? {
      name      = kubernetes_ingress_v1.grafana_ingress[0].metadata[0].name
      host      = "grafana.${var.ingress_config.domain}"
    } : null
    
    prometheus = var.monitoring_enabled ? {
      name      = kubernetes_ingress_v1.prometheus_ingress[0].metadata[0].name
      host      = "prometheus.${var.ingress_config.domain}"
      username  = "prometheus"
      password  = var.monitoring_enabled ? random_password.prometheus_password[0].result : null
    } : null
  }
}

output "ingress_controller" {
  description = "Ingress controller information"
  value = {
    namespace = "ingress-nginx"
    service   = "ingress-nginx-controller"
    type      = var.environment == "prod" ? "LoadBalancer" : "NodePort"
    ports = {
      http  = var.environment != "prod" ? 30080 : 80
      https = var.environment != "prod" ? 30443 : 443
    }
  }
}

output "tls_info" {
  description = "TLS certificate information"
  value = var.ingress_config.tls_enabled ? {
    enabled      = true
    secret_name  = var.ingress_config.tls_secret_name != "" ? var.ingress_config.tls_secret_name : "parking-tls"
    cert_manager = var.ingress_config.cert_manager_enabled
  } : {
    enabled = false
  }
}