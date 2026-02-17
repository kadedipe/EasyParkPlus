# PostgreSQL StatefulSet
resource "kubernetes_stateful_set" "postgresql" {
  count = var.postgresql_config.enabled ? 1 : 0
  
  metadata {
    name      = "postgresql"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "postgresql"
      component = "database"
      version   = var.postgresql_config.version
    })
  }

  spec {
    replicas               = var.postgresql_config.replicas
    service_name          = "postgresql"
    pod_management_policy = "OrderedReady"
    
    selector {
      match_labels = {
        app = "postgresql"
      }
    }

    template {
      metadata {
        labels = {
          app       = "postgresql"
          component = "database"
        }
        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "9187"
        }
      }

      spec {
        container {
          name  = "postgresql"
          image = "postgres:${var.postgresql_config.version}"
          
          port {
            container_port = 5432
            name           = "postgresql"
          }

          env {
            name = "POSTGRES_DB"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgresql_secret[0].metadata[0].name
                key  = "database"
              }
            }
          }

          env {
            name = "POSTGRES_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgresql_secret[0].metadata[0].name
                key  = "username"
              }
            }
          }

          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgresql_secret[0].metadata[0].name
                key  = "password"
              }
            }
          }

          resources {
            requests = {
              cpu    = "500m"
              memory = "1Gi"
            }
            limits = {
              cpu    = "1000m"
              memory = "2Gi"
            }
          }

          volume_mount {
            name       = "postgresql-data"
            mount_path = "/var/lib/postgresql/data"
            sub_path   = "postgresql"
          }

          liveness_probe {
            exec {
              command = ["pg_isready", "-U", "postgres"]
            }
            initial_delay_seconds = 60
            period_seconds        = 10
            timeout_seconds       = 5
          }

          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "postgres"]
            }
            initial_delay_seconds = 30
            period_seconds        = 5
            timeout_seconds       = 3
          }
        }

        container {
          name  = "postgres-exporter"
          image = "prometheuscommunity/postgres-exporter:latest"
          
          port {
            container_port = 9187
            name           = "metrics"
          }

          env {
            name = "DATA_SOURCE_NAME"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgresql_secret[0].metadata[0].name
                key  = "dsn"
              }
            }
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "128Mi"
            }
            limits = {
              cpu    = "200m"
              memory = "256Mi"
            }
          }
        }

        security_context {
          fs_group = 999
        }
      }
    }

    volume_claim_template {
      metadata {
        name = "postgresql-data"
      }
      spec {
        access_modes = ["ReadWriteOnce"]
        resources {
          requests = {
            storage = var.postgresql_config.storage_size
          }
        }
        storage_class_name = var.postgresql_config.storage_class
      }
    }

    service_name = "postgresql"
    update_strategy {
      type = "RollingUpdate"
    }
  }
}

# PostgreSQL Service
resource "kubernetes_service" "postgresql" {
  count = var.postgresql_config.enabled ? 1 : 0
  
  metadata {
    name      = "postgresql"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "postgresql"
      component = "database"
    })
  }

  spec {
    selector = {
      app = "postgresql"
    }
    
    port {
      name        = "postgresql"
      port        = 5432
      target_port = 5432
    }

    port {
      name        = "metrics"
      port        = 9187
      target_port = 9187
    }

    type = "ClusterIP"
  }
}

# PostgreSQL Secret
resource "kubernetes_secret" "postgresql_secret" {
  count = var.postgresql_config.enabled ? 1 : 0
  
  metadata {
    name      = "postgresql-secret"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "postgresql"
      component = "database"
    })
  }

  data = {
    database = var.postgresql_config.enabled ? "parkingdb" : ""
    username = var.postgresql_config.enabled ? "parking_user" : ""
    password = random_password.postgresql_password[0].result
    dsn      = var.postgresql_config.enabled ? "postgresql://parking_user:${random_password.postgresql_password[0].result}@postgresql:5432/parkingdb?sslmode=disable" : ""
  }

  type = "Opaque"
}

