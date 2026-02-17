# Ingress Controller (NGINX)
resource "kubernetes_namespace" "ingress_nginx" {
  metadata {
    name = "ingress-nginx"
    labels = merge(var.tags, {
      name = "ingress-nginx"
    })
  }
}

resource "helm_release" "ingress_nginx" {
  name       = "ingress-nginx"
  namespace  = kubernetes_namespace.ingress_nginx.metadata[0].name
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  version    = "4.7.0"

  set {
    name  = "controller.service.type"
    value = var.environment == "prod" ? "LoadBalancer" : "NodePort"
  }

  set {
    name  = "controller.service.nodePorts.http"
    value = var.environment != "prod" ? "30080" : ""
  }

  set {
    name  = "controller.service.nodePorts.https"
    value = var.environment != "prod" ? "30443" : ""
  }

  set {
    name  = "controller.metrics.enabled"
    value = "true"
  }

  set {
    name  = "controller.metrics.serviceMonitor.enabled"
    value = "true"
  }

  set {
    name  = "controller.replicaCount"
    value = var.environment == "prod" ? "3" : "1"
  }

  set {
    name  = "controller.resources.requests.cpu"
    value = "100m"
  }

  set {
    name  = "controller.resources.requests.memory"
    value = "256Mi"
  }

  set {
    name  = "controller.resources.limits.cpu"
    value = "500m"
  }

  set {
    name  = "controller.resources.limits.memory"
    value = "1Gi"
  }

  set {
    name  = "controller.autoscaling.enabled"
    value = var.environment == "prod" ? "true" : "false"
  }

  set {
    name  = "controller.autoscaling.minReplicas"
    value = "2"
  }

  set {
    name  = "controller.autoscaling.maxReplicas"
    value = "10"
  }

  set {
    name  = "controller.config.use-forwarded-headers"
    value = "true"
  }

  set {
    name  = "controller.config.enable-cors"
    value = var.ingress_config.enable_cors ? "true" : "false"
  }
}

# Main Ingress Resource
resource "kubernetes_ingress_v1" "main_ingress" {
  count = var.ingress_enabled ? 1 : 0
  
  metadata {
    name      = "parking-ingress"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "ingress"
    })
    annotations = {
      "kubernetes.io/ingress.class"              = var.ingress_config.ingress_class
      "nginx.ingress.kubernetes.io/rewrite-target" = "/"
      "nginx.ingress.kubernetes.io/ssl-redirect"   = var.ingress_config.tls_enabled ? "true" : "false"
      "nginx.ingress.kubernetes.io/proxy-body-size" = "10m"
      "nginx.ingress.kubernetes.io/proxy-connect-timeout" = "30"
      "nginx.ingress.kubernetes.io/proxy-read-timeout" = "60"
      "nginx.ingress.kubernetes.io/proxy-send-timeout" = "60"
      "nginx.ingress.kubernetes.io/enable-cors" = var.ingress_config.enable_cors ? "true" : "false"
      "nginx.ingress.kubernetes.io/cors-allow-methods" = "GET, POST, PUT, DELETE, OPTIONS"
      "nginx.ingress.kubernetes.io/cors-allow-headers" = "DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Authorization"
      "nginx.ingress.kubernetes.io/cors-allow-origin" = "*"
      "nginx.ingress.kubernetes.io/configuration-snippet" = <<-EOT
        more_set_headers "X-Frame-Options: DENY";
        more_set_headers "X-Content-Type-Options: nosniff";
        more_set_headers "X-XSS-Protection: 1; mode=block";
      EOT
    }
  }

  spec {
    rule {
      host = var.ingress_config.domain
      http {
        path {
          path     = "/api"
          path_type = "Prefix"
          backend {
            service {
              name = "parking-api"
              port {
                number = 80
              }
            }
          }
        }
        path {
          path     = "/auth"
          path_type = "Prefix"
          backend {
            service {
              name = "user-service"
              port {
                number = 80
              }
            }
          }
        }
        path {
          path     = "/payments"
          path_type = "Prefix"
          backend {
            service {
              name = "payment-service"
              port {
                number = 80
              }
            }
          }
        }
        path {
          path     = "/notifications"
          path_type = "Prefix"
          backend {
            service {
              name = "notification-service"
              port {
                number = 80
              }
            }
          }
        }
      }
    }

    dynamic "tls" {
      for_each = var.ingress_config.tls_enabled ? [1] : []
      content {
        hosts       = [var.ingress_config.domain]
        secret_name = var.ingress_config.tls_secret_name != "" ? var.ingress_config.tls_secret_name : "parking-tls"
      }
    }
  }
}

