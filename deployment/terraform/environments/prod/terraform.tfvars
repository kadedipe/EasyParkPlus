# Environment Configuration
environment = "prod"
region      = "us-east-1"

# Kubernetes Connection
kubeconfig_path = "~/.kube/config-prod"

# PostgreSQL Configuration - Production Grade
postgresql_config = {
  enabled         = true
  version         = "15"
  storage_size    = "200Gi"
  storage_class   = "premium-ssd"
  replicas        = 3                     # HA configuration with 3 replicas
  max_connections = 500
  shared_buffers  = "4GB"                  # 25% of total memory
  wal_level       = "replica"               # For replication
  max_wal_senders = 10                      # For replication
  synchronous_commit = "remote_write"       # Balance between durability and performance
  synchronous_standby_names = "FIRST 1 (*)" # At least 1 sync standby
  backup_enabled  = true
  backup_retention_days = 30
  monitoring_enabled = true
  auto_vacuum_config = {
    enabled = true
    freeze_max_age = 200000000
    vacuum_cost_limit = 2000
    autovacuum_vacuum_scale_factor = 0.05
    autovacuum_analyze_scale_factor = 0.02
  }
  performance_tuning = {
    effective_cache_size = "12GB"
    maintenance_work_mem = "1GB"
    checkpoint_completion_target = 0.9
    wal_buffers = "16MB"
    default_statistics_target = 500
    random_page_cost = 1.1
    effective_io_concurrency = 200
    work_mem = "32MB"
    huge_pages = "try"
  }
  connection_pooler = {
    enabled = true
    max_pool_size = 100
    min_pool_size = 10
  }
}

# Redis Configuration - Production Grade
redis_config = {
  enabled       = true
  version       = "7.0"
  storage_size  = "50Gi"
  storage_class = "premium-ssd"
  replicas      = 3                        # HA with 3 replicas
  maxmemory     = "8gb"                     # Maximum memory usage
  maxmemory_policy = "allkeys-lru"           # Eviction policy
  appendonly    = true                       # Persistence mode
  appendfsync   = "everysec"                  # Sync frequency
  auto_aof_rewrite_percentage = 100
  auto_aof_rewrite_min_size = "64mb"
  cluster_enabled = true
  cluster_config = {
    cluster_node_timeout = 5000
    cluster_require_full_coverage = false
  }
  sentinel_enabled = true
  sentinel_config = {
    quorum = 2
    down_after_milliseconds = 5000
    failover_timeout = 10000
  }
  performance_tuning = {
    tcp_keepalive = 300
    timeout = 0
    databases = 16
    maxclients = 10000
  }
}

