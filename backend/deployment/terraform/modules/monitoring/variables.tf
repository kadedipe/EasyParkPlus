variable "namespace" {
  description = "Kubernetes namespace"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "monitoring_config" {
  description = "Monitoring configuration"
  type = object({
    prometheus_storage_size   = string
    prometheus_retention_days = number
    grafana_admin_password    = string
    grafana_storage_size      = string
    alertmanager_enabled      = bool
    node_exporter_enabled     = bool
  })
}

variable "cluster_name" {
  description = "Kubernetes cluster name"
  type        = string
  default     = "kubernetes"
}

variable "ingress_domain" {
  description = "Ingress domain for Grafana"
  type        = string
  default     = "grafana.local"
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}