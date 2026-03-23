# parking-management/backend/scripts/maintenance/cache/clear.sh
# Cache clearing and management

run_cache_maintenance() {
    log_info "Starting cache maintenance..."
    
    # Check cache usage
    if ! check_cache_usage; then
        log_warning "Cache usage check failed"
    fi
    
    # Clear Redis cache if needed
    if should_clear_redis_cache; then
        clear_redis_cache
    fi
    
    # Clear application cache
    clear_application_cache
    
    # Clear CDN cache if configured
    if [ -n "${CDN_PURGE_URL}" ]; then
        clear_cdn_cache
    fi
    
    # Clear session cache
    clear_session_cache
    
    # Optimize cache settings
    optimize_cache_settings
    
    log_success "Cache maintenance completed"
    return 0
}

check_cache_usage() {
    log_info "Checking Redis cache usage..."
    
    if ! command -v redis-cli &> /dev/null; then
        log_warning "redis-cli not found"
        return 1
    fi
    
    local used_memory=$(redis-cli INFO memory | grep "used_memory_human" | cut -d':' -f2 | xargs)
    local max_memory=$(redis-cli CONFIG GET maxmemory | tail -n1)
    
    if [ -n "${max_memory}" ] && [ "${max_memory}" != "0" ]; then
        local used_bytes=$(redis-cli INFO memory | grep "used_memory" | head -n1 | cut -d':' -f2 | xargs)
        local usage_percent=$((used_bytes * 100 / max_memory))
        
        log_info "Redis usage: ${used_memory} / $(numfmt --to=iec ${max_memory}) (${usage_percent}%)"
        
        if [ ${usage_percent} -gt ${CACHE_CLEAR_BEFORE_PERCENT} ]; then
            log_warning "Redis usage above threshold (${usage_percent}%)"
            return 1
        fi
    else
        log_info "Redis memory limit not set"
    fi
    
    return 0
}

should_clear_redis_cache() {
    if [ "${FORCE}" = "true" ]; then
        return 0
    fi
    
    # Check if Redis usage is above threshold
    if ! check_cache_usage; then
        return 0
    fi
    
    # Check if cache has stale data
    local stale_keys=$(redis-cli KEYS "*:stale" 2>/dev/null | wc -l)
    if [ ${stale_keys} -gt 1000 ]; then
        log_info "Found ${stale_keys} stale keys"
        return 0
    fi
    
    return 1
}

clear_redis_cache() {
    log_info "Clearing Redis cache..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would clear Redis cache"
        return 0
    fi
    
    # Get cache size before clearing
    local before_size=$(redis-cli DBSIZE 2>/dev/null)
    log_info "Cache entries before: ${before_size}"
    
    # Clear specific patterns (preserve sessions if needed)
    local patterns=(
        "cache:*"
        "view:*"
        "query:*"
        "session:*:expired"
    )
    
    for pattern in "${patterns[@]}"; do
        redis-cli --scan --pattern "${pattern}" 2>/dev/null | \
            while read key; do
                redis-cli DEL "${key}" 2>/dev/null
            done
    done
    
    # Alternative: flush entire database (careful!)
    if [ "${FORCE}" = "true" ]; then
        log_warning "Flushing entire Redis database"
        redis-cli FLUSHDB 2>/dev/null
    fi
    
    local after_size=$(redis-cli DBSIZE 2>/dev/null)
    local removed=$((before_size - after_size))
    
    log_success "Cleared ${removed} cache entries"
    return 0
}

clear_application_cache() {
    log_info "Clearing application cache..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would clear application cache"
        return 0
    fi
    
    # Clear Node.js module cache (if application is running)
    if is_application_running && [ -f "${CURRENT_DIR}/scripts/clear-cache.js" ]; then
        cd "${CURRENT_DIR}" || return 1
        node scripts/clear-cache.js 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/cache_clear.log"
    fi
    
    # Clear temp files
    rm -rf "${CURRENT_DIR}/tmp/*" 2>/dev/null || true
    
    # Clear upload temp files
    find "${SHARED_DIR}/uploads/temp" -type f -mtime +1 -delete 2>/dev/null || true
    
    log_success "Application cache cleared"
    return 0
}

clear_cdn_cache() {
    log_info "Clearing CDN cache..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would clear CDN cache"
        return 0
    fi
    
    # Fastly CDN
    if [ -n "${FASTLY_SERVICE_ID}" ] && [ -n "${FASTLY_API_KEY}" ]; then
        curl -X POST -H "Fastly-Key: ${FASTLY_API_KEY}" \
            "https://api.fastly.com/service/${FASTLY_SERVICE_ID}/purge_all" \
            2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/cdn_clear.log"
    fi
    
    # CloudFlare
    if [ -n "${CLOUDFLARE_ZONE_ID}" ] && [ -n "${CLOUDFLARE_API_TOKEN}" ]; then
        curl -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/purge_cache" \
            -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
            -H "Content-Type: application/json" \
            --data '{"purge_everything":true}' \
            2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/cdn_clear.log"
    fi
    
    log_success "CDN cache cleared"
    return 0
}

clear_session_cache() {
    log_info "Clearing expired sessions..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would clear expired sessions"
        return 0
    fi
    
    # Clear expired sessions from Redis
    if command -v redis-cli &> /dev/null; then
        redis-cli --scan --pattern "session:*" 2>/dev/null | \
            while read key; do
                local ttl=$(redis-cli TTL "${key}" 2>/dev/null)
                if [ "${ttl}" -eq -2 ] || [ "${ttl}" -eq -1 ]; then
                    redis-cli DEL "${key}" 2>/dev/null
                fi
            done
    fi
    
    log_success "Expired sessions cleared"
    return 0
}

optimize_cache_settings() {
    log_info "Optimizing cache settings..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would optimize cache settings"
        return 0
    fi
    
    if command -v redis-cli &> /dev/null; then
        # Set max memory if not set
        local max_memory=$(redis-cli CONFIG GET maxmemory | tail -n1)
        if [ "${max_memory}" = "0" ]; then
            redis-cli CONFIG SET maxmemory "${REDIS_MAX_MEMORY_MB}mb" 2>/dev/null
            log_info "Set Redis max memory to ${REDIS_MAX_MEMORY_MB}MB"
        fi
        
        # Set eviction policy
        local current_policy=$(redis-cli CONFIG GET maxmemory-policy | tail -n1)
        if [ "${current_policy}" != "${REDIS_EVICTION_POLICY}" ]; then
            redis-cli CONFIG SET maxmemory-policy "${REDIS_EVICTION_POLICY}" 2>/dev/null
            log_info "Set Redis eviction policy to ${REDIS_EVICTION_POLICY}"
        fi
    fi
    
    return 0
}