# Redis StatefulSet
resource "kubernetes_stateful_set" "redis" {
  count = var.redis_config.enabled ? 1 : 0
  
  metadata {
    name      = "redis"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "redis"
      component = "database"
      version   = var.redis_config.version
    })
  }

  spec {
    replicas               = var.redis_config.replicas
    service_name          = "redis"
    pod_management_policy = "OrderedReady"
    
    selector {
      match_labels = {
        app = "redis"
      }
    }

    template {
      metadata {
        labels = {
          app       = "redis"
          component = "database"
        }
        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "9121"
        }
      }

      spec {
        container {
          name  = "redis"
          image = "redis:${var.redis_config.version}-alpine"
          
          command = [
            "redis-server",
            "--appendonly", "yes",
            "--maxmemory", var.redis_config.maxmemory,
            "--maxmemory-policy", "allkeys-lru"
          ]

          port {
            container_port = 6379
            name           = "redis"
          }

          resources {
            requests = {
              cpu    = "200m"
              memory = "512Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "1Gi"
            }
          }

          volume_mount {
            name       = "redis-data"
            mount_path = "/data"
          }

          liveness_probe {
            exec {
              command = ["redis-cli", "ping"]
            }
            initial_delay_seconds = 30
            period_seconds        = 10
            timeout_seconds       = 5
          }

          readiness_probe {
            exec {
              command = ["redis-cli", "ping"]
            }
            initial_delay_seconds = 15
            period_seconds        = 5
            timeout_seconds       = 3
          }
        }

        container {
          name  = "redis-exporter"
          image = "oliver006/redis_exporter:latest"
          
          port {
            container_port = 9121
            name           = "metrics"
          }

          env {
            name = "REDIS_ADDR"
            value = "redis://localhost:6379"
          }

          resources {
            requests = {
              cpu    = "50m"
              memory = "64Mi"
            }
            limits = {
              cpu    = "100m"
              memory = "128Mi"
            }
          }
        }
      }
    }

    volume_claim_template {
      metadata {
        name = "redis-data"
      }
      spec {
        access_modes = ["ReadWriteOnce"]
        resources {
          requests = {
            storage = var.redis_config.storage_size
          }
        }
        storage_class_name = var.redis_config.storage_class
      }
    }

    service_name = "redis"
  }
}

# Redis Service
resource "kubernetes_service" "redis" {
  count = var.redis_config.enabled ? 1 : 0
  
  metadata {
    name      = "redis"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "redis"
      component = "database"
    })
  }

  spec {
    selector = {
      app = "redis"
    }
    
    port {
      name        = "redis"
      port        = 6379
      target_port = 6379
    }

    port {
      name        = "metrics"
      port        = 9121
      target_port = 9121
    }

    type = "ClusterIP"
  }
}

# Random Passwords
resource "random_password" "postgresql_password" {
  count = var.postgresql_config.enabled ? 1 : 0
  
  length  = 32
  special = false
}

resource "random_password" "redis_password" {
  count = var.redis_config.enabled && var.redis_config.replicas > 1 ? 1 : 0
  
  length  = 32
  special = false
}

# Backup CronJob (if enabled)
resource "kubernetes_cron_job" "database_backup" {
  count = var.backup_enabled && (var.postgresql_config.enabled || var.redis_config.enabled) ? 1 : 0
  
  metadata {
    name      = "database-backup"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "backup"
    })
  }

  spec {
    schedule = var.backup_config.schedule
    job_template {
      metadata {
        labels = {
          component = "backup"
        }
      }
      spec {
        template {
          metadata {
            labels = {
              component = "backup"
            }
          }
          spec {
            container {
              name    = "backup"
              image   = "postgres:${var.postgresql_config.version}"
              command = ["/bin/sh", "-c"]
              args = [
                <<-EOT
                pg_dump postgresql://parking_user:${random_password.postgresql_password[0].result}@postgresql:5432/parkingdb > /backup/parkingdb-$(date +%Y%m%d-%H%M%S).sql
                if [ -n "${var.backup_config.cloud_storage_bucket}" ]; then
                  gsutil cp /backup/*.sql ${var.backup_config.cloud_storage_bucket}/ || aws s3 cp /backup/ ${var.backup_config.cloud_storage_bucket}/ --recursive || azcopy copy /backup/* ${var.backup_config.cloud_storage_bucket}/
                fi
                find /backup -type f -mtime +${var.backup_config.retention_days} -delete
                EOT
              ]
              
              volume_mount {
                name       = "backup-storage"
                mount_path = "/backup"
              }

              env {
                name = "PGPASSWORD"
                value_from {
                  secret_key_ref {
                    name = kubernetes_secret.postgresql_secret[0].metadata[0].name
                    key  = "password"
                  }
                }
              }
            }
            
            restart_policy = "OnFailure"
            
            volume {
              name = "backup-storage"
              persistent_volume_claim {
                claim_name = kubernetes_persistent_volume_claim.backup_pvc[0].metadata[0].name
              }
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "backup_pvc" {
  count = var.backup_enabled ? 1 : 0
  
  metadata {
    name      = "database-backup-pvc"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "backup"
    })
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = "20Gi"
      }
    }
    storage_class_name = var.postgresql_config.storage_class
  }
}