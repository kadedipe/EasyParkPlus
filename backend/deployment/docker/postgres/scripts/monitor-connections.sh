#!/bin/bash
# Monitor PostgreSQL connections

set -e

# Configuration
HOST=${HOST:-localhost}
PORT=${PORT:-5432}
USER=${POSTGRES_USER:-postgres}
DATABASE=${POSTGRES_DB:-parking_db}
INTERVAL=${INTERVAL:-5}
COUNT=${COUNT:-12}

# Monitor connections
monitor_connections() {
    echo "Monitoring PostgreSQL connections every ${INTERVAL}s..."
    echo "Press Ctrl+C to stop"
    echo ""
    
    for i in $(seq 1 $COUNT); do
        echo "=== Snapshot $i/$COUNT at $(date '+%H:%M:%S') ==="
        
        PGPASSWORD=$POSTGRES_PASSWORD psql \
            --host "$HOST" \
            --port "$PORT" \
            --username "$USER" \
            --dbname "$DATABASE" \
            --command "
            SELECT
                datname as database,
                count(*) as connections,
                count(CASE WHEN state = 'active' THEN 1 END) as active,
                count(CASE WHEN state = 'idle' THEN 1 END) as idle,
                count(CASE WHEN state = 'idle in transaction' THEN 1 END) as idle_in_transaction,
                count(CASE WHEN state = 'fastpath function call' THEN 1 END) as fastpath,
                count(CASE WHEN state = 'disabled' THEN 1 END) as disabled
            FROM pg_stat_activity
            WHERE datname IS NOT NULL
            GROUP BY datname
            ORDER BY connections DESC;
            " 2>/dev/null || true
        
        echo ""
        
        if [ $i -lt $COUNT ]; then
            sleep $INTERVAL
        fi
    done
}

# Show blocking queries
show_blocking() {
    echo "=== Blocking Queries ==="
    
    PGPASSWORD=$POSTGRES_PASSWORD psql \
        --host "$HOST" \
        --port "$PORT" \
        --username "$USER" \
        --dbname "$DATABASE" \
        --command "
        SELECT
            blocked_locks.pid AS blocked_pid,
            blocked_activity.usename AS blocked_user,
            blocking_locks.pid AS blocking_pid,
            blocking_activity.usename AS blocking_user,
            blocked_activity.query AS blocked_statement,
            blocking_activity.query AS current_statement_in_blocking_process,
            blocked_activity.application_name AS blocked_application,
            blocking_activity.application_name AS blocking_application
        FROM pg_catalog.pg_locks blocked_locks
        JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
        JOIN pg_catalog.pg_locks blocking_locks 
            ON blocking_locks.locktype = blocked_locks.locktype
            AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
            AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
            AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
            AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
            AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
            AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
            AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
            AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
            AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
            AND blocking_locks.pid != blocked_locks.pid
        JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
        WHERE NOT blocked_locks.GRANTED;
        " 2>/dev/null || true
}

# Main execution
main() {
    case "${1:-}" in
        monitor)
            monitor_connections
            ;;
        blocking)
            show_blocking
            ;;
        *)
            echo "Usage: $0 {monitor|blocking}"
            exit 1
            ;;
    esac
}

main "$@"