# API Gateway Ingress (for more specific routing)
resource "kubernetes_ingress_v1" "api_gateway" {
  count = var.ingress_enabled ? 1 : 0
  
  metadata {
    name      = "api-gateway"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "ingress"
      type      = "api"
    })
    annotations = {
      "kubernetes.io/ingress.class" = var.ingress_config.ingress_class
      "nginx.ingress.kubernetes.io/rewrite-target" = "/$2"
      "nginx.ingress.kubernetes.io/use-regex" = "true"
    }
  }

  spec {
    rule {
      host = "api.${var.ingress_config.domain}"
      http {
        path {
          path     = "/parking(/|$)(.*)"
          path_type = "ImplementationSpecific"
          backend {
            service {
              name = "parking-api"
              port {
                number = 80
              }
            }
          }
        }
        path {
          path     = "/users(/|$)(.*)"
          path_type = "ImplementationSpecific"
          backend {
            service {
              name = "user-service"
              port {
                number = 80
              }
            }
          }
        }
        path {
          path     = "/payments(/|$)(.*)"
          path_type = "ImplementationSpecific"
          backend {
            service {
              name = "payment-service"
              port {
                number = 80
              }
            }
          }
        }
      }
    }
  }
}

# Grafana Ingress (if monitoring enabled)
resource "kubernetes_ingress_v1" "grafana_ingress" {
  count = var.monitoring_enabled ? 1 : 0
  
  metadata {
    name      = "grafana-ingress"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "ingress"
      app       = "grafana"
    })
    annotations = {
      "kubernetes.io/ingress.class" = var.ingress_config.ingress_class
      "nginx.ingress.kubernetes.io/rewrite-target" = "/"
    }
  }

  spec {
    rule {
      host = "grafana.${var.ingress_config.domain}"
      http {
        path {
          path     = "/"
          path_type = "Prefix"
          backend {
            service {
              name = "grafana"
              port {
                number = 80
              }
            }
          }
        }
      }
    }
  }
}

# Prometheus Ingress (if monitoring enabled)
resource "kubernetes_ingress_v1" "prometheus_ingress" {
  count = var.monitoring_enabled ? 1 : 0
  
  metadata {
    name      = "prometheus-ingress"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "ingress"
      app       = "prometheus"
    })
    annotations = {
      "kubernetes.io/ingress.class" = var.ingress_config.ingress_class
      "nginx.ingress.kubernetes.io/rewrite-target" = "/"
      "nginx.ingress.kubernetes.io/auth-type" = "basic"
      "nginx.ingress.kubernetes.io/auth-secret" = "prometheus-auth"
    }
  }

  spec {
    rule {
      host = "prometheus.${var.ingress_config.domain}"
      http {
        path {
          path     = "/"
          path_type = "Prefix"
          backend {
            service {
              name = "prometheus"
              port {
                number = 9090
              }
            }
          }
        }
      }
    }
  }
}

# Basic Auth Secret for Prometheus
resource "kubernetes_secret" "prometheus_auth" {
  count = var.monitoring_enabled ? 1 : 0
  
  metadata {
    name      = "prometheus-auth"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "ingress"
      app       = "prometheus"
    })
  }

  data = {
    "auth" = "prometheus:${bcrypt(random_password.prometheus_password[0].result)}"
  }

  type = "kubernetes.io/basic-auth"
}

resource "random_password" "prometheus_password" {
  count = var.monitoring_enabled ? 1 : 0
  
  length  = 16
  special = false
}

# Cert Manager for TLS certificates
resource "helm_release" "cert_manager" {
  count = var.ingress_config.cert_manager_enabled ? 1 : 0
  
  name       = "cert-manager"
  namespace  = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  version    = "v1.12.0"

  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "prometheus.enabled"
    value = "true"
  }

  set {
    name  = "prometheus.servicemonitor.enabled"
    value = "true"
  }
}

resource "kubernetes_manifest" "cluster_issuer" {
  count = var.ingress_config.cert_manager_enabled && var.ingress_config.tls_enabled ? 1 : 0
  
  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "ClusterIssuer"
    metadata = {
      name = "letsencrypt-${var.environment}"
    }
    spec = {
      acme = {
        server = var.environment == "prod" ? "https://acme-v02.api.letsencrypt.org/directory" : "https://acme-staging-v02.api.letsencrypt.org/directory"
        email = "admin@${var.ingress_config.domain}"
        privateKeySecretRef = {
          name = "letsencrypt-${var.environment}"
        }
        solvers = [
          {
            http01 = {
              ingress = {
                class = var.ingress_config.ingress_class
              }
            }
          }
        ]
      }
    }
  }
}