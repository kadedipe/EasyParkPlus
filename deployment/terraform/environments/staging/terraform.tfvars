# Environment Configuration
environment = "staging"
region      = "us-east-1"

# Kubernetes Connection
kubeconfig_path = "~/.kube/config-staging"

# PostgreSQL Configuration
postgresql_config = {
  enabled         = true
  version         = "15"
  storage_size    = "20Gi"
  storage_class   = "standard"
  replicas        = 2
  max_connections = 200
  shared_buffers  = "512MB"
}

# Redis Configuration
redis_config = {
  enabled       = true
  version       = "7.0"
  storage_size  = "10Gi"
  storage_class = "standard"
  replicas      = 2
  maxmemory     = "2gb"
}

# Service Configurations
service_configs = {
  parking-api = {
    replicas         = 2
    min_replicas_hpa = 2
    max_replicas_hpa = 8
    cpu_request      = "500m"
    memory_request   = "1Gi"
    cpu_limit        = "1000m"
    memory_limit     = "2Gi"
    image_tag        = "staging-latest"
    enable_hpa       = true
  }
  user-service = {
    replicas         = 2
    min_replicas_hpa = 2
    max_replicas_hpa = 6
    cpu_request      = "300m"
    memory_request   = "512Mi"
    cpu_limit        = "600m"
    memory_limit     = "1Gi"
    image_tag        = "staging-latest"
    enable_hpa       = true
  }
  payment-service = {
    replicas         = 2
    min_replicas_hpa = 2
    max_replicas_hpa = 10
    cpu_request      = "400m"
    memory_request   = "768Mi"
    cpu_limit        = "800m"
    memory_limit     = "1.5Gi"
    image_tag        = "staging-latest"
    enable_hpa       = true
  }
  notification-service = {
    replicas         = 1
    min_replicas_hpa = 1
    max_replicas_hpa = 4
    cpu_request      = "200m"
    memory_request   = "256Mi"
    cpu_limit        = "400m"
    memory_limit     = "512Mi"
    image_tag        = "staging-latest"
    enable_hpa       = true
  }
}

# Monitoring Configuration
monitoring_enabled = true
monitoring_config = {
  prometheus_storage_size   = "50Gi"
  prometheus_retention_days = 15
  grafana_admin_password    = "staging-admin-password-change-me"
  grafana_storage_size      = "10Gi"
  alertmanager_enabled      = true
  node_exporter_enabled     = true
}

# Ingress Configuration
ingress_enabled = true
ingress_config = {
  domain              = "staging.parking.example.com"
  tls_enabled         = true
  tls_secret_name     = "staging-tls"
  cert_manager_enabled = true
  ingress_class       = "nginx"
  enable_cors         = true
}

# Cloud Provider Configuration
cloud_provider = "none"
# Uncomment if using AWS
# cloud_provider = "aws"
# aws_region = "us-east-1"
# aws_profile = "staging"

# Feature Flags
enable_hpa              = true
enable_pdb              = true
enable_network_policies = true
enable_service_mesh     = false
resource_limits_enabled = true

# Backup Configuration
backup_enabled = true
backup_config = {
  schedule             = "0 2 * * *"
  retention_days       = 14
  storage_location     = "/backups"
  cloud_storage_bucket = "s3://parking-staging-backups"
  # For Azure: "azure://parkingstagingbackups"
  # For GCP: "gs://parking-staging-backups"
}

# Resource Quotas
resource_quotas = {
  enabled = true
  hard = {
    "requests.cpu"    = "8"
    "requests.memory" = "16Gi"
    "limits.cpu"      = "16"
    "limits.memory"   = "32Gi"
    "pods"            = "30"
    "services"        = "40"
    "secrets"         = "30"
    "configmaps"      = "30"
    "persistentvolumeclaims" = "15"
  }
}

# Node Selectors and Tolerations
node_selector = {
  "workload-type" = "application"
}

monitoring_node_selector = {
  "workload-type" = "monitoring"
}

database_node_selector = {
  "workload-type" = "database"
}

# Tolerations for specialized nodes
tolerations = [
  {
    key      = "workload-type"
    operator = "Equal"
    value    = "application"
    effect   = "NoSchedule"
  }
]

# Pod Annotations
pod_annotations = {
  "cluster-autoscaler.kubernetes.io/safe-to-evict" = "true"
  "sidecar.istio.io/inject" = "false"
}

# Image Pull Secrets
image_pull_secrets = [
  {
    name = "regcred-staging"
  }
]

# Priority Classes
priority_class_name = "staging-priority"

# Pod Security Standards
pod_security_standard = "baseline" # or "restricted" for production

# Service Mesh Configuration (if enabled)
service_mesh_config = {
  enabled = false
  mtls_mode = "permissive"
  sidecar_injection = false
}

# Logging Configuration
logging_config = {
  enabled = true
  level = "info"
  format = "json"
  output_path = "/var/log/applications"
  retention_days = 30
}

# Tracing Configuration
tracing_enabled = true
tracing_config = {
  provider = "jaeger"
  endpoint = "http://jaeger-collector:14268/api/traces"
  sampling_rate = 0.1
}

# Cost Allocation Tags
cost_allocation_tags = {
  CostCenter = "platform-staging"
  Owner      = "platform-team"
  Environment = "staging"
  Project     = "parking-management"
  Department  = "engineering"
}

# Maintenance Windows
maintenance_windows = {
  enabled = true
  start_time = "03:00"
  end_time = "05:00"
  timezone = "America/New_York"
  days_of_week = ["sunday", "wednesday"]
}

# Canary Deployment Settings
canary_config = {
  enabled = true
  weight = 10
  analysis_interval = "5m"
  success_threshold = 90
  max_failures = 2
}

# Feature Flags
feature_flags = {
  enable_chaos_engineering = false
  enable_auto_rollback = true
  enable_mutation_testing = false
  enable_performance_profiling = true
}

# Custom Metrics Configuration
custom_metrics_config = {
  enabled = true
  metrics_server_enabled = true
  prometheus_adapter_enabled = true
  custom_metrics = [
    {
      name = "http_requests_per_second"
      type = "pods"
      target_average_value = 100
    },
    {
      name = "grpc_requests_per_second"
      type = "pods"
      target_average_value = 50
    }
  ]
}

# Alerting Configuration
alerting_config = {
  enabled = true
  slack_webhook = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
  pagerduty_service_key = "your-pagerduty-key"
  email_recipients = ["alerts-staging@example.com"]
  severity_levels = ["critical", "warning", "info"]
}

# Network Policies
network_policies = {
  enabled = true
  default_deny = true
  allow_same_namespace = true
  allow_monitoring = true
  allow_ingress = true
  allow_egress_to_dns = true
}

# Pod Disruption Budget Configuration
pdb_config = {
  enabled = true
  min_available_percentage = 50
  unhealthy_pod_eviction_policy = "IfHealthyBudget"
}

# Topology Spread Constraints
topology_spread_constraints = {
  enabled = true
  max_skew = 1
  topology_key = "topology.kubernetes.io/zone"
  when_unsatisfiable = "ScheduleAnyway"
}

# Tags
tags = {
  ManagedBy   = "Terraform"
  Project     = "ParkingManagement"
  Environment = "staging"
  Tier        = "staging"
  Version     = "2.0.0"
  Owner       = "PlatformTeam"
  CostCenter  = "staging"
  BackupPolicy = "daily"
  Compliance  = "internal"
}