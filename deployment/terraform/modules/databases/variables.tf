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

variable "postgresql_config" {
  description = "PostgreSQL configuration"
  type = object({
    enabled         = bool
    version         = string
    storage_size    = string
    storage_class   = string
    replicas        = number
    max_connections = number
    shared_buffers  = string
  })
}

variable "redis_config" {
  description = "Redis configuration"
  type = object({
    enabled       = bool
    version       = string
    storage_size  = string
    storage_class = string
    replicas      = number
    maxmemory     = string
  })
}

variable "backup_enabled" {
  description = "Enable backups"
  type        = bool
  default     = false
}

variable "backup_config" {
  description = "Backup configuration"
  type = object({
    schedule           = string
    retention_days     = number
    storage_location   = string
    cloud_storage_bucket = string
  })
  default = null
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}