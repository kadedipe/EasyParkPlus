# Service Accounts
resource "kubernetes_service_account" "service_accounts" {
  for_each = var.service_configs
  
  metadata {
    name      = "${each.key}-sa"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = each.key
      component = "backend"
    })
  }
}

# ConfigMaps for services
resource "kubernetes_config_map" "service_configs" {
  for_each = var.service_configs
  
  metadata {
    name      = "${each.key}-config"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = each.key
      component = "backend"
    })
  }

  data = {
    "config.yaml" = yamlencode({
      service = each.key
      environment = var.environment
      database = {
        host = "postgresql.${var.namespace}.svc.cluster.local"
        port = 5432
        name = "parkingdb"
      }
      redis = {
        host = "redis.${var.namespace}.svc.cluster.local"
        port = 6379
      }
      logging = {
        level = var.environment == "prod" ? "info" : "debug"
        format = "json"
      }
      metrics = {
        enabled = true
        port    = 8080
      }
    })
  }
}

# Secrets for services
resource "kubernetes_secret" "service_secrets" {
  for_each = var.service_configs
  
  metadata {
    name      = "${each.key}-secrets"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = each.key
      component = "backend"
    })
  }

  data = {
    "database_url" = "postgresql://parking_user:${var.postgresql_config.enabled ? random_password.postgresql_password[0].result : ""}@postgresql.${var.namespace}.svc.cluster.local:5432/parkingdb?sslmode=disable"
    "redis_url"    = "redis://redis.${var.namespace}.svc.cluster.local:6379"
    "jwt_secret"   = random_password.jwt_secret.result
    "api_key"      = random_password.api_keys[each.key].result
  }

  type = "Opaque"
}

# Deployments
resource "kubernetes_deployment" "services" {
  for_each = var.service_configs
  
  metadata {
    name      = each.key
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = each.key
      component = "backend"
      version   = each.value.image_tag
    })
  }

  spec {
    replicas = each.value.replicas
    
    selector {
      match_labels = {
        app = each.key
      }
    }

    strategy {
      type = "RollingUpdate"
      rolling_update {
        max_surge       = "25%"
        max_unavailable = "0"
      }
    }

    template {
      metadata {
        labels = {
          app       = each.key
          component = "backend"
          version   = each.value.image_tag
        }
        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "8080"
          "prometheus.io/path"   = "/metrics"
          "config.hash"          = sha256(kubernetes_config_map.service_configs[each.key].data["config.yaml"])
          "secret.hash"          = sha256(kubernetes_secret.service_secrets[each.key].data["database_url"])
        }
      }

      spec {
        service_account_name = kubernetes_service_account.service_accounts[each.key].metadata[0].name
        
        container {
          name              = each.key
          image             = "${var.image_registry}/${each.key}:${each.value.image_tag}"
          image_pull_policy = var.environment == "prod" ? "IfNotPresent" : "Always"
          
          port {
            container_port = 8080
            name           = "http"
          }
          
          port {
            container_port = 8081
            name           = "metrics"
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.service_configs[each.key].metadata[0].name
            }
          }

          env_from {
            secret_ref {
              name = kubernetes_secret.service_secrets[each.key].metadata[0].name
            }
          }

          env {
            name = "POD_NAME"
            value_from {
              field_ref {
                field_path = "metadata.name"
              }
            }
          }

          env {
            name = "POD_NAMESPACE"
            value_from {
              field_ref {
                field_path = "metadata.namespace"
              }
            }
          }

          env {
            name = "NODE_NAME"
            value_from {
              field_ref {
                field_path = "spec.nodeName"
              }
            }
          }

          resources {
            requests = {
              cpu    = each.value.cpu_request
              memory = each.value.memory_request
            }
            limits = var.resource_limits_enabled ? {
              cpu    = each.value.cpu_limit
              memory = each.value.memory_limit
            } : null
          }

          liveness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            initial_delay_seconds = 60
            period_seconds        = 10
            timeout_seconds       = 5
            failure_threshold     = 3
          }

          readiness_probe {
            http_get {
              path = "/ready"
              port = 8080
            }
            initial_delay_seconds = 30
            period_seconds        = 5
            timeout_seconds       = 3
            failure_threshold     = 2
          }

          volume_mount {
            name       = "tmp"
            mount_path = "/tmp"
          }

          volume_mount {
            name       = "logs"
            mount_path = "/var/log"
          }

          security_context {
            run_as_non_root = true
            run_as_user     = 1000
            run_as_group    = 1000
            read_only_root_filesystem = true
            capabilities {
              drop = ["ALL"]
            }
          }
        }

        volume {
          name = "tmp"
          empty_dir {}
        }

        volume {
          name = "logs"
          empty_dir {}
        }

        security_context {
          fs_group = 1000
        }

        node_selector = {
          "workload-type" = "application"
        }

        termination_grace_period_seconds = 60
      }
    }
  }
}

# Services
resource "kubernetes_service" "services" {
  for_each = var.service_configs
  
  metadata {
    name      = each.key
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = each.key
      component = "backend"
    })
    annotations = {
      "service.kubernetes.io/description" = "${each.key} service"
    }
  }

  spec {
    selector = {
      app = each.key
    }
    
    port {
      name        = "http"
      port        = 80
      target_port = 8080
    }

    port {
      name        = "metrics"
      port        = 8081
      target_port = 8081
    }

    type = "ClusterIP"
  }
}

# Horizontal Pod Autoscalers
resource "kubernetes_horizontal_pod_autoscaler_v2" "hpas" {
  for_each = var.enable_hpa ? { for k, v in var.service_configs : k => v if v.enable_hpa } : {}
  
  metadata {
    name      = "${each.key}-hpa"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = each.key
      component = "backend"
      hpa-type  = "resource-based"
    })
  }

  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = each.key
    }

    min_replicas = each.value.min_replicas_hpa
    max_replicas = each.value.max_replicas_hpa

    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 70
        }
      }
    }

    metric {
      type = "Resource"
      resource {
        name = "memory"
        target {
          type                = "Utilization"
          average_utilization = 80
        }
      }
    }

    behavior {
      scale_up {
        stabilization_window_seconds = 60
        policy {
          type           = "Pods"
          value          = 2
          period_seconds = 60
        }
        policy {
          type           = "Percent"
          value          = 50
          period_seconds = 60
        }
        select_policy = "Max"
      }

      scale_down {
        stabilization_window_seconds = 300
        policy {
          type           = "Pods"
          value          = 1
          period_seconds = 120
        }
        policy {
          type           = "Percent"
          value          = 10
          period_seconds = 120
        }
        select_policy = "Min"
      }
    }
  }
}

# Pod Disruption Budgets
resource "kubernetes_pod_disruption_budget_v1" "pdbs" {
  for_each = var.enable_pdb ? var.service_configs : {}
  
  metadata {
    name      = "${each.key}-pdb"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = each.key
      component = "backend"
    })
  }

  spec {
    min_available = each.key == "payment-service" ? 2 : 1
    
    selector {
      match_labels = {
        app = each.key
      }
    }
  }
}

# Random resources
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "api_keys" {
  for_each = var.service_configs
  
  length  = 32
  special = false
}