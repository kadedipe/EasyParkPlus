# Prometheus Configuration
resource "kubernetes_config_map" "prometheus_config" {
  metadata {
    name      = "prometheus-config"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "prometheus"
      component = "monitoring"
    })
  }

  data = {
    "prometheus.yml" = <<-EOT
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: ${var.environment}
    cluster: ${var.cluster_name}

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager:9093

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
      action: replace
      target_label: __metrics_path__
      regex: (.+)
    - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
      action: replace
      regex: ([^:]+)(?::\d+)?;(\d+)
      replacement: $$1:$$2
      target_label: __address__
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scheme]
      action: replace
      regex: (https?)
      target_label: __scheme__
    - action: labelmap
      regex: __meta_kubernetes_pod_label_(.+)
    - source_labels: [__meta_kubernetes_namespace]
      action: replace
      target_label: kubernetes_namespace
    - source_labels: [__meta_kubernetes_pod_name]
      action: replace
      target_label: kubernetes_pod_name

  - job_name: 'kubernetes-nodes'
    kubernetes_sd_configs:
    - role: node
    relabel_configs:
    - action: labelmap
      regex: __meta_kubernetes_node_label_(.+)
    - target_label: __address__
      replacement: kubernetes.default.svc:443
    - source_labels: [__meta_kubernetes_node_name]
      regex: (.+)
      target_label: __metrics_path__
      replacement: /api/v1/nodes/$$1/proxy/metrics

  - job_name: 'kubernetes-services'
    kubernetes_sd_configs:
    - role: service
    relabel_configs:
    - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
      action: replace
      target_label: __metrics_path__
      regex: (.+)
    - source_labels: [__address__, __meta_kubernetes_service_annotation_prometheus_io_port]
      action: replace
      regex: ([^:]+)(?::\d+)?;(\d+)
      replacement: $$1:$$2
      target_label: __address__
    - action: labelmap
      regex: __meta_kubernetes_service_label_(.+)
    - source_labels: [__meta_kubernetes_namespace]
      action: replace
      target_label: kubernetes_namespace
    - source_labels: [__meta_kubernetes_service_name]
      action: replace
      target_label: kubernetes_name

  - job_name: 'kubernetes-apiservers'
    kubernetes_sd_configs:
    - role: endpoints
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      insecure_skip_verify: true
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
    - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
      action: keep
      regex: default;kubernetes;https

  - job_name: 'postgresql'
    static_configs:
    - targets: ['postgresql.${var.namespace}:9187']
      labels:
        app: postgresql

  - job_name: 'redis'
    static_configs:
    - targets: ['redis.${var.namespace}:9121']
      labels:
        app: redis
EOT
  }
}

# Prometheus Rules
resource "kubernetes_config_map" "prometheus_rules" {
  metadata {
    name      = "prometheus-rules"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "prometheus"
      component = "monitoring"
    })
  }

  data = {
    "alerts.yml" = <<-EOT
groups:
  - name: parking-alerts
    interval: 30s
    rules:
    - alert: HighCPUUsage
      expr: sum(rate(container_cpu_usage_seconds_total{namespace=~".*"}[5m])) by (pod) > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High CPU usage detected"
        description: "Pod {{ $labels.pod }} has high CPU usage"

    - alert: HighMemoryUsage
      expr: sum(container_memory_usage_bytes{namespace=~".*"}) by (pod) / sum(kube_pod_container_resource_limits{resource="memory"}) by (pod) > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage detected"
        description: "Pod {{ $labels.pod }} has high memory usage"

    - alert: ServiceDown
      expr: up{job=~".*"} == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Service {{ $labels.job }} is down"
        description: "Service {{ $labels.job }} has been down for more than 1 minute"

    - alert: HighErrorRate
      expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value }}% for the last 5 minutes"

    - alert: PersistentVolumeUsage
      expr: (kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes) > 0.85
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Persistent volume usage is high"
        description: "Volume {{ $labels.persistentvolumeclaim }} is {{ $value }}% full"
EOT
  }
}

