#!/usr/bin/env python3
"""
Database performance analysis script for the parking management system.

This script analyzes database performance, identifies bottlenecks,
and provides optimization recommendations. It covers query analysis,
index usage, table statistics, connection pool analysis, and more.

Usage:
    python analyze_performance.py [options]

Options:
    --db-url URL        Database connection URL
    --config FILE       Configuration file
    --output FILE       Output file for report (JSON)
    --format FORMAT     Output format (console, json, html) [default: console]
    --verbose           Verbose output
    --help              Show this help message

Analysis types:
    --analyze-all       Run all analyses
    --analyze-queries   Analyze slow queries
    --analyze-indexes   Analyze index usage
    --analyze-tables    Analyze table statistics
    --analyze-connections Analyze connection pool
    --analyze-locks     Analyze lock contention
    --analyze-cache     Analyze cache hit rates
    --analyze-vacuum    Analyze vacuum/cleanup needs

Examples:
    # Run all analyses
    python analyze_performance.py --db-url postgresql://localhost/parking

    # Generate HTML report
    python analyze_performance.py --format html --output report.html

    # Analyze specific aspects
    python analyze_performance.py --analyze-indexes --analyze-queries

    # Verbose output
    python analyze_performance.py --verbose
"""

import os
import sys
import argparse
import logging
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import statistics

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import (
    create_engine, text, inspect, MetaData, Table,
    Index, func, select, distinct
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from data.migrations.models import Base
from utils.config import Config
from utils.logging import setup_logging

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Performance Analyzer
# ============================================================================

class PerformanceAnalyzer:
    """
    Analyzes database performance and provides optimization recommendations.
    
    Performs comprehensive analysis including:
    - Query performance analysis
    - Index usage analysis
    - Table statistics
    - Connection pool analysis
    - Lock contention analysis
    - Cache hit rate analysis
    - Vacuum/cleanup needs
    """
    
    def __init__(
        self,
        db_url: str,
        config: Optional[Config] = None,
        verbose: bool = False
    ):
        """
        Initialize the performance analyzer.
        
        Args:
            db_url: Database connection URL
            config: Configuration object
            verbose: Verbose output
        """
        self.db_url = db_url
        self.config = config or Config()
        self.verbose = verbose
        
        # Create engine
        self.engine = create_engine(
            db_url,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
            echo=False
        )
        
        # Determine database type
        self.db_type = self._detect_db_type()
        
        # Analysis results
        self.results = {
            'database': {
                'url': db_url,
                'type': self.db_type,
                'analyzed_at': datetime.utcnow().isoformat()
            },
            'queries': {},
            'indexes': {},
            'tables': {},
            'connections': {},
            'locks': {},
            'cache': {},
            'vacuum': {},
            'recommendations': []
        }
        
        logger.info(f"PerformanceAnalyzer initialized for {self.db_type} database")
    
    def _detect_db_type(self) -> str:
        """Detect database type from URL."""
        if 'postgresql' in self.db_url:
            return 'postgresql'
        elif 'mysql' in self.db_url:
            return 'mysql'
        elif 'sqlite' in self.db_url:
            return 'sqlite'
        else:
            return 'unknown'
    
    # ========================================================================
    # Main Analysis Methods
    # ========================================================================
    
    def analyze_all(self) -> Dict[str, Any]:
        """Run all analyses."""
        logger.info("Running comprehensive performance analysis...")
        
        self.analyze_queries()
        self.analyze_indexes()
        self.analyze_tables()
        self.analyze_connections()
        self.analyze_locks()
        self.analyze_cache()
        self.analyze_vacuum()
        self.generate_recommendations()
        
        return self.results
    
    def analyze_queries(self) -> Dict[str, Any]:
        """Analyze slow queries and query performance."""
        logger.info("Analyzing query performance...")
        
        if self.db_type == 'postgresql':
            self._analyze_postgresql_queries()
        elif self.db_type == 'mysql':
            self._analyze_mysql_queries()
        elif self.db_type == 'sqlite':
            self._analyze_sqlite_queries()
        
        return self.results['queries']
    
    def analyze_indexes(self) -> Dict[str, Any]:
        """Analyze index usage and effectiveness."""
        logger.info("Analyzing index usage...")
        
        if self.db_type == 'postgresql':
            self._analyze_postgresql_indexes()
        elif self.db_type == 'mysql':
            self._analyze_mysql_indexes()
        elif self.db_type == 'sqlite':
            self._analyze_sqlite_indexes()
        
        return self.results['indexes']
    
    def analyze_tables(self) -> Dict[str, Any]:
        """Analyze table statistics."""
        logger.info("Analyzing table statistics...")
        
        if self.db_type == 'postgresql':
            self._analyze_postgresql_tables()
        elif self.db_type == 'mysql':
            self._analyze_mysql_tables()
        elif self.db_type == 'sqlite':
            self._analyze_sqlite_tables()
        
        return self.results['tables']
    
    def analyze_connections(self) -> Dict[str, Any]:
        """Analyze connection pool usage."""
        logger.info("Analyzing connection pool...")
        
        if self.db_type == 'postgresql':
            self._analyze_postgresql_connections()
        elif self.db_type == 'mysql':
            self._analyze_mysql_connections()
        
        return self.results['connections']
    
    def analyze_locks(self) -> Dict[str, Any]:
        """Analyze lock contention."""
        logger.info("Analyzing lock contention...")
        
        if self.db_type == 'postgresql':
            self._analyze_postgresql_locks()
        elif self.db_type == 'mysql':
            self._analyze_mysql_locks()
        
        return self.results['locks']
    
    def analyze_cache(self) -> Dict[str, Any]:
        """Analyze cache hit rates."""
        logger.info("Analyzing cache hit rates...")
        
        if self.db_type == 'postgresql':
            self._analyze_postgresql_cache()
        elif self.db_type == 'mysql':
            self._analyze_mysql_cache()
        
        return self.results['cache']
    
    def analyze_vacuum(self) -> Dict[str, Any]:
        """Analyze vacuum/cleanup needs."""
        logger.info("Analyzing vacuum needs...")
        
        if self.db_type == 'postgresql':
            self._analyze_postgresql_vacuum()
        elif self.db_type == 'mysql':
            self._analyze_mysql_optimize()
        elif self.db_type == 'sqlite':
            self._analyze_sqlite_vacuum()
        
        return self.results['vacuum']
    
    # ========================================================================
    # PostgreSQL-Specific Analysis
    # ========================================================================
    
    def _analyze_postgresql_queries(self) -> None:
        """Analyze PostgreSQL query performance."""
        with self.engine.connect() as conn:
            # Get slow queries from pg_stat_statements
            try:
                result = conn.execute(text("""
                    SELECT 
                        query,
                        calls,
                        total_exec_time / 1000 as total_time_seconds,
                        mean_exec_time / 1000 as mean_time_seconds,
                        rows,
                        shared_blks_hit,
                        shared_blks_read
                    FROM pg_stat_statements
                    ORDER BY total_exec_time DESC
                    LIMIT 20
                """))
                
                queries = []
                for row in result:
                    queries.append({
                        'query': row[0][:200] + '...' if len(row[0]) > 200 else row[0],
                        'calls': row[1],
                        'total_time_seconds': round(row[2], 2),
                        'mean_time_seconds': round(row[3], 3),
                        'rows': row[4],
                        'cache_hit_ratio': round(
                            (row[5] / (row[5] + row[6]) * 100) if (row[5] + row[6]) > 0 else 0,
                            2
                        )
                    })
                
                self.results['queries']['slow_queries'] = queries
                
            except Exception as e:
                logger.warning(f"Could not query pg_stat_statements: {e}")
                self.results['queries']['error'] = str(e)
            
            # Get query statistics by type
            result = conn.execute(text("""
                SELECT 
                    CASE 
                        WHEN query LIKE 'SELECT%' THEN 'SELECT'
                        WHEN query LIKE 'INSERT%' THEN 'INSERT'
                        WHEN query LIKE 'UPDATE%' THEN 'UPDATE'
                        WHEN query LIKE 'DELETE%' THEN 'DELETE'
                        ELSE 'OTHER'
                    END as query_type,
                    COUNT(*) as count,
                    SUM(calls) as total_calls,
                    AVG(mean_exec_time) as avg_time_ms
                FROM pg_stat_statements
                GROUP BY 1
                ORDER BY 2 DESC
            """))
            
            query_stats = []
            for row in result:
                query_stats.append({
                    'type': row[0],
                    'unique_queries': row[1],
                    'total_calls': row[2],
                    'avg_time_ms': round(row[3], 2) if row[3] else 0
                })
            
            self.results['queries']['by_type'] = query_stats
    
    def _analyze_postgresql_indexes(self) -> None:
        """Analyze PostgreSQL index usage."""
        with self.engine.connect() as conn:
            # Get index usage statistics
            result = conn.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes
                ORDER BY idx_scan ASC
            """))
            
            unused_indexes = []
            for row in result:
                if row[3] == 0:  # idx_scan = 0
                    unused_indexes.append({
                        'schema': row[0],
                        'table': row[1],
                        'index': row[2],
                        'size': row[6]
                    })
            
            self.results['indexes']['unused_indexes'] = unused_indexes
            
            # Get most used indexes
            result = conn.execute(text("""
                SELECT
                    tablename,
                    indexname,
                    idx_scan,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes
                WHERE idx_scan > 0
                ORDER BY idx_scan DESC
                LIMIT 20
            """))
            
            used_indexes = []
            for row in result:
                used_indexes.append({
                    'table': row[0],
                    'index': row[1],
                    'scans': row[2],
                    'size': row[3]
                })
            
            self.results['indexes']['most_used'] = used_indexes
            
            # Get index size information
            result = conn.execute(text("""
                SELECT
                    pg_size_pretty(sum(pg_relation_size(indexrelid))) as total_index_size,
                    count(*) as total_indexes,
                    avg(idx_scan) as avg_scans
                FROM pg_stat_user_indexes
            """))
            
            row = result.first()
            if row:
                self.results['indexes']['summary'] = {
                    'total_size': row[0],
                    'total_indexes': row[1],
                    'avg_scans': round(row[2], 2) if row[2] else 0
                }
    
    def _analyze_postgresql_tables(self) -> None:
        """Analyze PostgreSQL table statistics."""
        with self.engine.connect() as conn:
            # Get table sizes and statistics
            result = conn.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_table_size(schemaname||'.'||tablename)) as table_size,
                    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as index_size,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows,
                    round(n_dead_tup::numeric / nullif(n_live_tup, 0) * 100, 2) as dead_pct,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """))
            
            tables = []
            largest_tables = []
            high_dead_rows = []
            
            for row in result:
                table_info = {
                    'schema': row[0],
                    'table': row[1],
                    'total_size': row[2],
                    'table_size': row[3],
                    'index_size': row[4],
                    'live_rows': row[5],
                    'dead_rows': row[6],
                    'dead_percentage': row[7],
                    'last_vacuum': row[8].isoformat() if row[8] else None,
                    'last_autovacuum': row[9].isoformat() if row[9] else None,
                    'last_analyze': row[10].isoformat() if row[10] else None,
                    'last_autoanalyze': row[11].isoformat() if row[11] else None
                }
                tables.append(table_info)
                
                # Track largest tables
                largest_tables.append({
                    'table': f"{row[0]}.{row[1]}",
                    'size': row[2],
                    'live_rows': row[5]
                })
                
                # Track tables with high dead row percentage
                if row[7] > 20:  # More than 20% dead rows
                    high_dead_rows.append({
                        'table': f"{row[0]}.{row[1]}",
                        'dead_percentage': row[7],
                        'live_rows': row[5],
                        'dead_rows': row[6]
                    })
            
            self.results['tables']['all'] = tables
            self.results['tables']['largest'] = sorted(
                largest_tables,
                key=lambda x: int(x['size'].replace(' GB', '').replace(' MB', '').split()[0]),
                reverse=True
            )[:10]
            self.results['tables']['high_dead_rows'] = high_dead_rows
    
    def _analyze_postgresql_connections(self) -> None:
        """Analyze PostgreSQL connection pool."""
        with self.engine.connect() as conn:
            # Get current connections
            result = conn.execute(text("""
                SELECT
                    count(*) as total_connections,
                    count(*) filter (where state = 'active') as active_connections,
                    count(*) filter (where state = 'idle') as idle_connections,
                    count(*) filter (where state = 'idle in transaction') as idle_in_transaction,
                    max(age(now(), state_change)) as oldest_connection_age
                FROM pg_stat_activity
                WHERE datname = current_database()
            """))
            
            row = result.first()
            if row:
                self.results['connections']['current'] = {
                    'total': row[0],
                    'active': row[1],
                    'idle': row[2],
                    'idle_in_transaction': row[3],
                    'oldest_connection': str(row[4]) if row[4] else None
                }
            
            # Get connection limits
            result = conn.execute(text("""
                SELECT setting as max_connections
                FROM pg_settings
                WHERE name = 'max_connections'
            """))
            
            row = result.first()
            if row:
                self.results['connections']['limits'] = {
                    'max_connections': row[0]
                }
            
            # Get connection usage over time (last 24 hours)
            # This would require pg_stat_statements history or external monitoring
    
    def _analyze_postgresql_locks(self) -> None:
        """Analyze PostgreSQL lock contention."""
        with self.engine.connect() as conn:
            # Get current locks
            result = conn.execute(text("""
                SELECT
                    locktype,
                    mode,
                    count(*) as count,
                    count(*) filter (where granted = false) as waiting
                FROM pg_locks
                WHERE database = (SELECT oid FROM pg_database WHERE datname = current_database())
                GROUP BY locktype, mode
                ORDER BY count DESC
            """))
            
            locks = []
            for row in result:
                locks.append({
                    'lock_type': row[0],
                    'mode': row[1],
                    'count': row[2],
                    'waiting': row[3]
                })
            
            self.results['locks']['current'] = locks
            
            # Get blocking queries
            result = conn.execute(text("""
                SELECT
                    blocked.pid as blocked_pid,
                    blocked.usename as blocked_user,
                    blocking.pid as blocking_pid,
                    blocking.usename as blocking_user,
                    blocked.query as blocked_query,
                    blocking.query as blocking_query,
                    age(now(), blocked.state_change) as blocked_duration
                FROM pg_stat_activity blocked
                JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
                WHERE blocked.datname = current_database()
            """))
            
            blocking = []
            for row in result:
                blocking.append({
                    'blocked_pid': row[0],
                    'blocked_user': row[1],
                    'blocking_pid': row[2],
                    'blocking_user': row[3],
                    'blocked_query': row[4][:100] + '...' if len(row[4]) > 100 else row[4],
                    'blocking_query': row[5][:100] + '...' if len(row[5]) > 100 else row[5],
                    'blocked_duration': str(row[6]) if row[6] else None
                })
            
            self.results['locks']['blocking'] = blocking
    
    def _analyze_postgresql_cache(self) -> None:
        """Analyze PostgreSQL cache hit rates."""
        with self.engine.connect() as conn:
            # Get overall cache hit ratio
            result = conn.execute(text("""
                SELECT
                    sum(heap_blks_read) as heap_read,
                    sum(heap_blks_hit) as heap_hit,
                    round(sum(heap_blks_hit)::numeric / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100, 2) as heap_hit_ratio,
                    sum(idx_blks_read) as idx_read,
                    sum(idx_blks_hit) as idx_hit,
                    round(sum(idx_blks_hit)::numeric / nullif(sum(idx_blks_hit) + sum(idx_blks_read), 0) * 100, 2) as idx_hit_ratio
                FROM pg_statio_user_tables
            """))
            
            row = result.first()
            if row:
                self.results['cache']['overall'] = {
                    'heap_hit_ratio': row[2],
                    'index_hit_ratio': row[5]
                }
            
            # Get cache hit ratio by table
            result = conn.execute(text("""
                SELECT
                    schemaname,
                    relname,
                    heap_blks_read,
                    heap_blks_hit,
                    round(heap_blks_hit::numeric / nullif(heap_blks_hit + heap_blks_read, 0) * 100, 2) as hit_ratio
                FROM pg_statio_user_tables
                WHERE heap_blks_read + heap_blks_hit > 0
                ORDER BY hit_ratio ASC
                LIMIT 20
            """))
            
            low_cache_hit = []
            for row in result:
                if row[4] < 90:  # Less than 90% cache hit
                    low_cache_hit.append({
                        'schema': row[0],
                        'table': row[1],
                        'reads': row[2],
                        'hits': row[3],
                        'hit_ratio': row[4]
                    })
            
            self.results['cache']['low_hit_tables'] = low_cache_hit
    
    def _analyze_postgresql_vacuum(self) -> None:
        """Analyze PostgreSQL vacuum needs."""
        with self.engine.connect() as conn:
            # Get tables needing vacuum
            result = conn.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    n_dead_tup,
                    n_live_tup,
                    round(n_dead_tup::numeric / nullif(n_live_tup, 0) * 100, 2) as dead_pct,
                    last_vacuum,
                    last_autovacuum,
                    vacuum_count,
                    autovacuum_count
                FROM pg_stat_user_tables
                WHERE n_dead_tup > 1000 OR (n_dead_tup > 0 AND n_dead_tup::numeric / nullif(n_live_tup, 0) > 0.2)
                ORDER BY n_dead_tup DESC
            """))
            
            needs_vacuum = []
            for row in result:
                needs_vacuum.append({
                    'schema': row[0],
                    'table': row[1],
                    'dead_rows': row[2],
                    'live_rows': row[3],
                    'dead_percentage': row[4],
                    'last_vacuum': row[5].isoformat() if row[5] else None,
                    'last_autovacuum': row[6].isoformat() if row[6] else None,
                    'vacuum_count': row[7],
                    'autovacuum_count': row[8]
                })
            
            self.results['vacuum']['needs_vacuum'] = needs_vacuum
            
            # Get vacuum settings
            result = conn.execute(text("""
                SELECT
                    name,
                    setting,
                    unit
                FROM pg_settings
                WHERE name LIKE 'autovacuum%'
                ORDER BY name
            """))
            
            settings = []
            for row in result:
                settings.append({
                    'name': row[0],
                    'value': row[1] + (' ' + row[2] if row[2] else '')
                })
            
            self.results['vacuum']['settings'] = settings
    
    # ========================================================================
    # MySQL-Specific Analysis
    # ========================================================================
    
    def _analyze_mysql_queries(self) -> None:
        """Analyze MySQL query performance."""
        with self.engine.connect() as conn:
            # Get slow query log status
            result = conn.execute(text("SHOW VARIABLES LIKE 'slow_query_log'"))
            row = result.first()
            self.results['queries']['slow_query_log_enabled'] = (row and row[1] == 'ON')
            
            # Get long query time
            result = conn.execute(text("SHOW VARIABLES LIKE 'long_query_time'"))
            row = result.first()
            self.results['queries']['long_query_time'] = float(row[1]) if row else None
            
            # Get queries from performance_schema if available
            try:
                result = conn.execute(text("""
                    SELECT
                        digest_text as query,
                        count_star as calls,
                        sum_timer_wait / 1000000000000 as total_time_seconds,
                        avg_timer_wait / 1000000000000 as avg_time_seconds,
                        sum_rows_examined as rows_examined,
                        sum_rows_sent as rows_sent
                    FROM performance_schema.events_statements_summary_by_digest
                    ORDER BY sum_timer_wait DESC
                    LIMIT 20
                """))
                
                queries = []
                for row in result:
                    queries.append({
                        'query': row[0][:200] + '...' if len(row[0]) > 200 else row[0],
                        'calls': row[1],
                        'total_time_seconds': round(row[2], 2),
                        'avg_time_seconds': round(row[3], 3),
                        'rows_examined': row[4],
                        'rows_sent': row[5]
                    })
                
                self.results['queries']['slow_queries'] = queries
                
            except Exception as e:
                logger.warning(f"Could not query performance_schema: {e}")
    
    def _analyze_mysql_indexes(self) -> None:
        """Analyze MySQL index usage."""
        with self.engine.connect() as conn:
            # Get unused indexes
            # MySQL doesn't have built-in index usage stats like PostgreSQL
            # We need to rely on performance_schema
            try:
                result = conn.execute(text("""
                    SELECT
                        object_schema,
                        object_name,
                        index_name,
                        count_star as reads
                    FROM performance_schema.table_io_waits_summary_by_index_usage
                    WHERE index_name IS NOT NULL
                    AND count_star = 0
                    ORDER BY object_schema, object_name
                """))
                
                unused_indexes = []
                for row in result:
                    unused_indexes.append({
                        'schema': row[0],
                        'table': row[1],
                        'index': row[2]
                    })
                
                self.results['indexes']['unused_indexes'] = unused_indexes
                
            except Exception as e:
                logger.warning(f"Could not query index usage: {e}")
    
    def _analyze_mysql_tables(self) -> None:
        """Analyze MySQL table statistics."""
        with self.engine.connect() as conn:
            # Get table sizes from information_schema
            result = conn.execute(text("""
                SELECT
                    table_schema,
                    table_name,
                    round(((data_length + index_length) / 1024 / 1024), 2) as size_mb,
                    table_rows,
                    round((data_length / 1024 / 1024), 2) as data_size_mb,
                    round((index_length / 1024 / 1024), 2) as index_size_mb,
                    create_time,
                    update_time
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                ORDER BY (data_length + index_length) DESC
            """))
            
            tables = []
            for row in result:
                tables.append({
                    'schema': row[0],
                    'table': row[1],
                    'size_mb': row[2],
                    'rows': row[3],
                    'data_size_mb': row[4],
                    'index_size_mb': row[5],
                    'create_time': row[6].isoformat() if row[6] else None,
                    'update_time': row[7].isoformat() if row[7] else None
                })
            
            self.results['tables']['all'] = tables
            self.results['tables']['largest'] = tables[:10]
    
    def _analyze_mysql_connections(self) -> None:
        """Analyze MySQL connection pool."""
        with self.engine.connect() as conn:
            # Get current connections
            result = conn.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
            row = result.first()
            current_connections = int(row[1]) if row else 0
            
            result = conn.execute(text("SHOW STATUS LIKE 'Threads_running'"))
            row = result.first()
            active_connections = int(row[1]) if row else 0
            
            self.results['connections']['current'] = {
                'total': current_connections,
                'active': active_connections,
                'idle': current_connections - active_connections
            }
            
            # Get connection limits
            result = conn.execute(text("SHOW VARIABLES LIKE 'max_connections'"))
            row = result.first()
            self.results['connections']['limits'] = {
                'max_connections': int(row[1]) if row else None
            }
    
    def _analyze_mysql_locks(self) -> None:
        """Analyze MySQL lock contention."""
        with self.engine.connect() as conn:
            # Get current locks from performance_schema
            try:
                result = conn.execute(text("""
                    SELECT
                        OBJECT_SCHEMA,
                        OBJECT_NAME,
                        LOCK_TYPE,
                        COUNT(*) as count
                    FROM performance_schema.metadata_locks
                    GROUP BY OBJECT_SCHEMA, OBJECT_NAME, LOCK_TYPE
                    ORDER BY count DESC
                """))
                
                locks = []
                for row in result:
                    locks.append({
                        'schema': row[0],
                        'table': row[1],
                        'lock_type': row[2],
                        'count': row[3]
                    })
                
                self.results['locks']['current'] = locks
                
            except Exception as e:
                logger.warning(f"Could not query locks: {e}")
    
    def _analyze_mysql_cache(self) -> None:
        """Analyze MySQL cache hit rates."""
        with self.engine.connect() as conn:
            # InnoDB buffer pool hit rate
            result = conn.execute(text("SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests'"))
            row = result.first()
            read_requests = int(row[1]) if row else 0
            
            result = conn.execute(text("SHOW STATUS LIKE 'Innodb_buffer_pool_reads'"))
            row = result.first()
            physical_reads = int(row[1]) if row else 0
            
            if read_requests > 0:
                hit_ratio = (read_requests - physical_reads) / read_requests * 100
            else:
                hit_ratio = 0
            
            self.results['cache']['overall'] = {
                'buffer_pool_hit_ratio': round(hit_ratio, 2)
            }
    
    def _analyze_mysql_optimize(self) -> None:
        """Analyze MySQL optimize/cleanup needs."""
        with self.engine.connect() as conn:
            # Get table fragmentation info
            result = conn.execute(text("""
                SELECT
                    table_schema,
                    table_name,
                    data_free / 1024 / 1024 as fragmentation_mb
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND data_free > 0
                ORDER BY data_free DESC
            """))
            
            needs_optimize = []
            for row in result:
                needs_optimize.append({
                    'schema': row[0],
                    'table': row[1],
                    'fragmentation_mb': round(row[2], 2)
                })
            
            self.results['vacuum']['needs_optimize'] = needs_optimize
    
    # ========================================================================
    # SQLite-Specific Analysis
    # ========================================================================
    
    def _analyze_sqlite_queries(self) -> None:
        """Analyze SQLite query performance."""
        with self.engine.connect() as conn:
            # Get query plan for common queries
            # SQLite doesn't have query statistics, so we'll analyze schema
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            query_suggestions = []
            for table in tables:
                # Check for missing indexes on foreign keys
                fks = inspector.get_foreign_keys(table)
                for fk in fks:
                    for column in fk['constrained_columns']:
                        # Check if index exists on this column
                        indexes = inspector.get_indexes(table)
                        has_index = any(
                            column in idx['column_names']
                            for idx in indexes
                        )
                        if not has_index:
                            query_suggestions.append({
                                'table': table,
                                'column': column,
                                'suggestion': f"Add index on {table}.{column} for foreign key"
                            })
            
            self.results['queries']['suggestions'] = query_suggestions
    
    def _analyze_sqlite_indexes(self) -> None:
        """Analyze SQLite index usage."""
        with self.engine.connect() as conn:
            # Get all indexes
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            indexes = []
            for table in tables:
                table_indexes = inspector.get_indexes(table)
                for idx in table_indexes:
                    # Get index size (approximate)
                    result = conn.execute(text(f"PRAGMA index_info({idx['name']})"))
                    columns = [row[2] for row in result]
                    
                    indexes.append({
                        'table': table,
                        'name': idx['name'],
                        'columns': columns,
                        'unique': idx['unique']
                    })
            
            self.results['indexes']['all'] = indexes
    
    def _analyze_sqlite_tables(self) -> None:
        """Analyze SQLite table statistics."""
        with self.engine.connect() as conn:
            # Get table info from sqlite_master
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            table_stats = []
            for table in tables:
                # Get row count
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                row_count = result.scalar()
                
                # Get table size (approximate)
                result = conn.execute(text(f"SELECT pages FROM sqlite_master WHERE name='{table}'"))
                # This is simplified - actual size calculation is more complex
                
                table_stats.append({
                    'table': table,
                    'rows': row_count,
                    'columns': len(inspector.get_columns(table))
                })
            
            self.results['tables']['all'] = table_stats
    
    def _analyze_sqlite_vacuum(self) -> None:
        """Analyze SQLite vacuum needs."""
        with self.engine.connect() as conn:
            # Get database info
            result = conn.execute(text("PRAGMA page_count"))
            page_count = result.scalar() or 0
            
            result = conn.execute(text("PRAGMA freelist_count"))
            free_pages = result.scalar() or 0
            
            if page_count > 0:
                fragmentation = (free_pages / page_count) * 100
            else:
                fragmentation = 0
            
            self.results['vacuum']['needs_vacuum'] = fragmentation > 20
            self.results['vacuum']['fragmentation'] = round(fragmentation, 2)
            self.results['vacuum']['page_count'] = page_count
            self.results['vacuum']['free_pages'] = free_pages
    
    # ========================================================================
    # Recommendations
    # ========================================================================
    
    def generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []
        
        # Index recommendations
        if self.results['indexes'].get('unused_indexes'):
            count = len(self.results['indexes']['unused_indexes'])
            recommendations.append(
                f"Found {count} unused indexes that could be removed to save space "
                "and improve write performance."
            )
        
        # Table recommendations
        if self.results['tables'].get('high_dead_rows'):
            for table in self.results['tables']['high_dead_rows'][:5]:
                recommendations.append(
                    f"Table {table['table']} has {table['dead_percentage']}% dead rows. "
                    "Consider running VACUUM to reclaim space."
                )
        
        # Cache recommendations
        cache = self.results['cache'].get('overall', {})
        if cache.get('heap_hit_ratio', 100) < 90:
            recommendations.append(
                f"Low cache hit ratio ({cache['heap_hit_ratio']}%). "
                "Consider increasing shared_buffers / buffer pool size."
            )
        
        if self.results['cache'].get('low_hit_tables'):
            for table in self.results['cache']['low_hit_tables'][:3]:
                recommendations.append(
                    f"Table {table['schema']}.{table['table']} has low cache hit ratio "
                    f"({table['hit_ratio']}%). Consider reviewing query patterns or increasing cache size."
                )
        
        # Connection recommendations
        connections = self.results['connections'].get('current', {})
        limits = self.results['connections'].get('limits', {})
        if limits.get('max_connections') and connections.get('total'):
            usage_pct = (connections['total'] / limits['max_connections']) * 100
            if usage_pct > 80:
                recommendations.append(
                    f"High connection usage ({usage_pct:.1f}% of max). "
                    "Consider increasing max_connections or reviewing connection pool settings."
                )
        
        # Lock recommendations
        if self.results['locks'].get('blocking'):
            count = len(self.results['locks']['blocking'])
            recommendations.append(
                f"Found {count} blocking queries. Review long-running transactions "
                "and consider optimizing query patterns."
            )
        
        # Vacuum recommendations
        if self.results['vacuum'].get('needs_vacuum'):
            if self.db_type == 'postgresql':
                recommendations.append(
                    "Tables need vacuuming. Schedule regular VACUUM or adjust autovacuum settings."
                )
            elif self.db_type == 'mysql':
                frag_tables = self.results['vacuum'].get('needs_optimize', [])
                if frag_tables:
                    recommendations.append(
                        f"Found {len(frag_tables)} fragmented tables. Consider running OPTIMIZE TABLE."
                    )
            elif self.db_type == 'sqlite':
                if self.results['vacuum'].get('needs_vacuum'):
                    recommendations.append(
                        f"Database fragmentation is {self.results['vacuum']['fragmentation']}%. "
                        "Consider running VACUUM to reclaim space."
                    )
        
        # Query recommendations
        if self.results['queries'].get('slow_queries'):
            count = len(self.results['queries']['slow_queries'])
            recommendations.append(
                f"Found {count} slow queries. Review execution plans and consider adding indexes."
            )
        
        self.results['recommendations'] = recommendations
        return recommendations
    
    # ========================================================================
    # Output Methods
    # ========================================================================
    
    def print_report(self) -> None:
        """Print analysis report to console."""
        print("\n" + "="*80)
        print("DATABASE PERFORMANCE ANALYSIS REPORT")
        print("="*80)
        print(f"Database: {self.results['database']['url']}")
        print(f"Type: {self.results['database']['type']}")
        print(f"Analyzed: {self.results['database']['analyzed_at']}")
        print("="*80)
        
        # Summary
        print("\n📊 SUMMARY")
        print("-"*40)
        
        # Tables
        tables = self.results['tables'].get('all', [])
        total_rows = sum(t.get('live_rows', t.get('rows', 0)) for t in tables)
        print(f"Total Tables: {len(tables)}")
        print(f"Total Rows: {total_rows:,}")
        
        if self.results['tables'].get('largest'):
            print(f"Largest Table: {self.results['tables']['largest'][0]['table']} "
                  f"({self.results['tables']['largest'][0]['size']})")
        
        # Indexes
        indexes = self.results['indexes'].get('summary', {})
        if indexes:
            print(f"\n📇 INDEXES")
            print(f"Total Indexes: {indexes.get('total_indexes', 0)}")
            print(f"Total Index Size: {indexes.get('total_size', '0')}")
            print(f"Avg Scans per Index: {indexes.get('avg_scans', 0)}")
        
        if self.results['indexes'].get('unused_indexes'):
            print(f"Unused Indexes: {len(self.results['indexes']['unused_indexes'])}")
        
        # Cache
        cache = self.results['cache'].get('overall', {})
        if cache:
            print(f"\n💾 CACHE")
            if 'heap_hit_ratio' in cache:
                print(f"Table Cache Hit Ratio: {cache['heap_hit_ratio']}%")
            if 'index_hit_ratio' in cache:
                print(f"Index Cache Hit Ratio: {cache['index_hit_ratio']}%")
            if 'buffer_pool_hit_ratio' in cache:
                print(f"Buffer Pool Hit Ratio: {cache['buffer_pool_hit_ratio']}%")
        
        # Connections
        connections = self.results['connections'].get('current', {})
        limits = self.results['connections'].get('limits', {})
        if connections:
            print(f"\n🔌 CONNECTIONS")
            print(f"Current: {connections.get('total', 0)}")
            print(f"Active: {connections.get('active', 0)}")
            print(f"Idle: {connections.get('idle', 0)}")
            if limits.get('max_connections'):
                print(f"Max: {limits['max_connections']}")
        
        # Locks
        if self.results['locks'].get('blocking'):
            print(f"\n🔒 LOCKS")
            print(f"Blocking Queries: {len(self.results['locks']['blocking'])}")
        
        # Vacuum
        if self.results['vacuum'].get('needs_vacuum'):
            print(f"\n🧹 VACUUM")
            if self.db_type == 'postgresql':
                print(f"Tables needing vacuum: {len(self.results['vacuum'].get('needs_vacuum', []))}")
            elif self.db_type == 'mysql':
                print(f"Tables needing optimize: {len(self.results['vacuum'].get('needs_optimize', []))}")
            elif self.db_type == 'sqlite':
                print(f"Fragmentation: {self.results['vacuum'].get('fragmentation', 0)}%")
        
        # Recommendations
        if self.results['recommendations']:
            print("\n💡 RECOMMENDATIONS")
            print("-"*40)
            for i, rec in enumerate(self.results['recommendations'], 1):
                print(f"{i}. {rec}")
        
        print("\n" + "="*80)
    
    def save_report(self, output_file: str, format: str = 'json') -> None:
        """
        Save analysis report to file.
        
        Args:
            output_file: Output file path
            format: Output format ('json' or 'html')
        """
        if format == 'json':
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            logger.info(f"Report saved to: {output_file}")
        
        elif format == 'html':
            self._save_html_report(output_file)
    
    def _save_html_report(self, output_file: str) -> None:
        """Save report as HTML."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Database Performance Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .summary {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; }}
                .recommendation {{ background-color: #fff3cd; padding: 10px; margin: 5px 0; border-left: 4px solid #ffc107; }}
                .metric {{ font-weight: bold; color: #0066cc; }}
            </style>
        </head>
        <body>
            <h1>Database Performance Analysis Report</h1>
            <div class="summary">
                <p><strong>Database:</strong> {self.results['database']['url']}</p>
                <p><strong>Type:</strong> {self.results['database']['type']}</p>
                <p><strong>Analyzed:</strong> {self.results['database']['analyzed_at']}</p>
            </div>
            
            <h2>📊 Summary</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Tables</td><td>{len(self.results['tables'].get('all', []))}</td></tr>
        """
        
        # Add more HTML content based on results
        
        html += """
            </table>
            <p><em>Report generated by PerformanceAnalyzer</em></p>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html)
        logger.info(f"HTML report saved to: {output_file}")


# ============================================================================
# Main Script
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Analyze database performance')
    
    # Database options
    parser.add_argument('--db-url', help='Database connection URL')
    parser.add_argument('--config', help='Configuration file path')
    
    # Output options
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--format', choices=['console', 'json', 'html'], 
                       default='console', help='Output format')
    
    # Analysis options
    parser.add_argument('--analyze-all', action='store_true', help='Run all analyses')
    parser.add_argument('--analyze-queries', action='store_true', help='Analyze slow queries')
    parser.add_argument('--analyze-indexes', action='store_true', help='Analyze index usage')
    parser.add_argument('--analyze-tables', action='store_true', help='Analyze table statistics')
    parser.add_argument('--analyze-connections', action='store_true', help='Analyze connection pool')
    parser.add_argument('--analyze-locks', action='store_true', help='Analyze lock contention')
    parser.add_argument('--analyze-cache', action='store_true', help='Analyze cache hit rates')
    parser.add_argument('--analyze-vacuum', action='store_true', help='Analyze vacuum needs')
    
    # Other options
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Load configuration
    config = None
    if args.config:
        config = Config(args.config)
    else:
        config = Config()
    
    # Get database URL
    db_url = args.db_url or config.get('database.url')
    if not db_url:
        logger.error("Database URL not specified")
        sys.exit(1)
    
    # Create analyzer
    analyzer = PerformanceAnalyzer(
        db_url=db_url,
        config=config,
        verbose=args.verbose
    )
    
    try:
        # Determine which analyses to run
        if args.analyze_all or not any([
            args.analyze_queries, args.analyze_indexes, args.analyze_tables,
            args.analyze_connections, args.analyze_locks, args.analyze_cache,
            args.analyze_vacuum
        ]):
            analyzer.analyze_all()
        else:
            if args.analyze_queries:
                analyzer.analyze_queries()
            if args.analyze_indexes:
                analyzer.analyze_indexes()
            if args.analyze_tables:
                analyzer.analyze_tables()
            if args.analyze_connections:
                analyzer.analyze_connections()
            if args.analyze_locks:
                analyzer.analyze_locks()
            if args.analyze_cache:
                analyzer.analyze_cache()
            if args.analyze_vacuum:
                analyzer.analyze_vacuum()
            
            analyzer.generate_recommendations()
        
        # Output results
        if args.format == 'console':
            analyzer.print_report()
        elif args.output:
            analyzer.save_report(args.output, args.format)
        else:
            analyzer.print_report()
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()