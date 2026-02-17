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

variable "service_configs" {
  description = "Service configurations"
  type = map(object({
    replicas          = number
    min_replicas_hpa  = number
    max_replicas_hpa  = number
    cpu_request       = string
    memory_request    = string
    cpu_limit         = string
    memory_limit      = string
    image_tag         = string
    enable_hpa        = bool
  }))
}

variable "enable_hpa" {
  description = "Enable Horizontal Pod Autoscaling"
  type        = bool
  default     = true
}

variable "enable_pdb" {
  description = "Enable Pod Disruption Budgets"
  type        = bool
  default     = true
}

variable "resource_limits_enabled" {
  description = "Enable resource limits"
  type        = bool
  default     = true
}

variable "image_registry" {
  description = "Container image registry"
  type        = string
  default     = "localhost:5000/parking-management"
}

variable "postgresql_config" {
  description = "PostgreSQL configuration"
  type = any
}

variable "redis_config" {
  description = "Redis configuration"
  type = any
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}