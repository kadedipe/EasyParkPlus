"""
Configuration management for the data layer.
"""

import os
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    host: str = Field("localhost", env="DB_HOST")
    port: int = Field(5432, env="DB_PORT")
    name: str = Field("parking_db", env="DB_NAME")
    user: str = Field("parking_user", env="DB_USER")
    password: str = Field("", env="DB_PASSWORD")
    pool_size: int = Field(20, env="DB_POOL_SIZE")
    max_overflow: int = Field(40, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(1800, env="DB_POOL_RECYCLE")
    echo: bool = Field(False, env="DB_ECHO")
    
    @property
    def url(self) -> str:
        """Get database URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def async_url(self) -> str:
        """Get async database URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseSettings):
    """Redis configuration."""
    
    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    db: int = Field(0, env="REDIS_DB")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    max_connections: int = Field(50, env="REDIS_MAX_CONNECTIONS")
    socket_timeout: int = Field(5, env="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: int = Field(5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class ElasticsearchConfig(BaseSettings):
    """Elasticsearch configuration."""
    
    hosts: List[str] = Field(["localhost:9200"], env="ELASTICSEARCH_HOSTS")
    user: Optional[str] = Field(None, env="ELASTICSEARCH_USER")
    password: Optional[str] = Field(None, env="ELASTICSEARCH_PASSWORD")
    verify_certs: bool = Field(True, env="ELASTICSEARCH_VERIFY_CERTS")
    ssl_show_warn: bool = Field(False, env="ELASTICSEARCH_SSL_SHOW_WARN")
    timeout: int = Field(30, env="ELASTICSEARCH_TIMEOUT")
    maxsize: int = Field(20, env="ELASTICSEARCH_MAXSIZE")
    
    @field_validator("hosts", mode="before")
    def parse_hosts(cls, v):
        """Parse hosts from string."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v


class CacheConfig(BaseSettings):
    """Cache configuration."""
    
    ttl_user: int = Field(86400, env="CACHE_TTL_USER")
    ttl_parking_spot: int = Field(300, env="CACHE_TTL_PARKING_SPOT")
    ttl_reservation: int = Field(600, env="CACHE_TTL_RESERVATION")
    ttl_rate: int = Field(3600, env="CACHE_TTL_RATE")
    
    enable_caching: bool = Field(True, env="ENABLE_CACHING")


class BackupConfig(BaseSettings):
    """Backup configuration."""
    
    backup_dir: str = Field("/var/backups/parking", env="BACKUP_DIR")
    retention_days: int = Field(30, env="BACKUP_RETENTION_DAYS")
    s3_bucket: Optional[str] = Field(None, env="BACKUP_S3_BUCKET")
    encryption_key: Optional[str] = Field(None, env="BACKUP_ENCRYPTION_KEY")


class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    secret_key: str = Field(..., env="SECRET_KEY")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    bcrypt_rounds: int = Field(12, env="BCRYPT_ROUNDS")
    
    enable_audit_log: bool = Field(True, env="ENABLE_AUDIT_LOG")
    enable_soft_delete: bool = Field(True, env="ENABLE_SOFT_DELETE")
    
    gdpr_enabled: bool = Field(True, env="GDPR_ENABLED")
    pci_compliance: bool = Field(True, env="PCI_COMPLIANCE")
    data_retention_days: int = Field(365, env="DATA_RETENTION_DAYS")
    audit_retention_days: int = Field(730, env="AUDIT_RETENTION_DAYS")


class MonitoringConfig(BaseSettings):
    """Monitoring configuration."""
    
    prometheus_port: int = Field(8000, env="PROMETHEUS_PORT")
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    new_relic_license_key: Optional[str] = Field(None, env="NEW_RELIC_LICENSE_KEY")
    
    log_level: LogLevel = Field(LogLevel.INFO, env="LOG_LEVEL")
    enable_performance_profiling: bool = Field(False, env="ENABLE_PERFORMANCE_PROFILING")


class FeatureFlags(BaseSettings):
    """Feature flags configuration."""
    
    enable_audit_log: bool = Field(True, env="ENABLE_AUDIT_LOG")
    enable_soft_delete: bool = Field(True, env="ENABLE_SOFT_DELETE")
    enable_partitioning: bool = Field(True, env="ENABLE_PARTITIONING")
    enable_caching: bool = Field(True, env="ENABLE_CACHING")
    enable_full_text_search: bool = Field(True, env="ENABLE_FULL_TEXT_SEARCH")
    enable_rate_limiting: bool = Field(True, env="RATE_LIMIT_ENABLED")
    enable_analytics: bool = Field(True, env="ENABLE_ANALYTICS")


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""
    
    enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    requests: int = Field(100, env="RATE_LIMIT_REQUESTS")
    period: int = Field(60, env="RATE_LIMIT_PERIOD")
    
    @property
    def rate(self) -> str:
        """Get rate limit string."""
        return f"{self.requests}/{self.period}second"


class Settings(BaseSettings):
    """Main settings class."""
    
    # Environment
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(True, env="DEBUG")
    api_version: str = Field("v1", env="API_VERSION")
    
    # Component configs
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    elasticsearch: ElasticsearchConfig = ElasticsearchConfig()
    cache: CacheConfig = CacheConfig()
    backup: BackupConfig = BackupConfig()
    security: SecurityConfig = SecurityConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    features: FeatureFlags = FeatureFlags()
    rate_limit: RateLimitConfig = RateLimitConfig()
    
    # Test configuration
    test_db_name: str = Field("parking_test_db", env="TEST_DB_NAME")
    test_redis_db: int = Field(1, env="TEST_REDIS_DB")
    test_elasticsearch_index: str = Field("test_parking", env="TEST_ELASTICSEARCH_INDEX")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def is_development(self) -> bool:
        """Check if environment is development."""
        return self.environment == Environment.DEVELOPMENT
    
    def is_staging(self) -> bool:
        """Check if environment is staging."""
        return self.environment == Environment.STAGING
    
    def is_production(self) -> bool:
        """Check if environment is production."""
        return self.environment == Environment.PRODUCTION
    
    def is_test(self) -> bool:
        """Check if environment is test."""
        return self.environment == Environment.TEST


# Global settings instance
settings = Settings()