-- session_cleanup.lua
-- Manages cleanup of expired sessions and related data

-- KEYS[1] = cleanup log key
-- KEYS[2] = stats key
-- ARGV[1] = operation: 'cleanup_expired', 'archive_old', 'vacuum', 'get_stats', 'schedule_cleanup'
-- ARGV[2] = parameters (JSON string)
-- ARGV[3] = current timestamp

local cleanup_key = KEYS[1] or 'cleanup:log'
local stats_key = KEYS[2] or 'cleanup:stats'
local operation = ARGV[1]
local params = cjson.decode(ARGV[2] or '{}')
local now = tonumber(ARGV[3]) or redis.call('TIME')[1]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Helper to log cleanup actions
local function log_cleanup(action, details, count)
    local log_entry = {
        timestamp = now,
        action = action,
        details = details,
        count = count,
        duration = 0
    }
    
    redis.call('LPUSH', cleanup_key, cjson.encode(log_entry))
    redis.call('LTRIM', cleanup_key, 0, 999) -- Keep last 1000 entries
end

if operation == 'cleanup_expired' then
    local start_time = redis.call('TIME')[1] * 1000
    local cleaned = {
        sessions = 0,
        tokens = 0,
        activity = 0,
        temp_data = 0
    }
    
    -- 1. Clean up expired user sessions
    local session_pattern = params.session_pattern or 'session:user:*'
    local cursor = '0'
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', session_pattern, 'COUNT', 1000)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local ttl = redis.call('PTTL', key)
            if ttl < 0 then
                -- Key exists but no TTL or expired
                redis.call('DEL', key)
                cleaned.sessions = cleaned.sessions + 1
            end
        end
    until cursor == '0'
    
    -- 2. Clean up expired tokens
    local token_pattern = params.token_pattern or 'token:*'
    cursor = '0'
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', token_pattern, 'COUNT', 1000)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local ttl = redis.call('PTTL', key)
            if ttl < 0 then
                redis.call('DEL', key)
                cleaned.tokens = cleaned.tokens + 1
            end
        end
    until cursor == '0'
    
    -- 3. Clean up expired activity data
    local activity_pattern = params.activity_pattern or 'activity:*'
    local threshold = now - (params.activity_retention_days or 7) * 86400
    
    cursor = '0'
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', activity_pattern, 'COUNT', 1000)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            if string.match(key, 'detail:') then
                -- Check timestamp in the data
                local data = redis.call('GET', key)
                if data then
                    local parsed = cjson.decode(data)
                    if parsed.timestamp and parsed.timestamp < threshold then
                        redis.call('DEL', key)
                        cleaned.activity = cleaned.activity + 1
                    end
                end
            elseif string.match(key, 'ZSET') then
                -- Remove old entries from sorted sets
                local removed = redis.call('ZREMRANGEBYSCORE', key, '-inf', threshold)
                cleaned.activity = cleaned.activity + removed
            end
        end
    until cursor == '0'
    
    -- 4. Clean up temporary data
    local temp_pattern = params.temp_pattern or 'temp:*'
    cursor = '0'
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', temp_pattern, 'COUNT', 1000)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local ttl = redis.call('PTTL', key)
            if ttl < 0 then
                redis.call('DEL', key)
                cleaned.temp_data = cleaned.temp_data + 1
            end
        end
    until cursor == '0'
    
    -- 5. Clean up orphaned session references
    local orphaned = 0
    local session_sets = redis.call('KEYS', 'user:*:sessions')
    
    for _, set_key in ipairs(session_sets) do
        local sessions = redis.call('SMEMBERS', set_key)
        for _, sess_id in ipairs(sessions) do
            local exists = redis.call('EXISTS', 'session:user:' .. sess_id)
            if exists == 0 then
                redis.call('SREM', set_key, sess_id)
                orphaned = orphaned + 1
            end
        end
    end
    
    cleaned.orphaned = orphaned
    
    local duration = (redis.call('TIME')[1] * 1000) - start_time
    
    -- Log cleanup
    log_cleanup('expired_cleanup', cleaned, cleaned.sessions + cleaned.tokens + cleaned.activity + cleaned.temp_data + orphaned)
    
    -- Update stats
    redis.call('HINCRBY', stats_key, 'total_cleanups', 1)
    redis.call('HINCRBY', stats_key, 'total_items_cleaned', cleaned.sessions + cleaned.tokens + cleaned.activity + cleaned.temp_data + orphaned)
    redis.call('HSET', stats_key, 'last_cleanup', now)
    
    return response(true, 'Cleanup completed', {
        cleaned = cleaned,
        duration_ms = duration,
        timestamp = now
    })

