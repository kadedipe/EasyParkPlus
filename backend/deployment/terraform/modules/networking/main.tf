# Network Policies
resource "kubernetes_network_policy" "default_deny" {
  count = var.enable_network_policies ? 1 : 0
  
  metadata {
    name      = "default-deny"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "networking"
    })
  }

  spec {
    pod_selector {
      match_labels = {}
    }
    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_network_policy" "allow_same_namespace" {
  count = var.enable_network_policies ? 1 : 0
  
  metadata {
    name      = "allow-same-namespace"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "networking"
    })
  }

  spec {
    pod_selector {
      match_labels = {}
    }

    ingress {
      from {
        namespace_selector {
          match_labels = {
            name = var.namespace
          }
        }
      }
    }

    egress {
      to {
        namespace_selector {
          match_labels = {
            name = var.namespace
          }
        }
      }
    }

    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_network_policy" "allow_api_to_db" {
  count = var.enable_network_policies ? 1 : 0
  
  metadata {
    name      = "allow-api-to-database"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "networking"
    })
  }

  spec {
    pod_selector {
      match_labels = {
        app = "database"
      }
    }

    ingress {
      from {
        pod_selector {
          match_labels = {
            component = "backend"
          }
        }
      }
      ports {
        port     = "5432"
        protocol = "TCP"
      }
      ports {
        port     = "6379"
        protocol = "TCP"
      }
    }

    policy_types = ["Ingress"]
  }
}

resource "kubernetes_network_policy" "allow_monitoring" {
  count = var.enable_network_policies ? 1 : 0
  
  metadata {
    name      = "allow-monitoring"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "networking"
    })
  }

  spec {
    pod_selector {
      match_labels = {}
    }

    ingress {
      from {
        namespace_selector {
          match_labels = {
            name = "${var.project_name}-monitoring"
          }
        }
      }
      ports {
        port     = "9090"
        protocol = "TCP"
      }
      ports {
        port     = "9100"
        protocol = "TCP"
      }
      ports {
        port     = "8080"
        protocol = "TCP"
      }
    }

    policy_types = ["Ingress"]
  }
}

# Service Mesh Configuration (if enabled)
resource "kubernetes_manifest" "service_mesh_config" {
  count = var.enable_service_mesh ? 1 : 0
  
  manifest = {
    apiVersion = "install.istio.io/v1alpha1"
    kind       = "IstioOperator"
    metadata = {
      name      = "istiocontrolplane"
      namespace = "istio-system"
    }
    spec = {
      profile = "default"
      components = {
        ingressGateways = {
          enabled = true
          k8s = {
            service = {
              type = "LoadBalancer"
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_manifest" "service_mesh_peer_authentication" {
  count = var.enable_service_mesh ? 1 : 0
  
  manifest = {
    apiVersion = "security.istio.io/v1beta1"
    kind       = "PeerAuthentication"
    metadata = {
      name      = "default"
      namespace = var.namespace
    }
    spec = {
      mtls = {
        mode = "PERMISSIVE"
      }
    }
  }
}

# Resource Quotas
resource "kubernetes_resource_quota" "namespace_quota" {
  metadata {
    name      = "namespace-quota"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "networking"
    })
  }

  spec {
    hard = {
      "requests.cpu"    = "4"
      "requests.memory" = "8Gi"
      "limits.cpu"      = "8"
      "limits.memory"   = "16Gi"
      "pods"            = "20"
      "services"        = "30"
      "secrets"         = "20"
      "configmaps"      = "20"
      "persistentvolumeclaims" = "10"
    }
  }
}

# Limit Ranges
resource "kubernetes_limit_range" "container_limits" {
  metadata {
    name      = "container-limits"
    namespace = var.namespace
    labels = merge(var.tags, {
      component = "networking"
    })
  }

  spec {
    limit {
      type = "Container"
      max = {
        cpu    = "2"
        memory = "4Gi"
      }
      min = {
        cpu    = "50m"
        memory = "64Mi"
      }
      default = {
        cpu    = "500m"
        memory = "512Mi"
      }
      default_request = {
        cpu    = "250m"
        memory = "256Mi"
      }
    }
  }
}