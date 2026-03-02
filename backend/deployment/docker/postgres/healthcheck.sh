#!/bin/bash
# Enhanced PostgreSQL Health Check Script
# Returns 0 if healthy, 1 if unhealthy

set -e

# Configuration
HOST=${HOST:-localhost}
PORT=${PORT:-5432}
USER=${POSTGRES_USER:-parking_user}
DATABASE=${POSTGRES_DB:-parking_db}
TIMEOUT=${TIMEOUT:-10}
MAX_CONNECTIONS_PERCENT=${MAX_CONNECTIONS_PERCENT:-80}

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if PostgreSQL is running
check_postgres_running() {
    log "Checking if PostgreSQL is running..."
    if pg_isready -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t "$TIMEOUT" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is running${NC}"
        return 0
    else
        echo -e "${RED}✗ PostgreSQL is not running${NC}"
        return 1
    fi
}

# Check connection count
check_connections() {
    log "Checking connection count..."
    local max_connections=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -c "SHOW max_connections;" 2>/dev/null | tr -d ' ')
    local current_connections=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = '$DATABASE';" 2>/dev/null | tr -d ' ')
    
    if [ -z "$max_connections" ] || [ -z "$current_connections" ]; then
        echo -e "${YELLOW}⚠ Could not retrieve connection information${NC}"
        return 2
    fi
    
    local percent=$((current_connections * 100 / max_connections))
    
    if [ "$percent" -lt "$MAX_CONNECTIONS_PERCENT" ]; then
        echo -e "${GREEN}✓ Connections: $current_connections/$max_connections ($percent%)${NC}"
        return 0
    else
        echo -e "${RED}✗ High connection usage: $current_connections/$max_connections ($percent%)${NC}"
        return 1
    fi
}

# Check replication status (if applicable)
check_replication() {
    log "Checking replication status..."
    local replication_status=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -c "SELECT pg_is_in_recovery();" 2>/dev/null | tr -d ' ')
    
    if [ "$replication_status" = "f" ]; then
        echo -e "${GREEN}✓ Primary database (not in recovery)${NC}"
        
        # Check for replication slots if primary
        local replication_slots=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -c "SELECT count(*) FROM pg_replication_slots WHERE active = true;" 2>/dev/null | tr -d ' ')
        echo -e "${GREEN}✓ Active replication slots: $replication_slots${NC}"
        
    elif [ "$replication_status" = "t" ]; then
        echo -e "${YELLOW}⚠ Standby database (in recovery)${NC}"
        
        # Check replication lag if standby
        local lag=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -c "SELECT EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())::INT;" 2>/dev/null | tr -d ' ')
        if [ -n "$lag" ] && [ "$lag" -lt 60 ]; then
            echo -e "${GREEN}✓ Replication lag: ${lag}s${NC}"
        elif [ -n "$lag" ]; then
            echo -e "${YELLOW}⚠ High replication lag: ${lag}s${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Could not determine replication status${NC}"
    fi
}

# Check database size and growth
check_database_size() {
    log "Checking database size..."
    local size=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -c "SELECT pg_size_pretty(pg_database_size('$DATABASE'));" 2>/dev/null | tr -d ' ')
    
    if [ -n "$size" ]; then
        echo -e "${GREEN}✓ Database size: $size${NC}"
    else
        echo -e "${YELLOW}⚠ Could not retrieve database size${NC}"
    fi
}

# Check for long-running transactions
check_long_running_transactions() {
    log "Checking for long-running transactions..."
    local long_tx=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';" 2>/dev/null | tr -d ' ')
    
    if [ -n "$long_tx" ] && [ "$long_tx" -eq 0 ]; then
        echo -e "${GREEN}✓ No long-running transactions${NC}"
    elif [ -n "$long_tx" ]; then
        echo -e "${YELLOW}⚠ Long-running transactions: $long_tx${NC}"
    else
        echo -e "${YELLOW}⚠ Could not check long-running transactions${NC}"
    fi
}

# Check for deadlocks
check_deadlocks() {
    log "Checking for deadlocks..."
    local deadlocks=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -c "SELECT deadlocks FROM pg_stat_database WHERE datname = '$DATABASE';" 2>/dev/null | tr -d ' ')
    
    if [ -n "$deadlocks" ]; then
        echo -e "${GREEN}✓ Deadlocks count: $deadlocks${NC}"
    else
        echo -e "${YELLOW}⚠ Could not retrieve deadlock count${NC}"
    fi
}

# Check disk space
check_disk_space() {
    log "Checking disk space..."
    local data_dir=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -c "SHOW data_directory;" 2>/dev/null | tr -d ' ')
    
    if [ -n "$data_dir" ]; then
        local disk_usage=$(df -h "$data_dir" | tail -1 | awk '{print $5}' | sed 's/%//')
        if [ "$disk_usage" -lt 90 ]; then
            echo -e "${GREEN}✓ Disk usage: ${disk_usage}%${NC}"
        else
            echo -e "${RED}✗ High disk usage: ${disk_usage}%${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ Could not check disk space${NC}"
    fi
}

# Main health check
main() {
    log "Starting PostgreSQL health check..."
    
    # Track overall health
    local overall_health=0
    
    # Run all checks
    check_postgres_running || overall_health=1
    check_connections || overall_health=1
    check_replication
    check_database_size
    check_long_running_transactions
    check_deadlocks
    check_disk_space || overall_health=1
    
    # Final status
    if [ $overall_health -eq 0 ]; then
        log "✅ PostgreSQL is healthy"
        exit 0
    else
        log "❌ PostgreSQL health check failed"
        exit 1
    fi
}

# Execute main function
main "$@"