# Service Configurations - Production Optimized
service_configs = {
  parking-api = {
    replicas         = 5
    min_replicas_hpa = 5
    max_replicas_hpa = 30
    cpu_request      = "1000m"
    memory_request   = "2Gi"
    cpu_limit        = "2000m"
    memory_limit     = "4Gi"
    image_tag        = "prod-${var.release_version}"
    enable_hpa       = true
    enable_pdb       = true
    enable_vpa       = true
    topology_spread_enabled = true
    priority_class = "high-priority"
    pod_annotations = {
      "cluster-autoscaler.kubernetes.io/safe-to-evict" = "false"
      "sidecar.istio.io/inject" = "true"
      "vpa-optimizer.kubernetes.io/controlled" = "true"
    }
    container_security_context = {
      run_as_non_root = true
      run_as_user = 10001
      run_as_group = 10001
      capabilities = {
        drop = ["ALL"]
      }
      read_only_root_filesystem = true
      allow_privilege_escalation = false
      seccomp_profile = {
        type = "RuntimeDefault"
      }
    }
    pod_security_context = {
      fs_group = 10001
      fs_group_change_policy = "OnRootMismatch"
    }
    resources = {
      requests = {
        cpu = "1000m"
        memory = "2Gi"
        ephemeral_storage = "1Gi"
      }
      limits = {
        cpu = "2000m"
        memory = "4Gi"
        ephemeral_storage = "2Gi"
      }
    }
    probes = {
      liveness = {
        path = "/health"
        initial_delay_seconds = 60
        period_seconds = 10
        timeout_seconds = 5
        failure_threshold = 3
      }
      readiness = {
        path = "/ready"
        initial_delay_seconds = 30
        period_seconds = 5
        timeout_seconds = 3
        success_threshold = 1
        failure_threshold = 3
      }
      startup = {
        path = "/startup"
        initial_delay_seconds = 0
        period_seconds = 5
        timeout_seconds = 2
        failure_threshold = 30
      }
    }
    lifecycle = {
      pre_stop = {
        exec = {
          command = ["/bin/sh", "-c", "sleep 10"]
        }
      }
    }
    termination_grace_period_seconds = 60
  }
  
  user-service = {
    replicas         = 5
    min_replicas_hpa = 5
    max_replicas_hpa = 25
    cpu_request      = "500m"
    memory_request   = "1Gi"
    cpu_limit        = "1000m"
    memory_limit     = "2Gi"
    image_tag        = "prod-${var.release_version}"
    enable_hpa       = true
    enable_pdb       = true
    enable_vpa       = true
    topology_spread_enabled = true
    priority_class = "high-priority"
    pod_annotations = {
      "cluster-autoscaler.kubernetes.io/safe-to-evict" = "false"
      "sidecar.istio.io/inject" = "true"
    }
  }
  
  payment-service = {
    replicas         = 5
    min_replicas_hpa = 5
    max_replicas_hpa = 40
    cpu_request      = "1000m"
    memory_request   = "2Gi"
    cpu_limit        = "2000m"
    memory_limit     = "4Gi"
    image_tag        = "prod-${var.release_version}"
    enable_hpa       = true
    enable_pdb       = true
    enable_vpa       = true
    topology_spread_enabled = true
    priority_class = "critical-priority"
    pod_annotations = {
      "cluster-autoscaler.kubernetes.io/safe-to-evict" = "false"
      "sidecar.istio.io/inject" = "true"
      "vault.hashicorp.com/agent-inject" = "true"
    }
    pci_compliance = true
    audit_logging_enabled = true
  }
  
  notification-service = {
    replicas         = 3
    min_replicas_hpa = 3
    max_replicas_hpa = 20
    cpu_request      = "500m"
    memory_request   = "1Gi"
    cpu_limit        = "1000m"
    memory_limit     = "2Gi"
    image_tag        = "prod-${var.release_version}"
    enable_hpa       = true
    enable_pdb       = true
    enable_vpa       = true
    topology_spread_enabled = true
    priority_class = "medium-priority"
  }
}

