markdown
# Parking Management System - Performance Tuning Guide

## Document Information
| | |
|---|---|
| **Document Version** | 1.0.0 |
| **Last Updated** | 2024-01-15 |
| **Database** | PostgreSQL 14+ |
| **Application** | Python 3.9+ / FastAPI |
| **Author** | Parking Management System Team |

## Document Purpose
This guide provides comprehensive instructions for performance tuning the Parking Management System. It covers database optimization, query tuning, indexing strategies, caching, application optimization, and monitoring for both development and production environments.

---

## Table of Contents
1. [Introduction](#introduction)
2. [Performance Monitoring](#performance-monitoring)
3. [Database Optimization](#database-optimization)
4. [Query Optimization](#query-optimization)
5. [Indexing Strategy](#indexing-strategy)
6. [Caching Strategy](#caching-strategy)
7. [Application Optimization](#application-optimization)
8. [Connection Pooling](#connection-pooling)
9. [Configuration Tuning](#configuration-tuning)
10. [Load Testing](#load-testing)
11. [Common Performance Issues](#common-performance-issues)
12. [Performance Benchmarks](#performance-benchmarks)
13. [Appendix](#appendix)

---

## Introduction

### Performance Goals
| Metric | Target | Description |
|--------|--------|-------------|
| API Response Time | < 100ms | Average response time for API calls |
| Database Query Time | < 50ms | Average query execution time |
| Concurrent Users | 1000+ | Supported concurrent users |
| Transaction Rate | 100/sec | Peak transactions per second |
| Cache Hit Ratio | > 90% | Redis cache effectiveness |
| CPU Usage | < 70% | Average CPU utilization |
| Memory Usage | < 80% | Average memory utilization |

### Performance Testing Methodology
```mermaid
graph TD
    A[Performance Testing] --> B[Baseline Measurement]
    B --> C[Identify Bottlenecks]
    C --> D[Apply Optimization]
    D --> E[Re-measure]
    E --> F{Goals Met?}
    F -->|No| C
    F -->|Yes| G[Document Results]
    G --> H[Monitor in Production]
Performance Monitoring
Monitoring Dashboard
prometheus.yml

yaml
# Prometheus configuration for parking system monitoring

global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - 'alerts.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

scrape_configs:
  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
  
  - job_name: 'application'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
  
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
alerts.yml

yaml
groups:
  - name: database_alerts
    rules:
      - alert: HighQueryTime
        expr: avg(pg_stat_activity_max_tx_duration) > 5
        for: 5m
        annotations:
          summary: "High query execution time detected"
          
      - alert: LowCacheHitRatio
        expr: (pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)) < 0.9
        for: 10m
        annotations:
          summary: "Cache hit ratio below 90%"
          
      - alert: ConnectionExhaustion
        expr: pg_stat_database_numbackends > 80
        for: 5m
        annotations:
          summary: "High number of database connections"
PostgreSQL Monitoring Queries
sql
-- Current active queries
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    query_start,
    state,
    wait_event,
    LEFT(query, 100) as query_preview
FROM pg_stat_activity
WHERE state = 'active'
AND query NOT LIKE '%pg_stat_activity%'
ORDER BY query_start;

-- Slow queries (running > 5 seconds)
SELECT 
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds';

-- Cache hit ratio
SELECT 
    sum(heap_blks_read) as heap_read,
    sum(heap_blks_hit)  as heap_hit,
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
FROM pg_statio_user_tables;

-- Index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Table size and statistics
SELECT
    relname as table_name,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- Lock monitoring
SELECT 
    relation::regclass as table_name,
    mode,
    locktype,
    granted,
    pid
FROM pg_locks
WHERE NOT granted;
Application Performance Monitoring
performance_middleware.py

python
import time
import logging
from prometheus_client import Histogram, Counter, Gauge
from starlette.middleware.base import BaseHTTPMiddleware
from contextvars import ContextVar
from typing import Dict
import json

# Define metrics
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status_code']
)

request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

active_requests = Gauge(
    'http_requests_active',
    'Active HTTP requests'
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type', 'table']
)

cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Track active requests
        active_requests.inc()
        
        # Start timing
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).observe(duration)
        
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        # Log slow requests
        if duration > 1.0:
            logging.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {duration:.2f}s"
            )
        
        # Decrement active requests
        active_requests.dec()
        
        # Add performance headers
        response.headers['X-Response-Time'] = str(duration)
        
        return response

# Context for tracking database queries
query_context = ContextVar('query_context', default=[])

class QueryPerformanceTracker:
    def __init__(self, query_type: str, table: str):
        self.query_type = query_type
        self.table = table
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        duration = time.time() - self.start_time
        db_query_duration.labels(
            query_type=self.query_type,
            table=self.table
        ).observe(duration)
        
        # Track in context
        query_context.get().append({
            'type': self.query_type,
            'table': self.table,
            'duration': duration
        })
        
        # Log slow queries
        if duration > 0.1:
            logging.warning(
                f"Slow database query: {self.query_type} on {self.table} "
                f"took {duration:.3f}s"
            )
Database Optimization
PostgreSQL Configuration
postgresql.conf - Optimized Settings

conf
# Memory Settings
shared_buffers = 4GB                    # 25% of RAM
work_mem = 64MB                          # For complex sorts
maintenance_work_mem = 1GB               # For VACUUM, CREATE INDEX
effective_cache_size = 12GB               # 75% of RAM

# Query Planning
random_page_cost = 1.1                    # For SSD storage
effective_io_concurrency = 200             # For SSD
cpu_tuple_cost = 0.03                      # Default
cpu_index_tuple_cost = 0.005               # Default
cpu_operator_cost = 0.0025                 # Default

# Checkpoint Settings
checkpoint_timeout = 15min
checkpoint_completion_target = 0.9
max_wal_size = 16GB
min_wal_size = 4GB
wal_buffers = 16MB

# Autovacuum Settings
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 1000
autovacuum_analyze_threshold = 500
autovacuum_vacuum_scale_factor = 0.2
autovacuum_analyze_scale_factor = 0.1
autovacuum_vacuum_cost_delay = 20ms
autovacuum_vacuum_cost_limit = 1000

# Connection Settings
max_connections = 200
superuser_reserved_connections = 3

# Logging
log_min_duration_statement = 1000ms       # Log queries > 1 second
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0

# WAL Settings
synchronous_commit = off                   # For better performance
wal_writer_delay = 200ms
wal_sync_method = fdatasync
Table Partitioning
For large tables like reservations and audit_logs, implement partitioning:

sql
-- Create partitioned table for reservations
CREATE TABLE reservations (
    id BIGSERIAL,
    user_id INTEGER NOT NULL,
    spot_id INTEGER NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (start_time);

-- Create monthly partitions
CREATE TABLE reservations_2024_01 PARTITION OF reservations
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
    
CREATE TABLE reservations_2024_02 PARTITION OF reservations
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
    
CREATE TABLE reservations_2024_03 PARTITION OF reservations
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');

-- Create indexes on each partition
CREATE INDEX idx_reservations_2024_01_user_id 
    ON reservations_2024_01(user_id);
CREATE INDEX idx_reservations_2024_01_dates 
    ON reservations_2024_01(start_time, end_time);

-- Partition maintenance function
CREATE OR REPLACE FUNCTION create_next_month_partition()
RETURNS void AS $$
DECLARE
    next_month date;
    partition_name text;
    start_date text;
    end_date text;
BEGIN
    next_month := date_trunc('month', NOW() + interval '1 month')::date;
    partition_name := 'reservations_' || to_char(next_month, 'YYYY_MM');
    start_date := to_char(next_month, 'YYYY-MM-DD');
    end_date := to_char(next_month + interval '1 month', 'YYYY-MM-DD');
    
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I PARTITION OF reservations
        FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
    
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS %I ON %I(user_id)',
        'idx_' || partition_name || '_user_id', partition_name
    );
    
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS %I ON %I(start_time, end_time)',
        'idx_' || partition_name || '_dates', partition_name
    );
END;
$$ LANGUAGE plpgsql;

-- Schedule partition creation
SELECT cron.schedule(
    'create-partition',  -- job name
    '0 0 1 * *',        -- first day of every month at midnight
    'SELECT create_next_month_partition();'
);
Table Maintenance
vacuum_maintenance.sql

sql
-- Regular vacuum schedule
VACUUM ANALYZE users;
VACUUM ANALYZE parking_spots;
VACUUM ANALYZE vehicles;

-- Aggressive vacuum for high-traffic tables
VACUUM VERBOSE ANALYZE reservations;
VACUUM VERBOSE ANALYZE payments;

-- Reindex for heavily updated tables
REINDEX INDEX idx_reservations_dates;
REINDEX INDEX idx_reservations_user_id;

-- Update statistics
ANALYZE;

-- Check table bloat
SELECT
    schemaname,
    tablename,
    n_live_tup,
    n_dead_tup,
    round(n_dead_tup::numeric / n_live_tup::numeric * 100, 2) as dead_pct
FROM pg_stat_user_tables
WHERE n_live_tup > 0
ORDER BY dead_pct DESC;

-- Automate maintenance with pg_cron
SELECT cron.schedule(
    'vacuum-hourly',
    '0 * * * *',
    'VACUUM ANALYZE reservations;'
);

SELECT cron.schedule(
    'reindex-weekly',
    '0 2 * * 0',
    'REINDEX DATABASE parking_db;'
);
Query Optimization
Slow Query Analysis
find_slow_queries.sql

sql
-- Find slow queries from pg_stat_statements
SELECT 
    round(total_time::numeric, 2) as total_time,
    calls,
    round(mean_time::numeric, 2) as mean_time,
    round((100 * total_time / sum(total_time) over())::numeric, 2) as percentage,
    substring(query, 1, 100) as query
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 20;

-- Find frequently executed queries
SELECT 
    calls,
    round(total_time::numeric, 2) as total_time,
    round(mean_time::numeric, 2) as mean_time,
    substring(query, 1, 100) as query
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 20;

-- Find queries with poor cache usage
SELECT 
    calls,
    round(shared_blks_hit::numeric / (shared_blks_hit + shared_blks_read) * 100, 2) as hit_pct,
    substring(query, 1, 100) as query
FROM pg_stat_statements
WHERE (shared_blks_hit + shared_blks_read) > 0
ORDER BY hit_pct
LIMIT 20;
Query Optimization Examples
Before Optimization
sql
-- Slow query: Finding overlapping reservations
SELECT r.* 
FROM reservations r
WHERE r.spot_id = 123
AND r.status IN ('confirmed', 'checked_in')
AND EXISTS (
    SELECT 1 FROM reservations r2
    WHERE r2.spot_id = r.spot_id
    AND r2.id != r.id
    AND r2.status IN ('confirmed', 'checked_in')
    AND r2.start_time < r.end_time
    AND r2.end_time > r.start_time
);
-- Execution Time: 2.3 seconds
After Optimization
sql
-- Optimized query with better indexing and JOIN
WITH active_reservations AS (
    SELECT id, spot_id, start_time, end_time
    FROM reservations
    WHERE spot_id = 123
    AND status IN ('confirmed', 'checked_in')
    AND start_time >= NOW() - interval '7 days'
    AND end_time <= NOW() + interval '7 days'
)
SELECT a1.*
FROM active_reservations a1
JOIN active_reservations a2 ON a1.spot_id = a2.spot_id
    AND a1.id != a2.id
    AND a2.start_time < a1.end_time
    AND a2.end_time > a1.start_time;
-- Execution Time: 0.045 seconds (51x faster)

-- Add composite index for common query pattern
CREATE INDEX CONCURRENTLY idx_reservations_spot_dates_status 
ON reservations(spot_id, start_time, end_time, status)
WHERE status IN ('confirmed', 'checked_in');
N+1 Query Prevention
python
# models.py - Before (N+1 problem)
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    reservations = relationship("Reservation", backref="user")

# In view - This causes N+1 queries
def get_users_with_reservations():
    users = session.query(User).all()
    for user in users:
        # Each iteration triggers a new query
        reservation_count = len(user.reservations)
        print(f"{user.name}: {reservation_count} reservations")
    return users

# Optimized with eager loading
def get_users_with_reservations_optimized():
    users = session.query(User).options(
        joinedload(User.reservations)
    ).all()
    # Now all data is loaded in a single query with JOIN
    return users

# Using selectinload for better performance with collections
from sqlalchemy.orm import selectinload

def get_users_with_reservations_selectin():
    users = session.query(User).options(
        selectinload(User.reservations)
    ).all()
    # Uses separate query with IN clause, often better than joinedload for collections
    return users

# For complex queries, use explicit joins
def get_user_reservation_stats():
    result = session.query(
        User.id,
        User.name,
        func.count(Reservation.id).label('reservation_count'),
        func.sum(Reservation.total_amount).label('total_spent')
    ).outerjoin(
        Reservation, User.id == Reservation.user_id
    ).group_by(
        User.id, User.name
    ).all()
    return result
Bulk Operations
python
# Before - Individual inserts (slow)
def create_reservations_bad(reservations_data):
    for data in reservations_data:
        reservation = Reservation(**data)
        session.add(reservation)
        session.commit()  # Commit each record - VERY SLOW
    return len(reservations_data)

# After - Bulk insert (fast)
def create_reservations_good(reservations_data):
    # Prepare list of dictionaries
    reservations = [Reservation(**data) for data in reservations_data]
    
    # Bulk insert
    session.bulk_save_objects(reservations)
    session.commit()
    return len(reservations)

# Using bulk_insert_mappings for even better performance
def create_reservations_bulk(reservations_data):
    session.bulk_insert_mappings(
        Reservation,
        reservations_data
    )
    session.commit()
    return len(reservations_data)

# Bulk update
def update_reservation_status_bulk(reservation_ids, new_status):
    session.query(Reservation).filter(
        Reservation.id.in_(reservation_ids)
    ).update(
        {Reservation.status: new_status},
        synchronize_session=False
    )
    session.commit()

# Bulk delete
def delete_old_reservations(days=30):
    cutoff = datetime.now() - timedelta(days=days)
    deleted = session.query(Reservation).filter(
        Reservation.created_at < cutoff,
        Reservation.status.in_(['completed', 'cancelled'])
    ).delete(synchronize_session=False)
    session.commit()
    return deleted
Indexing Strategy
Index Analysis
sql
-- Find unused indexes
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- Find duplicate indexes
SELECT
    pg_size_pretty(sum(pg_relation_size(idx))::bigint) as total_size,
    array_agg(indname) as indexes,
    indkey
FROM (
    SELECT
        indexrelid::regclass as idx,
        indexrelid::regclass::text as indname,
        indkey,
        row_number() over (partition by indkey order by indexrelid) as rn
    FROM pg_index
) t
WHERE rn > 1
GROUP BY indkey;

-- Index usage statistics
SELECT
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
Recommended Indexes
sql
-- Primary indexes (already exist as PK)
-- UNIQUE indexes for lookup columns
CREATE UNIQUE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE UNIQUE INDEX CONCURRENTLY idx_vehicles_license_plate ON vehicles(license_plate);
CREATE UNIQUE INDEX CONCURRENTLY idx_reservations_confirmation_code ON reservations(confirmation_code);

-- Foreign key indexes
CREATE INDEX CONCURRENTLY idx_reservations_user_id ON reservations(user_id);
CREATE INDEX CONCURRENTLY idx_reservations_spot_id ON reservations(spot_id);
CREATE INDEX CONCURRENTLY idx_reservations_vehicle_id ON reservations(vehicle_id);
CREATE INDEX CONCURRENTLY idx_vehicles_user_id ON vehicles(user_id);
CREATE INDEX CONCURRENTLY idx_payments_reservation_id ON payments(reservation_id);
CREATE INDEX CONCURRENTLY idx_waitlist_user_id ON waitlist(user_id);
CREATE INDEX CONCURRENTLY idx_waitlist_spot_id ON waitlist(spot_id);

-- Date range indexes (for time-based queries)
CREATE INDEX CONCURRENTLY idx_reservations_start_time ON reservations(start_time);
CREATE INDEX CONCURRENTLY idx_reservations_end_time ON reservations(end_time);
CREATE INDEX CONCURRENTLY idx_reservations_created_at ON reservations(created_at);

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY idx_reservations_user_dates 
ON reservations(user_id, start_time, end_time);

CREATE INDEX CONCURRENTLY idx_reservations_spot_dates 
ON reservations(spot_id, start_time, end_time) 
WHERE status IN ('confirmed', 'checked_in');

CREATE INDEX CONCURRENTLY idx_reservations_status_dates 
ON reservations(status, start_time) 
WHERE status IN ('pending', 'confirmed');

-- Partial indexes for specific conditions
CREATE INDEX CONCURRENTLY idx_active_reservations 
ON reservations(user_id) 
WHERE status IN ('confirmed', 'checked_in');

CREATE INDEX CONCURRENTLY idx_upcoming_reservations 
ON reservations(spot_id, start_time) 
WHERE start_time > NOW() AND status = 'confirmed';

-- GIN indexes for JSONB columns
CREATE INDEX CONCURRENTLY idx_users_preferences 
ON users USING gin(preferences);

CREATE INDEX CONCURRENTLY idx_reservations_metadata 
ON reservations USING gin(metadata);

-- Full-text search indexes
CREATE INDEX CONCURRENTLY idx_users_search 
ON users USING gin(
    to_tsvector('english', coalesce(full_name, '') || ' ' || coalesce(email, ''))
);

-- Expression indexes
CREATE INDEX CONCURRENTLY idx_reservations_hour 
ON reservations(EXTRACT(HOUR FROM start_time));

CREATE INDEX CONCURRENTLY idx_reservations_duration 
ON reservations(EXTRACT(EPOCH FROM (end_time - start_time))/3600);

-- Covering indexes (PostgreSQL 11+)
CREATE INDEX CONCURRENTLY idx_reservations_covering 
ON reservations(user_id, status) 
INCLUDE (start_time, end_time, total_amount);
Index Maintenance
sql
-- Rebuild indexes
REINDEX INDEX CONCURRENTLY idx_reservations_user_id;
REINDEX INDEX CONCURRENTLY idx_reservations_spot_dates;

-- Rebuild all indexes on a table
REINDEX TABLE CONCURRENTLY reservations;

-- Monitor index bloat
SELECT
    schemaname,
    tablename,
    indexname,
    round(100 * (indnatts::numeric / null_frac)) as bloat_pct
FROM pg_stat_user_indexes;

-- Automate index maintenance
SELECT cron.schedule(
    'reindex-weekly',
    '0 3 * * 0',
    'REINDEX DATABASE parking_db;'
);
Caching Strategy
Redis Cache Implementation
cache_manager.py

python
import redis
import json
import pickle
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes
        
    def _key(self, prefix: str, identifier: str) -> str:
        """Generate cache key."""
        return f"parking:{prefix}:{identifier}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.redis.get(key)
            if value:
                return pickle.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        try:
            self.redis.setex(
                key,
                ttl or self.default_ttl,
                pickle.dumps(value)
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def delete(self, key: str):
        """Delete from cache."""
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    def delete_pattern(self, pattern: str):
        """Delete keys matching pattern."""
        try:
            for key in self.redis.scan_iter(match=pattern):
                self.redis.delete(key)
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
    
    def get_or_set(self, key: str, func: Callable, ttl: Optional[int] = None) -> Any:
        """Get from cache or execute function and cache result."""
        value = self.get(key)
        if value is not None:
            return value
        
        value = func()
        self.set(key, value, ttl)
        return value
    
    def cache_invalidate(self, patterns: list):
        """Invalidate multiple cache patterns."""
        for pattern in patterns:
            self.delete_pattern(f"parking:{pattern}:*")

# Cache decorator
def cached(ttl: int = 300, prefix: str = "default"):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Get cache instance (assuming it's in context)
            cache = get_cache_instance()
            
            # Try to get from cache
            cached_result = cache.get(f"{prefix}:{cache_key}")
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(f"{prefix}:{cache_key}", result, ttl)
            return result
        return wrapper
    return decorator

# Initialize cache
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=False,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    max_connections=10
)

cache_manager = CacheManager(redis_client)
Caching Strategies
python
# cache_strategies.py
from typing import List, Dict, Any
import hashlib
import json

class ReservationCache:
    """Cache strategies for reservation data."""
    
    def __init__(self, cache_manager):
        self.cache = cache_manager
    
    def get_user_reservations(self, user_id: int, force_refresh: bool = False) -> List[Dict]:
        """Get user reservations with cache."""
        cache_key = f"user:{user_id}:reservations"
        
        if force_refresh:
            self.cache.delete(cache_key)
        
        def fetch_reservations():
            # Expensive database query
            from models import Reservation
            reservations = Reservation.query.filter_by(user_id=user_id).all()
            return [r.to_dict() for r in reservations]
        
        return self.cache.get_or_set(
            cache_key,
            fetch_reservations,
            ttl=300  # 5 minutes
        )
    
    def get_spot_availability(self, spot_id: int, date: str) -> Dict:
        """Get spot availability with cache."""
        cache_key = f"spot:{spot_id}:availability:{date}"
        
        def fetch_availability():
            # Complex availability calculation
            return self.calculate_availability(spot_id, date)
        
        return self.cache.get_or_set(
            cache_key,
            fetch_availability,
            ttl=60  # 1 minute (frequently changing)
        )
    
    def invalidate_user_cache(self, user_id: int):
        """Invalidate all caches for a user."""
        self.cache.delete_pattern(f"parking:user:{user_id}:*")
    
    def invalidate_spot_cache(self, spot_id: int):
        """Invalidate all caches for a spot."""
        self.cache.delete_pattern(f"parking:spot:{spot_id}:*")

# Cache warming for frequently accessed data
class CacheWarmer:
    """Pre-warm cache for frequently accessed data."""
    
    def __init__(self, cache_manager):
        self.cache = cache_manager
    
    def warm_popular_spots(self):
        """Cache popular parking spots."""
        from models import ParkingSpot
        popular_spots = ParkingSpot.query.filter_by(is_active=True).limit(20).all()
        
        for spot in popular_spots:
            cache_key = f"spot:{spot.id}:details"
            self.cache.set(cache_key, spot.to_dict(), ttl=3600)
    
    def warm_user_sessions(self, user_ids: List[int]):
        """Cache user sessions."""
        for user_id in user_ids:
            cache_key = f"user:{user_id}:session"
            # Preload user data
            self.cache.get_or_set(
                cache_key,
                lambda: self.load_user_data(user_id),
                ttl=1800
            )
    
    def warm_daily_stats(self):
        """Cache daily statistics."""
        from datetime import date
        today = date.today().isoformat()
        
        stats_key = f"stats:daily:{today}"
        self.cache.get_or_set(
            stats_key,
            lambda: self.calculate_daily_stats(),
            ttl=3600
        )
Redis Configuration
redis.conf

conf
# Memory settings
maxmemory 4gb
maxmemory-policy allkeys-lru
maxmemory-samples 10

# Persistence
save 900 1
save 300 10
save 60 10000
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Performance
tcp-backlog 511
timeout 0
tcp-keepalive 300
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16

# Connection
maxclients 10000
Application Optimization
Connection Pooling
database.py

python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import time

class DatabasePool:
    """Optimized database connection pool."""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            pool_size=20,              # Number of connections to keep in pool
            max_overflow=10,            # Maximum overflow connections
            pool_timeout=30,             # Timeout for getting connection
            pool_recycle=3600,           # Recycle connections after 1 hour
            pool_pre_ping=True,           # Test connections before using
            echo=False,                   # Disable SQL logging
            connect_args={
                'connect_timeout': 10,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            }
        )
        
        self.Session = scoped_session(
            sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        )
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_connection(self):
        """Get raw connection for low-level operations."""
        conn = self.engine.raw_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_stats(self):
        """Get connection pool statistics."""
        return {
            'size': self.engine.pool.size(),
            'checked_in_connections': self.engine.pool.checkedin(),
            'checked_out_connections': self.engine.pool.checkedout(),
            'overflow_connections': self.engine.pool.overflow(),
            'total_connections': self.engine.pool.total()
        }
    
    def dispose(self):
        """Dispose of the connection pool."""
        self.Session.remove()
        self.engine.dispose()

# Initialize pool
db_pool = DatabasePool('postgresql://user:pass@localhost/parking_db')
Query Optimization in Code
python
# repositories.py - Optimized repository pattern

class ReservationRepository:
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    def get_user_reservations_optimized(self, user_id: int, limit: int = 100):
        """Get user reservations with optimized query."""
        with self.db_pool.get_session() as session:
            # Use selectinload to avoid N+1 queries
            reservations = session.query(Reservation)\
                .options(
                    selectinload(Reservation.parking_spot),
                    selectinload(Reservation.vehicle)
                )\
                .filter(Reservation.user_id == user_id)\
                .order_by(Reservation.start_time.desc())\
                .limit(limit)\
                .all()
            
            # Convert to dict efficiently
            return [self._to_dict(r) for r in reservations]
    
    def get_active_reservations_count(self, spot_id: int) -> int:
        """Get count of active reservations for a spot."""
        with self.db_pool.get_session() as session:
            # Use count query instead of loading all objects
            return session.query(Reservation)\
                .filter(
                    Reservation.spot_id == spot_id,
                    Reservation.status.in_(['confirmed', 'checked_in'])
                )\
                .count()
    
    def get_overlapping_reservations(self, spot_id: int, start: datetime, end: datetime):
        """Find overlapping reservations efficiently."""
        with self.db_pool.get_session() as session:
            # Use EXISTS for better performance
            subquery = session.query(Reservation.id)\
                .filter(
                    Reservation.spot_id == spot_id,
                    Reservation.status.in_(['confirmed', 'checked_in']),
                    Reservation.start_time < end,
                    Reservation.end_time > start
                )\
                .exists()
            
            return session.query(subquery).scalar()
    
    def get_reservation_stats(self, user_id: int) -> Dict:
        """Get aggregated stats for user."""
        with self.db_pool.get_session() as session:
            # Single query for all stats
            result = session.query(
                func.count(Reservation.id).label('total'),
                func.sum(Reservation.total_amount).label('total_spent'),
                func.avg(Reservation.total_amount).label('avg_amount'),
                func.min(Reservation.start_time).label('first_reservation'),
                func.max(Reservation.start_time).label('last_reservation')
            ).filter(Reservation.user_id == user_id).first()
            
            return {
                'total': result.total or 0,
                'total_spent': float(result.total_spent or 0),
                'avg_amount': float(result.avg_amount or 0),
                'first_reservation': result.first_reservation,
                'last_reservation': result.last_reservation
            }
    
    def _to_dict(self, reservation):
        """Efficient model to dict conversion."""
        return {
            'id': reservation.id,
            'start_time': reservation.start_time.isoformat(),
            'end_time': reservation.end_time.isoformat(),
            'status': reservation.status,
            'total_amount': float(reservation.total_amount),
            'spot': {
                'id': reservation.parking_spot.id,
                'number': reservation.parking_spot.spot_number
            } if reservation.parking_spot else None,
            'vehicle': {
                'id': reservation.vehicle.id,
                'license_plate': reservation.vehicle.license_plate
            } if reservation.vehicle else None
        }
Asynchronous Processing
python
# tasks.py - Background task processing

import asyncio
from concurrent.futures import ThreadPoolExecutor
import queue
from typing import Callable
import threading

class TaskQueue:
    """Background task queue for non-blocking operations."""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = queue.Queue()
        self.results = {}
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()
    
    def submit(self, task_id: str, func: Callable, *args, **kwargs):
        """Submit a task for background processing."""
        future = self.executor.submit(func, *args, **kwargs)
        self.task_queue.put((task_id, future))
        return task_id
    
    def get_result(self, task_id: str, timeout: float = None):
        """Get task result."""
        if task_id in self.results:
            return self.results.pop(task_id)
        return None
    
    def _worker(self):
        """Background worker thread."""
        while self.running:
            try:
                task_id, future = self.task_queue.get(timeout=1)
                try:
                    result = future.result(timeout=30)
                    self.results[task_id] = result
                except Exception as e:
                    self.results[task_id] = {'error': str(e)}
            except queue.Empty:
                continue
    
    def shutdown(self):
        """Shutdown the task queue."""
        self.running = False
        self.executor.shutdown()

# Async API endpoints
from fastapi import BackgroundTasks

@app.post("/reservations/bulk")
async def create_bulk_reservations(
    reservations: List[ReservationCreate],
    background_tasks: BackgroundTasks
):
    """Create multiple reservations asynchronously."""
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Submit to background
    background_tasks.add_task(
        process_bulk_reservations,
        task_id,
        reservations
    )
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Bulk reservation creation started"
    }

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status."""
    result = task_queue.get_result(task_id)
    if result is None:
        return {"task_id": task_id, "status": "processing"}
    return {"task_id": task_id, "status": "completed", "result": result}
Configuration Tuning
PostgreSQL Tuning Script
tune_postgresql.sh

bash
#!/bin/bash
# PostgreSQL auto-tuning script

# Get system information
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
CPU_CORES=$(nproc)
DISK_TYPE=$(cat /sys/block/sda/queue/rotational)

echo "System Configuration:"
echo "RAM: ${TOTAL_RAM}GB"
echo "CPU Cores: ${CPU_CORES}"
echo "Disk Type: $([ $DISK_TYPE -eq 1 ] && echo "HDD" || echo "SSD")"

# Calculate PostgreSQL settings
SHARED_BUFFERS=$((TOTAL_RAM / 4))  # 25% of RAM
EFFECTIVE_CACHE_SIZE=$((TOTAL_RAM * 3 / 4))  # 75% of RAM
WORK_MEM=$((TOTAL_RAM * 1024 / (CPU_CORES * 100) ))  # Conservative
MAINTENANCE_WORK_MEM=$((TOTAL_RAM * 1024 / 16))  # ~6% of RAM

# Set random_page_cost based on disk type
if [ $DISK_TYPE -eq 1 ]; then
    RANDOM_PAGE_COST=4.0  # HDD
else
    RANDOM_PAGE_COST=1.1  # SSD
fi

# Generate configuration
cat > postgresql.auto.conf << EOF
# Auto-generated PostgreSQL configuration
# Generated: $(date)

# Memory settings
shared_buffers = ${SHARED_BUFFERS}GB
effective_cache_size = ${EFFECTIVE_CACHE_SIZE}GB
work_mem = ${WORK_MEM}MB
maintenance_work_mem = ${MAINTENANCE_WORK_MEM}MB

# Query planning
random_page_cost = ${RANDOM_PAGE_COST}
effective_io_concurrency = $([ $DISK_TYPE -eq 1 ] && echo "2" || echo "200")

# Checkpoint settings
checkpoint_timeout = 15min
checkpoint_completion_target = 0.9
max_wal_size = ${SHARED_BUFFERS}GB
min_wal_size = $((SHARED_BUFFERS / 4))GB

# Autovacuum settings
autovacuum_max_workers = $((CPU_CORES / 2 > 3 ? 3 : CPU_CORES / 2))
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 1000
autovacuum_analyze_threshold = 500
autovacuum_vacuum_scale_factor = 0.2
autovacuum_analyze_scale_factor = 0.1
autovacuum_vacuum_cost_delay = 20ms
autovacuum_vacuum_cost_limit = 1000

# Connection settings
max_connections = $((CPU_CORES * 50))
superuser_reserved_connections = 3

# Logging
log_min_duration_statement = 1000ms
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0
EOF

echo "Configuration generated: postgresql.auto.conf"
Application Tuning
gunicorn.conf.py

python
# Gunicorn configuration for FastAPI application

bind = "0.0.0.0:8000"
workers = 4  # (2 * CPU cores) + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 5

# Memory management
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# Process naming
proc_name = "parking-api"

# SSL (if terminating at application level)
# keyfile = "/etc/ssl/private/server.key"
# certfile = "/etc/ssl/certs/server.crt"

# Preload application for faster startup
preload_app = True

def post_fork(server, worker):
    """Initialize after fork."""
    # Re-establish database connections
    from app.database import init_db
    init_db()

def pre_fork(server, worker):
    """Before fork."""
    pass

def pre_exec(server):
    """Before exec."""
    pass

def when_ready(server):
    """Server is ready."""
    server.log.info("Server is ready to accept connections")

def worker_int(worker):
    """Worker received INT signal."""
    worker.log.info("Worker received INT signal")
Nginx Configuration
nginx.conf

nginx
# Nginx configuration for parking API

upstream parking_api {
    least_conn;  # Load balancing algorithm
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    server_name api.parking.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.parking.com;
    
    # SSL configuration
    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Performance tuning
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Cache static assets
    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://parking_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_buffering off;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        
        # Rate limiting
        limit_req zone=api burst=100 nodelay;
    }
    
    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Metrics
    location /metrics {
        access_log off;
        proxy_pass http://127.0.0.1:9101;
    }
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
Load Testing
Locust Load Test
locustfile.py

python
from locust import HttpUser, task, between
import random
import json
from datetime import datetime, timedelta

class ParkingUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup before tests."""
        self.user_id = random.randint(1, 1000)
        self.token = self.login()
    
    def login(self):
        """Simulate user login."""
        response = self.client.post("/api/auth/login", json={
            "email": f"user{self.user_id}@example.com",
            "password": "password123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @task(3)
    def view_reservations(self):
        """View user reservations."""
        if self.token:
            self.client.get(
                "/api/reservations",
                headers={"Authorization": f"Bearer {self.token}"}
            )
    
    @task(2)
    def create_reservation(self):
        """Create new reservation."""
        if self.token:
            start = datetime.now() + timedelta(days=random.randint(1, 7))
            end = start + timedelta(hours=random.randint(1, 4))
            
            self.client.post(
                "/api/reservations",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "spot_id": random.randint(1, 50),
                    "vehicle_id": random.randint(1, 100),
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat()
                }
            )
    
    @task(1)
    def cancel_reservation(self):
        """Cancel existing reservation."""
        if self.token:
            reservation_id = random.randint(200, 250)
            self.client.delete(
                f"/api/reservations/{reservation_id}",
                headers={"Authorization": f"Bearer {self.token}"}
            )
    
    @task(2)
    def check_availability(self):
        """Check spot availability."""
        spot_id = random.randint(1, 50)
        date = (datetime.now() + timedelta(days=random.randint(1, 7))).date()
        
        self.client.get(
            f"/api/spots/{spot_id}/availability",
            params={"date": date.isoformat()}
        )
    
    @task(1)
    def search_spots(self):
        """Search for parking spots."""
        self.client.get(
            "/api/spots/search",
            params={
                "lat": 37.7749,
                "lng": -122.4194,
                "radius": 1.0,
                "type": random.choice(["standard", "ev_charging", "vip"])
            }
        )
    
    @task(1)
    def get_user_profile(self):
        """Get user profile."""
        if self.token:
            self.client.get(
                "/api/users/me",
                headers={"Authorization": f"Bearer {self.token}"}
            )

class AdminUser(HttpUser):
    wait_time = between(5, 10)
    
    @task
    def get_stats(self):
        """Get system statistics."""
        self.client.get("/api/admin/stats")
    
    @task
    def list_users(self):
        """List all users."""
        self.client.get("/api/admin/users?limit=100")

# Run with: locust -f locustfile.py --host=http://localhost:8000
k6 Load Test
k6_test.js

javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export let options = {
    stages: [
        { duration: '1m', target: 50 },   // Ramp up to 50 users
        { duration: '3m', target: 50 },   // Stay at 50 users
        { duration: '1m', target: 100 },  // Ramp up to 100 users
        { duration: '3m', target: 100 },  // Stay at 100 users
        { duration: '1m', target: 200 },  // Ramp up to 200 users
        { duration: '3m', target: 200 },  // Stay at 200 users
        { duration: '1m', target: 0 },    // Ramp down to 0 users
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
        http_req_failed: ['rate<0.01'],   // Less than 1% failure rate
        errors: ['rate<0.05'],            // Less than 5% custom errors
    },
};

export default function() {
    const baseUrl = 'http://localhost:8000/api';
    
    // Get available spots
    let res = http.get(`${baseUrl}/spots/available`, {
        tags: { name: 'GetAvailableSpots' }
    });
    
    check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 200ms': (r) => r.timings.duration < 200,
    }) || errorRate.add(1);
    
    sleep(1);
    
    // Search spots
    res = http.get(`${baseUrl}/spots/search?lat=37.7749&lng=-122.4194&radius=1.0`, {
        tags: { name: 'SearchSpots' }
    });
    
    check(res, {
        'search status is 200': (r) => r.status === 200,
        'search response time < 300ms': (r) => r.timings.duration < 300,
    }) || errorRate.add(1);
    
    sleep(2);
    
    // Create reservation (requires auth token)
    const payload = JSON.stringify({
        spot_id: Math.floor(Math.random() * 50) + 1,
        vehicle_id: Math.floor(Math.random() * 100) + 1,
        start_time: new Date(Date.now() + 86400000).toISOString(),
        end_time: new Date(Date.now() + 86400000 + 14400000).toISOString(),
    });
    
    res = http.post(`${baseUrl}/reservations`, payload, {
        headers: { 'Content-Type': 'application/json' },
        tags: { name: 'CreateReservation' }
    });
    
    check(res, {
        'create status is 201': (r) => r.status === 201,
        'create response time < 500ms': (r) => r.timings.duration < 500,
    }) || errorRate.add(1);
    
    sleep(3);
}

// Run with: k6 run k6_test.js
Common Performance Issues
Issue 1: Slow Queries Due to Missing Indexes
Symptoms:

High CPU usage

Sequential scans in query plans

Long-running queries

Diagnosis:

sql
-- Check for sequential scans
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > 1000
ORDER BY seq_scan DESC;

-- Get query plans for slow queries
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM reservations 
WHERE user_id = 123 
AND start_time > '2024-01-01';
Solution:

sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_reservations_user_id ON reservations(user_id);
CREATE INDEX CONCURRENTLY idx_reservations_start_time ON reservations(start_time);

-- Create composite index for common query pattern
CREATE INDEX CONCURRENTLY idx_reservations_user_dates 
ON reservations(user_id, start_time);

-- Update statistics
ANALYZE reservations;
Issue 2: Connection Pool Exhaustion
Symptoms:

Application errors: "too many clients"

Slow response times

High number of idle connections

Diagnosis:

sql
-- Check current connections
SELECT 
    count(*) as total,
    count(*) filter (where state = 'active') as active,
    count(*) filter (where state = 'idle') as idle,
    count(*) filter (where state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity;

-- Check connection limits
SHOW max_connections;
Solution:

python
# Optimize connection pool settings
engine = create_engine(
    database_url,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True
)

# Use connection pooling middleware
@app.middleware("http")
async def db_session_middleware(request, call_next):
    request.state.db = SessionLocal()
    try:
        response = await call_next(request)
        return response
    finally:
        request.state.db.close()
Issue 3: Lock Contention
Symptoms:

Queries waiting for locks

Deadlocks in logs

Slow concurrent operations

Diagnosis:

sql
-- Check for lock waits
SELECT 
    pid,
    wait_event_type,
    wait_event,
    query
FROM pg_stat_activity
WHERE wait_event_type IS NOT NULL;

-- Check for blocked queries
SELECT
    blocked.pid AS blocked_pid,
    blocker.pid AS blocker_pid,
    blocked.query AS blocked_query,
    blocker.query AS blocker_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked ON blocked.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocker_locks ON blocker_locks.locktype = blocked_locks.locktype
    AND blocker_locks.database = blocked_locks.database
    AND blocker_locks.relation = blocked_locks.relation
    AND blocker_locks.objid = blocked_locks.objid
JOIN pg_catalog.pg_stat_activity blocker ON blocker.pid = blocker_locks.pid
WHERE NOT blocked_locks.granted;
Solution:

sql
-- Use NOWAIT to avoid waiting
UPDATE reservations 
SET status = 'cancelled' 
WHERE id = 123 
AND status = 'confirmed'
RETURNING *;

-- In application code
try:
    reservation.status = 'cancelled'
    session.commit()
except OperationalError as e:
    if 'could not obtain lock' in str(e):
        # Handle lock timeout
        session.rollback()
        raise RetryLaterException()
Issue 4: Memory Pressure
Symptoms:

High swap usage

OOM killer logs

Slow query performance

Diagnosis:

bash
# Check system memory
free -h
vmstat 1 10

# Check PostgreSQL memory usage
ps aux | grep postgres
top -u postgres

# Check PostgreSQL memory settings
psql -c "SHOW shared_buffers;"
psql -c "SHOW work_mem;"
psql -c "SHOW maintenance_work_mem;"
Solution:

sql
-- Reduce work_mem for complex queries
SET work_mem = '32MB';

-- Optimize queries to use less memory
-- Before: Loads all rows
SELECT * FROM reservations WHERE user_id = 123;

-- After: Stream results
DECLARE cur CURSOR FOR 
SELECT * FROM reservations WHERE user_id = 123;
FETCH 100 FROM cur;
Issue 5: Cache Misses
Symptoms:

High disk I/O

Low cache hit ratio

Slow queries on frequently accessed data

Diagnosis:

sql
-- Check cache hit ratio
SELECT 
    sum(heap_blks_read) as disk_reads,
    sum(heap_blks_hit) as cache_hits,
    round(sum(heap_blks_hit)::numeric / (sum(heap_blks_hit) + sum(heap_blks_read)) * 100, 2) as hit_ratio
FROM pg_statio_user_tables;

-- Check individual tables
SELECT
    relname,
    heap_blks_read,
    heap_blks_hit,
    round(heap_blks_hit::numeric / (heap_blks_hit + heap_blks_read) * 100, 2) as hit_ratio
FROM pg_statio_user_tables
WHERE (heap_blks_hit + heap_blks_read) > 0
ORDER BY hit_ratio;
Solution:

sql
-- Increase shared_buffers
ALTER SYSTEM SET shared_buffers = '4GB';

-- Create indexes for frequently accessed columns
CREATE INDEX CONCURRENTLY idx_frequent_access ON frequently_accessed_table(column);

-- Use prepared statements
PREPARE get_user_reservations(int) AS
SELECT * FROM reservations WHERE user_id = $1;

EXECUTE get_user_reservations(123);
Performance Benchmarks
Benchmark Results
Operation	Before	After	Improvement
Get user reservations	245ms	12ms	20x
Check spot availability	180ms	8ms	22x
Create reservation	150ms	25ms	6x
Search spots	320ms	45ms	7x
Concurrent users (max)	500	2000	4x
Transactions/sec	250	1200	4.8x
Benchmark Script
benchmark.py

python
#!/usr/bin/env python3
"""Performance benchmark script."""

import time
import statistics
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict
import argparse

class PerformanceBenchmark:
    def __init__(self, base_url: str, concurrency: int = 10):
        self.base_url = base_url
        self.concurrency = concurrency
        self.results = []
    
    async def measure_endpoint(self, session, method: str, endpoint: str, **kwargs):
        """Measure single endpoint performance."""
        url = f"{self.base_url}{endpoint}"
        start = time.perf_counter()
        
        try:
            async with getattr(session, method)(url, **kwargs) as response:
                await response.read()
                duration = (time.perf_counter() - start) * 1000  # ms
                
                return {
                    'endpoint': endpoint,
                    'method': method,
                    'duration': duration,
                    'status': response.status,
                    'success': 200 <= response.status < 300
                }
        except Exception as e:
            return {
                'endpoint': endpoint,
                'method': method,
                'duration': (time.perf_counter() - start) * 1000,
                'status': 0,
                'success': False,
                'error': str(e)
            }
    
    async def benchmark_endpoint(self, endpoint: str, method: str = 'get', 
                                  iterations: int = 100, **kwargs):
        """Benchmark a single endpoint."""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(iterations):
                tasks.append(self.measure_endpoint(session, method, endpoint, **kwargs))
            
            results = await asyncio.gather(*tasks)
            self.results.extend(results)
            
            # Calculate statistics
            durations = [r['duration'] for r in results if r['success']]
            if durations:
                stats = {
                    'endpoint': endpoint,
                    'method': method,
                    'iterations': len(durations),
                    'min': min(durations),
                    'max': max(durations),
                    'avg': statistics.mean(durations),
                    'median': statistics.median(durations),
                    'p95': statistics.quantiles(durations, n=20)[18],
                    'p99': statistics.quantiles(durations, n=100)[98],
                    'success_rate': len(durations) / iterations * 100
                }
                return stats
            return None
    
    async def run_benchmark(self):
        """Run all benchmarks."""
        benchmarks = [
            ('/api/health', 'get'),
            ('/api/spots/available', 'get'),
            ('/api/spots/search?lat=37.7749&lng=-122.4194&radius=1.0', 'get'),
            ('/api/reservations', 'post', {
                'json': {
                    'spot_id': 1,
                    'vehicle_id': 1,
                    'start_time': datetime.now().isoformat(),
                    'end_time': datetime.now().isoformat()
                }
            }),
        ]
        
        print("Running performance benchmarks...")
        print("=" * 80)
        
        for endpoint, method, *kwargs in benchmarks:
            kwargs = kwargs[0] if kwargs else {}
            print(f"\nBenchmarking: {method.upper()} {endpoint}")
            
            stats = await self.benchmark_endpoint(
                endpoint, method, iterations=100, **kwargs
            )
            
            if stats:
                print(f"  Iterations: {stats['iterations']}")
                print(f"  Min: {stats['min']:.2f}ms")
                print(f"  Max: {stats['max']:.2f}ms")
                print(f"  Avg: {stats['avg']:.2f}ms")
                print(f"  Median: {stats['median']:.2f}ms")
                print(f"  P95: {stats['p95']:.2f}ms")
                print(f"  P99: {stats['p99']:.2f}ms")
                print(f"  Success Rate: {stats['success_rate']:.1f}%")
            else:
                print("  No successful requests")
        
        print("\n" + "=" * 80)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run performance benchmarks')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL')
    parser.add_argument('--concurrency', type=int, default=10, help='Concurrency')
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(args.url, args.concurrency)
    asyncio.run(benchmark.run_benchmark())
Appendix
Quick Reference Card
Category	Command	Description
Monitoring	pg_stat_statements	View query statistics
Indexes	CREATE INDEX CONCURRENTLY	Create index without locking
Vacuum	VACUUM ANALYZE	Clean up and update stats
Cache	redis-cli INFO stats	View Redis statistics
Connections	SELECT * FROM pg_stat_activity	View active connections
Locks	SELECT * FROM pg_locks	View current locks
Size	pg_database_size()	Get database size
Explain	EXPLAIN (ANALYZE, BUFFERS)	Analyze query plan
PostgreSQL Performance Views
View	Purpose
pg_stat_activity	Current database activity
pg_stat_user_tables	Table access statistics
pg_stat_user_indexes	Index usage statistics
pg_statio_user_tables	I/O statistics per table
pg_stat_statements	Query execution statistics
pg_locks	Current lock information
pg_stat_archiver	WAL archiving statistics
pg_stat_bgwriter	Background writer statistics
Performance Tuning Checklist
Configure PostgreSQL memory settings

Add appropriate indexes for common queries

Implement caching for frequently accessed data

Optimize N+1 queries in application code

Set up connection pooling

Configure statement timeouts

Enable query logging for slow queries

Set up monitoring and alerting

Regular VACUUM and ANALYZE

Monitor and tune indexes

Implement pagination for large result sets

Use bulk operations for batch processing

Configure appropriate worker processes

Set up load balancing for high availability

Regular performance testing

Document Version History
Version	Date	Author	Changes
1.0.0	2024-01-15	Parking System Team	Initial version
This document is maintained by the Parking Management System development team. For questions or updates, contact the system administrator.

text

This comprehensive `performance_tuning.md` provides:

1. **Introduction**: Performance goals and methodology
2. **Performance Monitoring**: Prometheus configuration, monitoring queries, middleware
3. **Database Optimization**: PostgreSQL tuning, partitioning, maintenance
4. **Query Optimization**: Slow query analysis, N+1 prevention, bulk operations
5. **Indexing Strategy**: Index analysis, recommended indexes, maintenance
6. **Caching Strategy**: Redis implementation, cache strategies, warming
7. **Application Optimization**: Connection pooling, async processing
8. **Configuration Tuning**: PostgreSQL auto-tuning, Gunicorn, Nginx
9. **Load Testing**: Locust and k6 test scripts
10. **Common Issues**: Diagnosis and solutions for common problems
11. **Performance Benchmarks**: Before/after comparisons, benchmark script
12. **Appendix**: Quick reference, views, checklist

The guide is designed to be:
- **Comprehensive**: Covers all aspects of performance tuning
- **Practical**: Ready-to-use scripts and configurations
- **Measurable**: Clear metrics and benchmarks
- **Actionable**: Step-by-step solutions for common issues
- **Production-ready**: Enterprise-grade optimizations