# Prometheus Deployment
resource "kubernetes_deployment" "prometheus" {
  metadata {
    name      = "prometheus"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "prometheus"
      component = "monitoring"
    })
  }

  spec {
    replicas = 1
    
    selector {
      match_labels = {
        app = "prometheus"
      }
    }

    strategy {
      type = "Recreate"
    }

    template {
      metadata {
        labels = {
          app       = "prometheus"
          component = "monitoring"
        }
        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "9090"
        }
      }

      spec {
        service_account_name = "prometheus-sa"
        
        container {
          name  = "prometheus"
          image = "prom/prometheus:v2.45.0"
          
          args = [
            "--config.file=/etc/prometheus/prometheus.yml",
            "--storage.tsdb.path=/prometheus",
            "--storage.tsdb.retention.time=${var.monitoring_config.prometheus_retention_days}d",
            "--web.enable-lifecycle",
            "--web.enable-admin-api",
            "--web.console.libraries=/usr/share/prometheus/console_libraries",
            "--web.console.templates=/usr/share/prometheus/consoles"
          ]

          port {
            container_port = 9090
            name           = "http"
          }

          resources {
            requests = {
              cpu    = "1000m"
              memory = "2Gi"
            }
            limits = {
              cpu    = "2000m"
              memory = "4Gi"
            }
          }

          volume_mount {
            name       = "prometheus-config"
            mount_path = "/etc/prometheus"
          }

          volume_mount {
            name       = "prometheus-data"
            mount_path = "/prometheus"
          }

          volume_mount {
            name       = "prometheus-rules"
            mount_path = "/etc/prometheus/rules"
          }

          liveness_probe {
            http_get {
              path = "/-/healthy"
              port = 9090
            }
            initial_delay_seconds = 60
            period_seconds        = 10
          }

          readiness_probe {
            http_get {
              path = "/-/ready"
              port = 9090
            }
            initial_delay_seconds = 30
            period_seconds        = 5
          }

          security_context {
            run_as_user                = 65534
            run_as_non_root            = true
            read_only_root_filesystem  = true
          }
        }

        container {
          name  = "config-reloader"
          image = "jimmidyson/configmap-reload:v0.8.0"
          
          args = [
            "--volume-dir=/etc/prometheus",
            "--webhook-url=http://localhost:9090/-/reload"
          ]

          volume_mount {
            name       = "prometheus-config"
            mount_path = "/etc/prometheus"
            read_only  = true
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

          security_context {
            run_as_user                = 65534
            run_as_non_root            = true
          }
        }

        volume {
          name = "prometheus-config"
          config_map {
            name = kubernetes_config_map.prometheus_config.metadata[0].name
          }
        }

        volume {
          name = "prometheus-rules"
          config_map {
            name = kubernetes_config_map.prometheus_rules.metadata[0].name
          }
        }

        volume {
          name = "prometheus-data"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.prometheus_pvc.metadata[0].name
          }
        }

        security_context {
          fs_group = 65534
        }

        node_selector = {
          "workload-type" = "monitoring"
        }

        termination_grace_period_seconds = 300
      }
    }
  }
}

# Prometheus PVC
resource "kubernetes_persistent_volume_claim" "prometheus_pvc" {
  metadata {
    name      = "prometheus-data-pvc"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "prometheus"
      component = "monitoring"
    })
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = var.monitoring_config.prometheus_storage_size
      }
    }
    storage_class_name = "standard"
  }
}

# Prometheus Service
resource "kubernetes_service" "prometheus" {
  metadata {
    name      = "prometheus"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "prometheus"
      component = "monitoring"
    })
    annotations = {
      "prometheus.io/scrape" = "true"
      "prometheus.io/port"   = "9090"
    }
  }

  spec {
    selector = {
      app = "prometheus"
    }
    
    port {
      name        = "http"
      port        = 9090
      target_port = 9090
    }

    type = "ClusterIP"
  }
}