# Monitoring Configuration - Comprehensive Production Monitoring
monitoring_enabled = true
monitoring_config = {
  prometheus_storage_size   = "500Gi"
  prometheus_retention_days = 60
  grafana_admin_password    = var.grafana_admin_password
  grafana_storage_size      = "100Gi"
  alertmanager_enabled      = true
  node_exporter_enabled     = true
  kube_state_metrics_enabled = true
  thanos_enabled            = true
  thanos_config = {
    bucket = "parking-prod-metrics"
    retention_days = 365
    compact_interval = "5m"
  }
  prometheus_config = {
    retention_size = "400GB"
    wal_compression = true
    query_log_enabled = true
    rule_evaluation_interval = "15s"
    scrape_interval = "15s"
    evaluation_interval = "15s"
    external_labels = {
      environment = "prod"
      cluster = "parking-prod"
    }
  }
  grafana_config = {
    ldap_enabled = true
    saml_enabled = true
    auto_assign_org = true
    viewers_can_edit = false
    editors_can_admin = false
    disable_login_form = true
    oauth_config = {
      enabled = true
      provider = "google"
      client_id = var.grafana_oauth_client_id
      client_secret = var.grafana_oauth_client_secret
    }
    plugins = [
      "grafana-piechart-panel",
      "grafana-worldmap-panel",
      "grafana-clock-panel",
      "grafana-simple-json-datasource"
    ]
    dashboards = {
      enabled = true
      auto_update = true
      provisioning_path = "/etc/grafana/provisioning/dashboards"
    }
  }
  alertmanager_config = {
    enabled = true
    replicas = 3
    retention = "120h"
    config = {
      global = {
        slack_api_url = var.slack_webhook_url
        pagerduty_url = "https://events.pagerduty.com/v2/enqueue"
        opsgenie_api_key = var.opsgenie_api_key
      }
      route = {
        group_by = ["alertname", "cluster", "service"]
        group_wait = "30s"
        group_interval = "5m"
        repeat_interval = "4h"
        receiver = "critical-notifications"
        routes = [
          {
            match = {
              severity = "critical"
            }
            receiver = "pagerduty-critical"
            continue = true
          },
          {
            match = {
              severity = "warning"
            }
            receiver = "slack-warnings"
          }
        ]
      }
      receivers = [
        {
          name = "pagerduty-critical"
          pagerduty_configs = [{
            service_key = var.pagerduty_service_key
            severity = "critical"
          }]
        },
        {
          name = "slack-warnings"
          slack_configs = [{
            channel = "#prod-alerts"
            title = "{{ .GroupLabels.alertname }}"
            text = "{{ .CommonAnnotations.description }}"
          }]
        }
      ]
    }
  }
  service_monitors = {
    enabled = true
    scrape_interval = "30s"
    sample_limit = 10000
  }
  pod_monitors = {
    enabled = true
    scrape_interval = "30s"
  }
  probe_monitors = {
    enabled = true
    scrape_interval = "60s"
  }
}

# Ingress Configuration - Production Grade
ingress_enabled = true
ingress_config = {
  domain              = "parking.example.com"
  tls_enabled         = true
  tls_secret_name     = "parking-tls"
  cert_manager_enabled = true
  ingress_class       = "nginx"
  enable_cors         = true
  waf_enabled         = true
  rate_limiting_enabled = true
  geoip_filtering_enabled = true
  allowed_countries   = ["US", "CA", "GB", "DE", "FR", "JP", "AU"]
  blocked_ips         = []
  ssl_protocols       = ["TLSv1.2", "TLSv1.3"]
  ssl_ciphers         = "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
  hsts_enabled        = true
  hsts_max_age        = 31536000
  hsts_include_subdomains = true
  hsts_preload        = true
  proxy_config = {
    proxy_connect_timeout = 30
    proxy_send_timeout = 60
    proxy_read_timeout = 60
    proxy_buffer_size = "4k"
    proxy_buffers = "8 4k"
    proxy_busy_buffers_size = "8k"
    proxy_max_temp_file_size = "1024m"
    proxy_request_buffering = "on"
    proxy_http_version = "1.1"
    proxy_set_header = {
      "X-Real-IP" = "$remote_addr"
      "X-Forwarded-For" = "$proxy_add_x_forwarded_for"
      "X-Forwarded-Proto" = "$scheme"
      "X-Forwarded-Host" = "$host"
    }
  }
  cors_config = {
    enabled = true
    allowed_origins = ["https://*.parking.example.com", "https://admin.parking.example.com"]
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers = ["DNT", "X-CustomHeader", "Keep-Alive", "User-Agent", "X-Requested-With", "If-Modified-Since", "Cache-Control", "Content-Type", "Authorization"]
    expose_headers = ["Content-Length", "Content-Range"]
    max_age = 86400
    allow_credentials = true
  }
}

# Cloud Provider Configuration - AWS Production
cloud_provider = "aws"
aws_region = "us-east-1"
aws_profile = "prod"
aws_assume_role = "arn:aws:iam::123456789012:role/TerraformProdRole"

# Multi-region failover configuration
multi_region = {
  enabled = true
  primary_region = "us-east-1"
  secondary_region = "us-west-2"
  failover_dns = "global.parking.example.com"
  auto_failover = true
  health_check_interval = 60
  unhealthy_threshold = 3
  healthy_threshold = 2
}

