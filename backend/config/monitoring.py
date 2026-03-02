"""Monitoring and observability configuration."""

from typing import Dict, Any, Optional

from . import config


class MonitoringConfig:
    """Monitoring configuration."""
    
    # Sentry (error tracking)
    SENTRY_DSN: str = config.SENTRY_DSN
    SENTRY_ENABLED: bool = config.SENTRY_ENABLED
    SENTRY_ENVIRONMENT: str = config.SENTRY_ENVIRONMENT
    SENTRY_TRACES_SAMPLE_RATE: float = config.SENTRY_TRACES_SAMPLE_RATE
    SENTRY_PROFILING_ENABLED: bool = True
    SENTRY_PROFILING_SAMPLE_RATE: float = 0.1
    
    # Prometheus (metrics)
    PROMETHEUS_ENABLED: bool = config.PROMETHEUS_ENABLED
    PROMETHEUS_PORT: int = config.PROMETHEUS_PORT
    PROMETHEUS_METRICS_PATH: str = config.PROMETHEUS_METRICS_PATH
    
    # Health checks
    HEALTH_CHECK_PATH: str = "/health"
    READINESS_PATH: str = "/ready"
    LIVENESS_PATH: str = "/live"
    
    # Performance monitoring
    SLOW_REQUEST_THRESHOLD: float = 1.0  # seconds
    SLOW_QUERY_THRESHOLD: float = 0.5  # seconds
    
    # Custom metrics
    METRICS: Dict[str, Dict[str, Any]] = {
        "http_requests_total": {
            "type": "counter",
            "description": "Total HTTP requests",
            "labels": ["method", "endpoint", "status"],
        },
        "http_request_duration_seconds": {
            "type": "histogram",
            "description": "HTTP request duration",
            "labels": ["method", "endpoint"],
            "buckets": [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        },
        "active_requests": {
            "type": "gauge",
            "description": "Active HTTP requests",
        },
        "db_queries_total": {
            "type": "counter",
            "description": "Total database queries",
            "labels": ["operation", "table"],
        },
        "db_query_duration_seconds": {
            "type": "histogram",
            "description": "Database query duration",
            "labels": ["operation", "table"],
            "buckets": [0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
        },
        "cache_hits_total": {
            "type": "counter",
            "description": "Total cache hits",
            "labels": ["cache_type"],
        },
        "cache_misses_total": {
            "type": "counter",
            "description": "Total cache misses",
            "labels": ["cache_type"],
        },
        "reservations_created_total": {
            "type": "counter",
            "description": "Total reservations created",
        },
        "reservations_cancelled_total": {
            "type": "counter",
            "description": "Total reservations cancelled",
        },
        "active_reservations": {
            "type": "gauge",
            "description": "Active reservations",
        },
        "payments_processed_total": {
            "type": "counter",
            "description": "Total payments processed",
            "labels": ["status", "method"],
        },
        "payment_amount_total": {
            "type": "counter",
            "description": "Total payment amount",
            "labels": ["currency"],
        },
        "user_registrations_total": {
            "type": "counter",
            "description": "Total user registrations",
        },
        "active_users": {
            "type": "gauge",
            "description": "Active users",
        },
    }
    
    # Alert rules
    ALERTS: Dict[str, Dict[str, Any]] = {
        "high_error_rate": {
            "condition": "http_requests_total{status=~'5..'} / http_requests_total > 0.05",
            "duration": "5m",
            "severity": "critical",
        },
        "high_response_time": {
            "condition": "http_request_duration_seconds{p95} > 1.0",
            "duration": "10m",
            "severity": "warning",
        },
        "database_connection_exhaustion": {
            "condition": "db_connections_active > 80",
            "duration": "5m",
            "severity": "critical",
        },
        "cache_hit_ratio_low": {
            "condition": "cache_hits_total / (cache_hits_total + cache_misses_total) < 0.9",
            "duration": "15m",
            "severity": "warning",
        },
    }


monitoring_config = MonitoringConfig()