# Grafana Deployment
resource "kubernetes_deployment" "grafana" {
  metadata {
    name      = "grafana"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "grafana"
      component = "monitoring"
    })
  }

  spec {
    replicas = 1
    
    selector {
      match_labels = {
        app = "grafana"
      }
    }

    template {
      metadata {
        labels = {
          app       = "grafana"
          component = "monitoring"
        }
      }

      spec {
        container {
          name  = "grafana"
          image = "grafana/grafana:10.0.0"
          
          port {
            container_port = 3000
            name           = "http"
          }

          env {
            name = "GF_SECURITY_ADMIN_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.grafana_secret.metadata[0].name
                key  = "admin-user"
              }
            }
          }

          env {
            name = "GF_SECURITY_ADMIN_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.grafana_secret.metadata[0].name
                key  = "admin-password"
              }
            }
          }

          env {
            name = "GF_INSTALL_PLUGINS"
            value = "grafana-piechart-panel"
          }

          env {
            name = "GF_SERVER_ROOT_URL"
            value = "https://${var.ingress_domain}"
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
            name       = "grafana-data"
            mount_path = "/var/lib/grafana"
          }

          volume_mount {
            name       = "grafana-datasources"
            mount_path = "/etc/grafana/provisioning/datasources"
            read_only  = true
          }

          liveness_probe {
            http_get {
              path = "/api/health"
              port = 3000
            }
            initial_delay_seconds = 60
            period_seconds        = 10
          }

          readiness_probe {
            http_get {
              path = "/api/health"
              port = 3000
            }
            initial_delay_seconds = 30
            period_seconds        = 5
          }
        }

        volume {
          name = "grafana-data"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.grafana_pvc.metadata[0].name
          }
        }

        volume {
          name = "grafana-datasources"
          config_map {
            name = kubernetes_config_map.grafana_datasources.metadata[0].name
          }
        }
      }
    }
  }
}

# Grafana PVC
resource "kubernetes_persistent_volume_claim" "grafana_pvc" {
  metadata {
    name      = "grafana-data-pvc"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "grafana"
      component = "monitoring"
    })
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = var.monitoring_config.grafana_storage_size
      }
    }
    storage_class_name = "standard"
  }
}

# Grafana Service
resource "kubernetes_service" "grafana" {
  metadata {
    name      = "grafana"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "grafana"
      component = "monitoring"
    })
  }

  spec {
    selector = {
      app = "grafana"
    }
    
    port {
      name        = "http"
      port        = 80
      target_port = 3000
    }

    type = "ClusterIP"
  }
}

# Node Exporter DaemonSet
resource "kubernetes_daemon_set" "node_exporter" {
  count = var.monitoring_config.node_exporter_enabled ? 1 : 0
  
  metadata {
    name      = "node-exporter"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "node-exporter"
      component = "monitoring"
    })
  }

  spec {
    selector {
      match_labels = {
        app = "node-exporter"
      }
    }

    template {
      metadata {
        labels = {
          app = "node-exporter"
        }
        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "9100"
        }
      }

      spec {
        host_pid = true
        host_ipc = false
        host_network = false

        container {
          name  = "node-exporter"
          image = "prom/node-exporter:v1.5.0"
          
          args = [
            "--path.rootfs=/host"
          ]

          port {
            container_port = 9100
            name           = "metrics"
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

          volume_mount {
            name       = "host-proc"
            mount_path = "/host/proc"
            read_only  = true
          }

          volume_mount {
            name       = "host-sys"
            mount_path = "/host/sys"
            read_only  = true
          }

          volume_mount {
            name       = "host-root"
            mount_path = "/host/root"
            read_only  = true
          }

          security_context {
            run_as_non_root = true
            run_as_user     = 65534
          }
        }

        volume {
          name = "host-proc"
          host_path {
            path = "/proc"
          }
        }

        volume {
          name = "host-sys"
          host_path {
            path = "/sys"
          }
        }

        volume {
          name = "host-root"
          host_path {
            path = "/"
          }
        }

        tolerations {
          operator = "Exists"
        }
      }
    }
  }
}

# Node Exporter Service
resource "kubernetes_service" "node_exporter" {
  count = var.monitoring_config.node_exporter_enabled ? 1 : 0
  
  metadata {
    name      = "node-exporter"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "node-exporter"
      component = "monitoring"
    })
    annotations = {
      "prometheus.io/scrape" = "true"
      "prometheus.io/port"   = "9100"
    }
  }

  spec {
    selector = {
      app = "node-exporter"
    }
    
    port {
      name        = "metrics"
      port        = 9100
      target_port = 9100
    }

    type = "ClusterIP"
    cluster_ip = "None"
  }
}