# Feature Flags - Production Hardened
enable_hpa              = true
enable_vpa              = true
enable_pdb              = true
enable_network_policies = true
enable_service_mesh     = true
enable_pod_security_policies = true
enable_opa_gatekeeper   = true
enable_kyverno         = true
resource_limits_enabled = true
enable_chaos_engineering = false
enable_auto_rollback    = true
enable_canary_deployments = true
enable_blue_green_deployments = true
enable_istio_mtls       = true
enable_istio_authorization = true
enable_istio_rate_limiting = true
enable_istio_circuit_breaking = true
enable_istio_retry_policies = true
enable_istio_timeout_policies = true
enable_istio_mirroring = true

# Backup Configuration - Comprehensive Backup Strategy
backup_enabled = true
backup_config = {
  schedule             = "0 1,13 * * *"  # Twice daily
  retention_days       = 90
  storage_location     = "/backups"
  cloud_storage_bucket = "s3://parking-prod-backups"
  backup_types = ["full", "incremental"]
  full_backup_day = "sunday"
  incremental_backup_frequency = "daily"
  encryption_enabled = true
  encryption_key_arn = "arn:aws:kms:us-east-1:123456789012:key/backup-key"
  verification_enabled = true
  verification_schedule = "0 6 * * 0"  # Weekly verification
  cross_region_copy = {
    enabled = true
    region = "us-west-2"
    bucket = "s3://parking-prod-backups-dr"
    retention_days = 30
  }
  point_in_time_recovery = true
  pitr_retention_days = 35
  backup_monitoring = {
    enabled = true
    alerts = {
      failed_backup = true
      skipped_backup = true
      verification_failed = true
    }
  }
}

# Disaster Recovery Configuration
dr_config = {
  enabled = true
  dr_region = "us-west-2"
  dr_cluster = "parking-prod-dr"
  replication_enabled = true
  replication_mode = "async"  # or "sync" for critical data
  recovery_time_objective = 3600  # 1 hour RTO
  recovery_point_objective = 300   # 5 minutes RPO
  dr_testing_schedule = "0 8 * * 1"  # Weekly DR testing
  failover_plan = {
    automatic = false
    manual_approval_required = true
    approvers = ["oncall@example.com", "platform-team@example.com"]
  }
}

# Security Configuration - Defense in Depth
security_config = {
  pod_security_standard = "restricted"
  enable_pod_security_policies = true
  enable_network_policies = true
  enable_secrets_encryption = true
  secrets_encryption_key = "arn:aws:kms:us-east-1:123456789012:key/secrets-key"
  enable_service_account_token_automount = false
  enable_container_security_context = true
  enable_seccomp_profiles = true
  enable_apparmor_profiles = true
  enable_selinux_options = true
  enable_read_only_root_fs = true
  enable_run_as_non_root = true
  enable_privilege_escalation = false
  enable_allow_privilege_escalation = false
  enable_capabilities_drop = ["ALL"]
  image_pull_policy = "Always"
  image_pull_secrets = ["regcred-prod"]
  vulnerability_scanning = {
    enabled = true
    scanner = "trivy"
    scan_frequency = "hourly"
    fail_on_critical = true
    fail_on_high = true
    allowed_severities = ["low", "medium"]
  }
  runtime_security = {
    enabled = true
    runtime = "falco"
    rules = ["default", "custom-prod"]
    alert_on = ["shell_open", "privilege_escalation", "k8s_service_account_token"]
  }
  audit_logging = {
    enabled = true
    destination = "cloudwatch"
    retention_days = 365
    audit_level = "RequestResponse"
  }
}

# Resource Quotas - Production Limits
resource_quotas = {
  enabled = true
  hard = {
    "requests.cpu"    = "64"
    "requests.memory" = "256Gi"
    "limits.cpu"      = "128"
    "limits.memory"   = "512Gi"
    "pods"            = "200"
    "services"        = "100"
    "secrets"         = "200"
    "configmaps"      = "200"
    "persistentvolumeclaims" = "50"
    "services.nodeports" = "20"
    "services.loadbalancers" = "10"
  }
}

