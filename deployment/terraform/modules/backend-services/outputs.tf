output "service_endpoints" {
  description = "Service endpoints"
  value = {
    for k, v in kubernetes_service.services : k => {
      name      = v.metadata[0].name
      namespace = v.metadata[0].namespace
      cluster_ip = v.spec[0].cluster_ip
      ports     = v.spec[0].port
      internal_url = "${v.metadata[0].name}.${v.metadata[0].namespace}.svc.cluster.local"
    }
  }
}

output "deployment_status" {
  description = "Deployment status"
  value = {
    for k, v in kubernetes_deployment.services : k => {
      replicas          = v.spec[0].replicas
      available_replicas = v.status[0].available_replicas
      image             = v.spec[0].template[0].spec[0].container[0].image
    }
  }
}

output "hpa_status" {
  description = "HPA status"
  value = var.enable_hpa ? {
    for k, v in kubernetes_horizontal_pod_autoscaler_v2.hpas : k => {
      min_replicas = v.spec[0].min_replicas
      max_replicas = v.spec[0].max_replicas
    }
  } : null
}

output "secrets" {
  description = "Created secrets"
  value = {
    for k, v in kubernetes_secret.service_secrets : k => v.metadata[0].name
  }
  sensitive = true
}