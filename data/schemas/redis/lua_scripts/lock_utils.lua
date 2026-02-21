-- lock_utils.lua
-- Utility functions for lock management

-- KEYS[1] = lock key
-- ARGV[1] = operation
-- ARGV[2] = parameters (JSON)

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

local operation = ARGV[1]
local params = cjson.decode(ARGV[2] or '{}')

if operation == 'get_ttl' then
    -- Get TTL for a lock
    local ttl = redis.call('PTTL', KEYS[1])
    local owner = redis.call('GET', KEYS[1])
    
    return response(true, 'TTL retrieved', {
        key = KEYS[1],
        owner = owner,
        ttl = ttl,
        expired = ttl <= 0
    })

elseif operation == 'wait_for_lock' then
    -- Wait for lock to be released with timeout
    local timeout = params.timeout or 5000
    local check_interval = params.interval or 100
    local start_time = redis.call('TIME')[1] * 1000
    
    while true do
        local owner = redis.call('GET', KEYS[1])
        if not owner then
            return response(true, 'Lock is free')
        end
        
        local elapsed = (redis.call('TIME')[1] * 1000) - start_time
        if elapsed >= timeout then
            return response(false, 'Timeout waiting for lock', {
                owner = owner,
                elapsed = elapsed,
                timeout = timeout
            })
        end
        
        -- Use Redis to sleep
        redis.call('PEXPIRE', 'lock_utils:sleep', check_interval)
    end

elseif operation == 'lock_info' then
    -- Get detailed lock information
    local owner = redis.call('GET', KEYS[1])
    local ttl = redis.call('PTTL', KEYS[1])
    local metadata = redis.call('HGETALL', KEYS[1] .. ':meta')
    
    return response(true, 'Lock info retrieved', {
        key = KEYS[1],
        owner = owner,
        ttl = ttl,
        metadata = metadata,
        is_locked = owner and true or false
    })

elseif operation == 'safe_release' then
    -- Safely release lock only if it matches expected value
    local expected_owner = params.expected_owner
    local current = redis.call('GET', KEYS[1])
    
    if current == expected_owner then
        redis.call('DEL', KEYS[1])
        return response(true, 'Lock released')
    elseif current then
        return response(false, 'Lock owner mismatch', {
            expected = expected_owner,
            actual = current
        })
    else
        return response(false, 'Lock already released')
    end

elseif operation == 'lock_pattern' then
    -- Get all locks matching a pattern
    local pattern = params.pattern or '*'
    local cursor = '0'
    local locks = {}
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', pattern, 'COUNT', 100)
        cursor = result[1]
        for _, key in ipairs(result[2]) do
            local owner = redis.call('GET', key)
            if owner then
                table.insert(locks, {
                    key = key,
                    owner = owner,
                    ttl = redis.call('PTTL', key)
                })
            end
        end
    until cursor == '0'
    
    return response(true, 'Locks retrieved', {
        count = #locks,
        locks = locks
    })

elseif operation == 'lock_stats' then
    -- Get statistics about locks
    local stats = {
        total_keys = 0,
        locked_keys = 0,
        owners = {},
        avg_ttl = 0,
        min_ttl = nil,
        max_ttl = 0
    }
    
    local cursor = '0'
    local total_ttl = 0
    local ttl_count = 0
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', params.pattern or '*lock*', 'COUNT', 1000)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            stats.total_keys = stats.total_keys + 1
            
            local owner = redis.call('GET', key)
            if owner then
                stats.locked_keys = stats.locked_keys + 1
                stats.owners[owner] = (stats.owners[owner] or 0) + 1
                
                local ttl = redis.call('PTTL', key)
                if ttl > 0 then
                    total_ttl = total_ttl + ttl
                    ttl_count = ttl_count + 1
                    
                    if stats.min_ttl is None or ttl < stats.min_ttl then
                        stats.min_ttl = ttl
                    end
                    if ttl > stats.max_ttl then
                        stats.max_ttl = ttl
                    end
                end
            end
        end
    until cursor == '0'
    
    if ttl_count > 0 then
        stats.avg_ttl = total_ttl / ttl_count
    end
    
    return response(true, 'Lock statistics', stats)

elseif operation == 'cleanup_stale' then
    -- Clean up stale locks (with expired TTL but still present)
    local cleaned = 0
    local cursor = '0'
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', params.pattern or '*lock*', 'COUNT', 100)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local ttl = redis.call('PTTL', key)
            if ttl <= 0 then
                -- Key exists but TTL expired, delete it
                redis.call('DEL', key)
                cleaned = cleaned + 1
            end
        end
    until cursor == '0'
    
    return response(true, 'Stale locks cleaned', {
        cleaned = cleaned
    })
end

return response(false, 'Unknown operation')