# Node Selectors and Tolerations - Workload Isolation
node_selector = {
  "workload-type" = "application"
  "environment" = "prod"
  "instance-type" = "compute-optimized"
}

monitoring_node_selector = {
  "workload-type" = "monitoring"
  "environment" = "prod"
  "instance-type" = "memory-optimized"
}

database_node_selector = {
  "workload-type" = "database"
  "environment" = "prod"
  "instance-type" = "storage-optimized"
  "dedicated" = "database"
}

# Tolerations for specialized nodes
tolerations = [
  {
    key      = "workload-type"
    operator = "Equal"
    value    = "application"
    effect   = "NoSchedule"
  },
  {
    key      = "environment"
    operator = "Equal"
    value    = "prod"
    effect   = "NoSchedule"
  }
]

database_tolerations = [
  {
    key      = "workload-type"
    operator = "Equal"
    value    = "database"
    effect   = "NoSchedule"
  },
  {
    key      = "dedicated"
    operator = "Equal"
    value    = "database"
    effect   = "NoSchedule"
  }
]

# Priority Classes
priority_classes = {
  "critical-priority" = {
    value = 1000000
    global_default = false
    description = "Critical production services"
  }
  "high-priority" = {
    value = 900000
    global_default = false
    description = "High priority production services"
  }
  "medium-priority" = {
    value = 800000
    global_default = true
    description = "Medium priority production services"
  }
  "low-priority" = {
    value = 100000
    global_default = false
    description = "Low priority production services"
  }
}

# Pod Disruption Budget Configuration - High Availability
pdb_config = {
  enabled = true
  min_available_percentage = 50
  max_unavailable_percentage = 25
  unhealthy_pod_eviction_policy = "IfHealthyBudget"
  pdb_advanced = {
    critical = {
      min_available = "80%"
      max_unavailable = 1
    }
    high = {
      min_available = "70%"
      max_unavailable = "20%"
    }
    medium = {
      min_available = "50%"
      max_unavailable = "30%"
    }
  }
}

# Topology Spread Constraints - Multi-AZ Distribution
topology_spread_constraints = {
  enabled = true
  max_skew = 1
  topology_key = "topology.kubernetes.io/zone"
  when_unsatisfiable = "DoNotSchedule"
  additional_constraints = {
    "kubernetes.io/hostname" = {
      max_skew = 2
      when_unsatisfiable = "ScheduleAnyway"
    }
  }
}

# Service Mesh Configuration - Istio
service_mesh_config = {
  enabled = true
  provider = "istio"
  version = "1.18.0"
  mtls_mode = "strict"
  sidecar_injection = true
  auto_injection_namespaces = ["parking-system", "parking-database", "parking-monitoring"]
  istio_config = {
    gateway = {
      enabled = true
      servers = [
        {
          port = {
            number = 80
            protocol = "HTTP"
          }
          hosts = ["*.parking.example.com"]
          tls = {
            httpsRedirect = true
          }
        },
        {
          port = {
            number = 443
            protocol = "HTTPS"
          }
          hosts = ["*.parking.example.com"]
          tls = {
            mode = "SIMPLE"
            credentialName = "parking-tls"
          }
        }
      ]
    }
    authorization_policy = {
      enabled = true
      action = "ALLOW"
      rules = [
        {
          from = [
            {
              source = {
                requestPrincipals = ["*"]
              }
            }
          ]
        }
      ]
    }
    destination_rules = {
      traffic_policy = {
        connection_pool = {
          tcp = {
            max_connections = 100
            connect_timeout = "5s"
          }
          http = {
            http1_max_pending_requests = 100
            http2_max_requests = 100
            max_requests_per_connection = 10
          }
        }
        outlier_detection = {
          consecutive_5xx_errors = 5
          interval = "30s"
          base_ejection_time = "30s"
          max_ejection_percent = 10
        }
        load_balancer = {
          simple = "ROUND_ROBIN"
        }
      }
    }
    virtual_services = {
      retries = {
        attempts = 3
        per_try_timeout = "2s"
        retry_on = "connect-failure,refused-stream,unavailable,cancelled,resource-exhausted,retriable-status-codes"
      }
      timeout = "10s"
      fault_injection = {
        enabled = false
      }
      mirror = {
        enabled = false
      }
    }
  }
}