elseif operation == 'archive_old' then
    local archive_key = params.archive_key or 'archive:sessions'
    local age_threshold = params.age_days or 30
    local threshold = now - (age_threshold * 86400)
    local batch_size = params.batch_size or 100
    
    local archived = 0
    local cursor = '0'
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', 'parking:session:*', 'COUNT', batch_size)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local session_json = redis.call('GET', key)
            if session_json then
                local session = cjson.decode(session_json)
                if session.exit_time and session.exit_time < threshold then
                    -- Move to archive
                    redis.call('HSET', archive_key, key, session_json)
                    redis.call('DEL', key)
                    archived = archived + 1
                end
            end
        end
    until cursor == '0' or archived >= (params.max_archive or 10000)
    
    log_cleanup('archive_old', {age_days = age_threshold, archived = archived}, archived)
    
    return response(true, 'Archive completed', {
        archived = archived,
        archive_key = archive_key
    })

elseif operation == 'vacuum' then
    -- Reclaim memory by removing fragmented data
    local start_memory = tonumber(redis.call('INFO', 'memory')['used_memory'])
    local reclaimed = 0
    
    -- 1. Remove empty sorted sets
    local zset_pattern = params.zset_pattern or '*'
    cursor = '0'
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', zset_pattern, 'TYPE', 'zset', 'COUNT', 1000)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local size = redis.call('ZCARD', key)
            if size == 0 then
                redis.call('DEL', key)
                reclaimed = reclaimed + 1
            end
        end
    until cursor == '0'
    
    -- 2. Remove empty sets
    cursor = '0'
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', '*', 'TYPE', 'set', 'COUNT', 1000)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local size = redis.call('SCARD', key)
            if size == 0 then
                redis.call('DEL', key)
                reclaimed = reclaimed + 1
            end
        end
    until cursor == '0'
    
    -- 3. Remove empty hashes
    cursor = '0'
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', '*', 'TYPE', 'hash', 'COUNT', 1000)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local size = redis.call('HLEN', key)
            if size == 0 then
                redis.call('DEL', key)
                reclaimed = reclaimed + 1
            end
        end
    until cursor == '0'
    
    local end_memory = tonumber(redis.call('INFO', 'memory')['used_memory'])
    local memory_freed = start_memory - end_memory
    
    log_cleanup('vacuum', {reclaimed = reclaimed, memory_freed = memory_freed}, reclaimed)
    
    return response(true, 'Vacuum completed', {
        reclaimed_keys = reclaimed,
        memory_freed = memory_freed,
        start_memory = start_memory,
        end_memory = end_memory
    })

elseif operation == 'get_stats' then
    local stats = redis.call('HGETALL', stats_key)
    local recent_cleanups = redis.call('LRANGE', cleanup_key, 0, 9)
    local parsed_cleanups = {}
    
    for _, entry in ipairs(recent_cleanups) do
        table.insert(parsed_cleanups, cjson.decode(entry))
    end
    
    return response(true, 'Cleanup stats retrieved', {
        stats = stats,
        recent_cleanups = parsed_cleanups,
        total_cleanups = #parsed_cleanups
    })

elseif operation == 'schedule_cleanup' then
    -- Schedule periodic cleanup (would be called by external scheduler)
    local schedule = params.schedule or {}
    local next_run = schedule.interval or 3600 -- Default 1 hour
    
    redis.call('HSET', stats_key, 'next_scheduled', now + next_run)
    redis.call('HSET', stats_key, 'schedule', cjson.encode(schedule))
    
    return response(true, 'Cleanup scheduled', {
        next_run = now + next_run,
        interval = next_run
    })
end

return response(false, 'Unknown operation')