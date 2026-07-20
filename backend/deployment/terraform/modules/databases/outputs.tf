output "connection_info" {
  description = "Database connection information"
  value = {
    postgresql = var.postgresql_config.enabled ? {
      host     = kubernetes_service.postgresql[0].metadata[0].name
      port     = 5432
      database = "parkingdb"
      user     = "parking_user"
      password = random_password.postgresql_password[0].result
      dsn      = "postgresql://parking_user:${random_password.postgresql_password[0].result}@${kubernetes_service.postgresql[0].metadata[0].name}:5432/parkingdb?sslmode=disable"
    } : null
    
    redis = var.redis_config.enabled ? {
      host = kubernetes_service.redis[0].metadata[0].name
      port = 6379
      url  = "redis://${kubernetes_service.redis[0].metadata[0].name}:6379"
    } : null
  }
  sensitive = true
}

output "secrets" {
  description = "Database secrets"
  value = {
    postgresql_secret = var.postgresql_config.enabled ? kubernetes_secret.postgresql_secret[0].metadata[0].name : null
  }
  sensitive = true
}

output "services" {
  description = "Database services"
  value = {
    postgresql = var.postgresql_config.enabled ? kubernetes_service.postgresql[0].metadata[0].name : null
    redis      = var.redis_config.enabled ? kubernetes_service.redis[0].metadata[0].name : null
  }
}

output "backup_info" {
  description = "Backup information"
  value = var.backup_enabled ? {
    cronjob_name = kubernetes_cron_job.database_backup[0].metadata[0].name
    schedule     = var.backup_config.schedule
    retention    = var.backup_config.retention_days
    pvc_name     = kubernetes_persistent_volume_claim.backup_pvc[0].metadata[0].name
  } : null
}