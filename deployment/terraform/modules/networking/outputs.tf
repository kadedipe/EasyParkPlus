output "network_policies" {
  description = "Created network policies"
  value = {
    default_deny = var.enable_network_policies ? kubernetes_network_policy.default_deny[0].metadata[0].name : null
    same_namespace = var.enable_network_policies ? kubernetes_network_policy.allow_same_namespace[0].metadata[0].name : null
  }
}

output "service_mesh_enabled" {
  description = "Whether service mesh is enabled"
  value = var.enable_service_mesh
}

output "resource_quotas" {
  description = "Resource quota information"
  value = {
    quota_name = kubernetes_resource_quota.namespace_quota.metadata[0].name
    limits     = kubernetes_resource_quota.namespace_quota.spec[0].hard
  }
}