# Alert Manager (if enabled)
resource "kubernetes_deployment" "alertmanager" {
  count = var.monitoring_config.alertmanager_enabled ? 1 : 0
  
  metadata {
    name      = "alertmanager"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "alertmanager"
      component = "monitoring"
    })
  }

  spec {
    replicas = 1
    
    selector {
      match_labels = {
        app = "alertmanager"
      }
    }

    template {
      metadata {
        labels = {
          app = "alertmanager"
        }
      }

      spec {
        container {
          name  = "alertmanager"
          image = "prom/alertmanager:v0.25.0"
          
          args = [
            "--config.file=/etc/alertmanager/config.yml",
            "--storage.path=/alertmanager"
          ]

          port {
            container_port = 9093
            name           = "http"
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              cpu    = "200m"
              memory = "512Mi"
            }
          }

          volume_mount {
            name       = "alertmanager-config"
            mount_path = "/etc/alertmanager"
          }

          volume_mount {
            name       = "alertmanager-data"
            mount_path = "/alertmanager"
          }
        }

        volume {
          name = "alertmanager-config"
          config_map {
            name = kubernetes_config_map.alertmanager_config[0].metadata[0].name
          }
        }

        volume {
          name = "alertmanager-data"
          empty_dir {}
        }
      }
    }
  }
}

resource "kubernetes_config_map" "alertmanager_config" {
  count = var.monitoring_config.alertmanager_enabled ? 1 : 0
  
  metadata {
    name      = "alertmanager-config"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "alertmanager"
      component = "monitoring"
    })
  }

  data = {
    "config.yml" = <<-EOT
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'slack-notifications'
  routes:
  - match:
      severity: critical
    receiver: slack-notifications
    continue: true

receivers:
- name: 'slack-notifications'
  slack_configs:
  - channel: '#alerts'
    title: '{{ .GroupLabels.alertname }}'
    text: '{{ .CommonAnnotations.description }}'
EOT
  }
}

resource "kubernetes_service" "alertmanager" {
  count = var.monitoring_config.alertmanager_enabled ? 1 : 0
  
  metadata {
    name      = "alertmanager"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "alertmanager"
      component = "monitoring"
    })
  }

  spec {
    selector = {
      app = "alertmanager"
    }
    
    port {
      name        = "http"
      port        = 9093
      target_port = 9093
    }

    type = "ClusterIP"
  }
}

# Grafana Datasources ConfigMap
resource "kubernetes_config_map" "grafana_datasources" {
  metadata {
    name      = "grafana-datasources"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "grafana"
      component = "monitoring"
    })
  }

  data = {
    "prometheus.yaml" = <<-EOT
apiVersion: 1

datasources:
- name: Prometheus
  type: prometheus
  access: proxy
  url: http://prometheus:9090
  isDefault: true
  version: 1
  editable: true
  jsonData:
    timeInterval: 15s
    queryTimeout: 30s
    httpMethod: POST
EOT
  }
}

# Grafana Secret
resource "kubernetes_secret" "grafana_secret" {
  metadata {
    name      = "grafana-secret"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "grafana"
      component = "monitoring"
    })
  }

  data = {
    "admin-user"     = "admin"
    "admin-password" = var.monitoring_config.grafana_admin_password != "" ? var.monitoring_config.grafana_admin_password : random_password.grafana_password.result
  }

  type = "Opaque"
}

resource "random_password" "grafana_password" {
  length  = 16
  special = false
}

# Prometheus Service Account and RBAC
resource "kubernetes_service_account" "prometheus_sa" {
  metadata {
    name      = "prometheus-sa"
    namespace = var.namespace
    labels = merge(var.tags, {
      app       = "prometheus"
      component = "monitoring"
    })
  }
}

resource "kubernetes_cluster_role" "prometheus" {
  metadata {
    name = "prometheus"
    labels = merge(var.tags, {
      app       = "prometheus"
      component = "monitoring"
    })
  }

  rule {
    api_groups = [""]
    resources  = ["nodes", "nodes/metrics", "services", "endpoints", "pods"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get"]
  }

  rule {
    api_groups = ["networking.k8s.io"]
    resources  = ["ingresses"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    non_resource_urls = ["/metrics"]
    verbs             = ["get"]
  }
}

resource "kubernetes_cluster_role_binding" "prometheus" {
  metadata {
    name = "prometheus"
    labels = merge(var.tags, {
      app       = "prometheus"
      component = "monitoring"
    })
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.prometheus.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.prometheus_sa.metadata[0].name
    namespace = var.namespace
  }
}