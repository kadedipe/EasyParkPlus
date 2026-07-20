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

variable "ingress_enabled" {
  description = "Enable ingress"
  type        = bool
  default     = true
}

variable "ingress_config" {
  description = "Ingress configuration"
  type = object({
    domain              = string
    tls_enabled         = bool
    tls_secret_name     = string
    cert_manager_enabled = bool
    ingress_class       = string
    enable_cors         = bool
  })
}

variable "service_configs" {
  description = "Service configurations"
  type        = any
}

variable "monitoring_enabled" {
  description = "Whether monitoring is enabled"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}