# Canary Deployment Configuration
canary_config = {
  enabled = true
  analysis = {
    interval = "1m"
    threshold = 5
    max_weight = 50
    step_weight = 10
    step_weight_promotion = 5
    metrics = [
      {
        name = "success-rate"
        interval = "1m"
        threshold_range = {
          min = 95
          max = 100
        }
      },
      {
        name = "latency"
        interval = "1m"
        threshold_range = {
          max = 500
        }
      }
    ]
  }
  ingress_ref = "parking-ingress"
  target_service = "parking-api"
  analysis_template = "success-rate"
}

# Logging Configuration - Comprehensive Logging
logging_config = {
  enabled = true
  provider = "elasticsearch"
  level = "info"
  format = "json"
  output_path = "/var/log/applications"
  retention_days = 90
  log_shipping = {
    enabled = true
    destination = "cloudwatch"
    buffer_size = "10MB"
    flush_interval = "5s"
  }
  log_parsing = {
    enabled = true
    parser = "json"
    custom_patterns = {}
  }
  log_filtering = {
    enabled = true
    exclude_patterns = ["healthcheck", "metrics"]
    redact_patterns = ["password", "token", "secret"]
  }
  log_aggregation = {
    enabled = true
    index_prefix = "parking-prod"
    shard_count = 5
    replica_count = 1
  }
}

# Tracing Configuration - Distributed Tracing
tracing_enabled = true
tracing_config = {
  provider = "jaeger"
  endpoint = "http://jaeger-collector:14268/api/traces"
  sampling_rate = 0.5  # Sample 50% of requests in production
  agent_endpoint = "jaeger-agent:6831"
  collector_endpoint = "http://jaeger-collector:14250"
  tags = {
    environment = "prod"
    cluster = "parking-prod"
  }
  buffer_max_spans = 1000
  queue_size = 100
  flush_interval = "1s"
  jaeger_config = {
    strategy = "probabilistic"
    param = 0.5
    collector_url = "http://jaeger-collector:14268/api/traces"
  }
}

# Cost Allocation Tags
cost_allocation_tags = {
  CostCenter = "platform-prod"
  Owner      = "platform-team"
  Environment = "prod"
  Project     = "parking-management"
  Department  = "engineering"
  Application = "parking-system"
  DataClassification = "confidential"
  Compliance = "pci-dss"
  BackupPolicy = "daily-retention-90days"
  DisasterRecovery = "cross-region"
}

# Maintenance Windows
maintenance_windows = {
  enabled = true
  start_time = "02:00"
  end_time = "06:00"
  timezone = "America/New_York"
  days_of_week = ["sunday", "wednesday"]
  blackout_periods = [
    {
      start = "2024-12-20"
      end = "2025-01-05"
      reason = "Holiday season"
    }
  ]
  notifications = {
    enabled = true
    channels = ["slack", "email"]
    recipients = ["platform@example.com"]
    advance_notice_hours = 48
  }
}

# Chaos Engineering Configuration
chaos_engineering_config = {
  enabled = false  # Disabled in production by default
  experiments = []
  schedules = []
  safeguards = {
    auto_stop = true
    max_duration = "1h"
    allowed_services = []
    notification_channels = ["security@example.com"]
  }
}

# SLO/SLI Configuration
slo_config = {
  enabled = true
  service_level_objectives = [
    {
      name = "api-availability"
      target = 99.99
      window = "30d"
      indicators = [
        {
          type = "availability"
          metric = "probe_success"
          threshold = 99.95
        }
      ]
    },
    {
      name = "api-latency"
      target = 99.9
      window = "30d"
      indicators = [
        {
          type = "latency"
          metric = "http_request_duration_seconds"
          threshold = 0.5
          percentile = 95
        }
      ]
    },
    {
      name = "payment-success-rate"
      target = 99.95
      window = "30d"
      indicators = [
        {
          type = "success_rate"
          metric = "payment_success_total / payment_total"
          threshold = 99.9
        }
      ]
    }
  ]
}

