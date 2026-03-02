-- lock_monitor.lua
-- Monitoring and debugging tools for distributed locks

-- KEYS[1] = monitor key
-- ARGV[1] = operation: 'record_event', 'get_events', 'get_contention', 'analyze_deadlock'
-- ARGV[2] = parameters (JSON)

local monitor_key = KEYS[1] or 'lock_monitor'
local operation = ARGV[1]
local params = cjson.decode(ARGV[2] or '{}')

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

if operation == 'record_event' then
    -- Record a lock event for monitoring
    local event = {
        timestamp = redis.call('TIME')[1],
        lock_key = params.lock_key,
        owner = params.owner,
        event_type = params.event_type, -- 'acquire', 'release', 'contention', 'timeout'
        duration = params.duration,
        success = params.success,
        metadata = params.metadata
    }
    
    local event_key = monitor_key .. ':events:' .. os.date('%Y%m%d')
    redis.call('LPUSH', event_key, cjson.encode(event))
    redis.call('LTRIM', event_key, 0, 9999) -- Keep last 10000 events
    
    -- Update contention stats if applicable
    if params.event_type == 'contention' then
        local contention_key = monitor_key .. ':contention:' .. params.lock_key
        redis.call('HINCRBY', contention_key, 'total_contentions', 1)
        redis.call('HINCRBY', contention_key, 'total_wait_time', params.duration or 0)
        redis.call('HSET', contention_key, 'last_contention', event.timestamp)
    end
    
    return response(true, 'Event recorded')

elseif operation == 'get_events' then
    -- Get recent lock events
    local date = params.date or os.date('%Y%m%d')
    local limit = params.limit or 100
    local event_key = monitor_key .. ':events:' .. date
    
    local events = redis.call('LRANGE', event_key, 0, limit - 1)
    local decoded = {}
    
    for _, event_json in ipairs(events) do
        table.insert(decoded, cjson.decode(event_json))
    end
    
    return response(true, 'Events retrieved', {
        date = date,
        count = #decoded,
        events = decoded
    })

elseif operation == 'get_contention' then
    -- Get contention statistics for locks
    local pattern = monitor_key .. ':contention:*'
    local cursor = '0'
    local contentions = {}
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', pattern, 'COUNT', 100)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local lock_key = key:match('contention:(.+)')
            local stats = redis.call('HGETALL', key)
            
            contentions[lock_key] = {
                total_contentions = tonumber(stats.total_contentions) or 0,
                total_wait_time = tonumber(stats.total_wait_time) or 0,
                avg_wait_time = (tonumber(stats.total_wait_time) or 0) / (tonumber(stats.total_contentions) or 1),
                last_contention = tonumber(stats.last_contention)
            }
        end
    until cursor == '0'
    
    return response(true, 'Contention stats', {
        locks = contentions,
        total_locks_with_contention = #contentions
    })

elseif operation == 'analyze_deadlock' then
    -- Analyze potential deadlocks
    local wait_graph = {}
    local deadlocks = {}
    
    -- Get all current locks
    local locks = redis.call('KEYS', params.lock_pattern or '*lock*')
    
    -- Build wait-for graph
    for _, lock_key in ipairs(locks) do
        local owner = redis.call('GET', lock_key)
        if owner then
            -- Check what this owner is waiting for
            local waiting_for = redis.call('SMEMBERS', 'waiting:' .. owner)
            wait_graph[owner] = {
                holds = lock_key,
                waiting_for = waiting_for
            }
        end
    end
    
    -- Simple deadlock detection (cycle detection)
    local function detect_cycles(start, visited, stack)
        if stack[start] then
            -- Found a cycle
            local cycle = {}
            local current = start
            repeat
                table.insert(cycle, current)
                current = wait_graph[current] and wait_graph[current].waiting_for[1]
            until current == start
            return cycle
        end
        
        if visited[start] then
            return nil
        end
        
        visited[start] = true
        stack[start] = true
        
        if wait_graph[start] and wait_graph[start].waiting_for then
            for _, waiter in ipairs(wait_graph[start].waiting_for) do
                local cycle = detect_cycles(waiter, visited, stack)
                if cycle then
                    return cycle
                end
            end
        end
        
        stack[start] = nil
        return nil
    end
    
    for owner, _ in pairs(wait_graph) do
        local cycle = detect_cycles(owner, {}, {})
        if cycle then
            table.insert(deadlocks, cycle)
        end
    end
    
    return response(true, 'Deadlock analysis', {
        has_deadlocks = #deadlocks > 0,
        deadlocks = deadlocks,
        wait_graph = wait_graph,
        total_owners = #wait_graph
    })

elseif operation == 'health_check' then
    -- Health check for lock system
    local stats = {
        timestamp = redis.call('TIME')[1],
        total_locks = 0,
        active_locks = 0,
        avg_acquisition_time = 0,
        contention_rate = 0,
        healthy = true,
        issues = {}
    }
    
    -- Count locks
    local locks = redis.call('KEYS', params.lock_pattern or '*lock*')
    stats.total_locks = #locks
    
    for _, lock_key in ipairs(locks) do
        if redis.call('EXISTS', lock_key) > 0 then
            stats.active_locks = stats.active_locks + 1
        end
    end
    
    -- Check for stale locks
    local stale_threshold = params.stale_threshold or 60000 -- 1 minute
    for _, lock_key in ipairs(locks) do
        local ttl = redis.call('PTTL', lock_key)
        if ttl < 0 then
            table.insert(stats.issues, {
                type = 'stale_lock',
                lock = lock_key,
                ttl = ttl
            })
            stats.healthy = false
        end
    end
    
    -- Check memory usage
    local info = redis.call('INFO', 'memory')
    local used_memory = tonumber(info.match('used_memory:(%d+)'))
    if used_memory and used_memory > (params.memory_limit or 1024^3) then
        table.insert(stats.issues, {
            type = 'high_memory',
            used_memory = used_memory
        })
        stats.healthy = false
    end
    
    return response(true, 'Health check', stats)
end

return response(false, 'Unknown operation')