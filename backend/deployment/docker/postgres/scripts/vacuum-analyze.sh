#!/bin/bash
# Vacuum and analyze script for PostgreSQL

set -e

# Configuration
HOST=${HOST:-localhost}
PORT=${PORT:-5432}
USER=${POSTGRES_USER:-postgres}
DATABASE=${POSTGRES_DB:-parking_db}
LOG_FILE="/var/log/postgresql/vacuum.log"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Run vacuum analyze on all tables
run_vacuum_analyze() {
    log "Starting VACUUM ANALYZE on database: $DATABASE"
    
    PGPASSWORD=$POSTGRES_PASSWORD vacuumdb \
        --host "$HOST" \
        --port "$PORT" \
        --username "$USER" \
        --dbname "$DATABASE" \
        --analyze \
        --verbose 2>&1 | tee -a "$LOG_FILE"
    
    log "VACUUM ANALYZE completed"
}

# Run reindex on database
run_reindex() {
    log "Starting REINDEX on database: $DATABASE"
    
    PGPASSWORD=$POSTGRES_PASSWORD psql \
        --host "$HOST" \
        --port "$PORT" \
        --username "$USER" \
        --dbname "$DATABASE" \
        --command "REINDEX DATABASE $DATABASE;" 2>&1 | tee -a "$LOG_FILE"
    
    log "REINDEX completed"
}

# Check for bloated tables
check_bloat() {
    log "Checking for table bloat..."
    
    PGPASSWORD=$POSTGRES_PASSWORD psql \
        --host "$HOST" \
        --port "$PORT" \
        --username "$USER" \
        --dbname "$DATABASE" \
        --command "
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as total_size,
            pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) as table_size,
            pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename) - pg_relation_size(schemaname || '.' || tablename)) as index_size,
            n_dead_tup as dead_tuples,
            n_live_tup as live_tuples,
            round((n_dead_tup::numeric / (n_live_tup + n_dead_tup) * 100), 2) as dead_tuple_percent
        FROM pg_stat_user_tables
        WHERE n_dead_tup > 1000
        ORDER BY dead_tuple_percent DESC
        LIMIT 10;
        " 2>&1 | tee -a "$LOG_FILE"
}

# Main execution
main() {
    case "${1:-}" in
        vacuum)
            run_vacuum_analyze
            ;;
        reindex)
            run_reindex
            ;;
        bloat)
            check_bloat
            ;;
        all)
            run_vacuum_analyze
            run_reindex
            check_bloat
            ;;
        *)
            echo "Usage: $0 {vacuum|reindex|bloat|all}"
            exit 1
            ;;
    esac
}

main "$@"