# Compliance Configuration
compliance_config = {
  pci_dss = {
    enabled = true
    scope = ["payment-service", "database"]
    audit_logging = true
    encryption_at_rest = true
    encryption_in_transit = true
    key_rotation_days = 90
    access_control = "rbac"
    quarterly_scans = true
    annual_assessment = true
  }
  soc2 = {
    enabled = true
    controls = ["security", "availability", "confidentiality"]
    audit_frequency = "quarterly"
  }
  gdpr = {
    enabled = true
    data_classification = true
    data_retention_days = 365
    right_to_be_forgotten = true
    breach_notification = true
  }
  hipaa = {
    enabled = false
  }
}

# Alerting Configuration - Production Alerting
alerting_config = {
  enabled = true
  slack_webhook = var.slack_webhook_url
  pagerduty_service_key = var.pagerduty_service_key
  opsgenie_api_key = var.opsgenie_api_key
  email_recipients = ["oncall@example.com", "platform-alerts@example.com"]
  severity_levels = ["critical", "warning", "info"]
  escalation_policies = {
    critical = {
      first = "pagerduty"
      second = "phone"
      third = "email"
      timeout_minutes = 5
    }
    warning = {
      first = "slack"
      second = "email"
      timeout_minutes = 15
    }
  }
  notification_routing = {
    business_hours = {
      start = "09:00"
      end = "17:00"
      timezone = "America/New_York"
      channels = ["slack", "email"]
    }
    after_hours = {
      channels = ["pagerduty", "phone"]
    }
    weekends = {
      channels = ["pagerduty"]
    }
  }
  silence_periods = []
  aggregation = {
    enabled = true
    max_alerts_per_group = 10
    group_by = ["alertname", "severity", "service"]
    group_interval = "30s"
  }
  inhibition_rules = [
    {
      source_match = {
        severity = "critical"
      }
      target_match = {
        severity = "warning"
      }
      equal = ["alertname", "service"]
    }
  ]
}

# Custom resource definitions (CRDs) for advanced features
custom_resources = {
  vertical_pod_autoscalers = {
    enabled = true
    update_mode = "Auto"
    min_replicas = 3
    max_replicas = 30
    controlled_resources = ["cpu", "memory"]
  }
  pod_identity = {
    enabled = true
    provider = "aws"
    role_arn = "arn:aws:iam::123456789012:role/parking-pod-identity"
  }
  secret_store = {
    enabled = true
    provider = "aws-secrets-manager"
    secrets = [
      {
        name = "database-credentials"
        key = "prod/database/credentials"
      },
      {
        name = "api-keys"
        key = "prod/api/keys"
      }
    ]
  }
}

# Variables that must be provided at runtime
# These are typically set via environment variables or CI/CD
variable "release_version" {
  description = "Release version tag for images"
  type        = string
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
}

variable "grafana_oauth_client_id" {
  description = "Grafana OAuth client ID"
  type        = string
  sensitive   = true
}

variable "grafana_oauth_client_secret" {
  description = "Grafana OAuth client secret"
  type        = string
  sensitive   = true
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts"
  type        = string
  sensitive   = true
}

variable "pagerduty_service_key" {
  description = "PagerDuty service integration key"
  type        = string
  sensitive   = true
}

variable "opsgenie_api_key" {
  description = "OpsGenie API key"
  type        = string
  sensitive   = true
}

variable "aws_access_key_id" {
  description = "AWS Access Key ID"
  type        = string
  sensitive   = true
}

variable "aws_secret_access_key" {
  description = "AWS Secret Access Key"
  type        = string
  sensitive   = true
}

variable "docker_registry_password" {
  description = "Docker registry password"
  type        = string
  sensitive   = true
}