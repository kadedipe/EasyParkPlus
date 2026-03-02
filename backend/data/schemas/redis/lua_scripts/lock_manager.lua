-- lock_manager.lua
-- Centralized lock manager for monitoring and managing all locks

-- KEYS[1] = locks hash key
-- KEYS[2] = owners set key
-- KEYS[3] = stats key
-- ARGV[1] = operation: 'register', 'unregister', 'list', 'stats', 'cleanup', 'force_release'
-- ARGV[2] = lock key (for specific operations)
-- ARGV[3] = owner (for specific operations)
-- ARGV[4] = current timestamp
-- ARGV[5] = timeout threshold (for cleanup)

local locks_key = KEYS[1] or 'lock_manager:locks'
local owners_key = KEYS[2] or 'lock_manager:owners'
local stats_key = KEYS[3] or 'lock_manager:stats'
local operation = ARGV[1]
local target_lock = ARGV[2]
local target_owner = ARGV[3]
local now = tonumber(ARGV[4])
local timeout_threshold = tonumber(ARGV[5]) or 30000 -- 30 seconds

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

if operation == 'register' then
    -- Register a lock acquisition
    if not target_lock or not target_owner then
        return response(false, 'Lock and owner required')
    end
    
    local lock_info = {
        owner = target_owner,
        acquired_at = now,
        last_heartbeat = now,
        timeout = timeout_threshold,
        status = 'active'
    }
    
    redis.call('HSET', locks_key, target_lock, cjson.encode(lock_info))
    redis.call('SADD', owners_key .. ':' .. target_owner, target_lock)
    
    -- Update stats
    redis.call('HINCRBY', stats_key, 'total_locks', 1)
    redis.call('HINCRBY', stats_key, 'active_locks', 1)
    redis.call('HSET', stats_key, 'last_activity', now)
    
    return response(true, 'Lock registered', lock_info)

elseif operation == 'unregister' then
    -- Unregister a lock release
    if not target_lock then
        return response(false, 'Lock required')
    end
    
    local lock_json = redis.call('HGET', locks_key, target_lock)
    if lock_json then
        local lock_info = cjson.decode(lock_json)
        
        redis.call('HDEL', locks_key, target_lock)
        redis.call('SREM', owners_key .. ':' .. lock_info.owner, target_lock)
        
        -- Update stats
        redis.call('HINCRBY', stats_key, 'active_locks', -1)
        redis.call('HINCRBY', stats_key, 'total_releases', 1)
        
        return response(true, 'Lock unregistered', lock_info)
    else
        return response(false, 'Lock not found')
    end

elseif operation == 'list' then
    -- List all locks or locks for specific owner
    local locks = {}
    
    if target_owner then
        -- List locks for specific owner
        local owner_locks = redis.call('SMEMBERS', owners_key .. ':' .. target_owner)
        for _, lock_key in ipairs(owner_locks) do
            local lock_json = redis.call('HGET', locks_key, lock_key)
            if lock_json then
                locks[lock_key] = cjson.decode(lock_json)
            end
        end
    else
        -- List all locks
        local all_locks = redis.call('HGETALL', locks_key)
        for i = 1, #all_locks, 2 do
            locks[all_locks[i]] = cjson.decode(all_locks[i+1])
        end
    end
    
    return response(true, 'Locks retrieved', {
        count = #locks,
        locks = locks
    })

elseif operation == 'stats' then
    -- Get lock manager statistics
    local stats = redis.call('HGETALL', stats_key)
    
    -- Add derived stats
    local active_locks = redis.call('HLEN', locks_key)
    local unique_owners = 0
    
    -- Count unique owners
    local owner_keys = redis.call('KEYS', owners_key .. ':*')
    for _, key in ipairs(owner_keys) do
        if redis.call('SCARD', key) > 0 then
            unique_owners = unique_owners + 1
        end
    end
    
    stats['current_active_locks'] = active_locks
    stats['unique_owners'] = unique_owners
    stats['timestamp'] = now
    
    return response(true, 'Stats retrieved', stats)

elseif operation == 'cleanup' then
    -- Clean up expired/stale locks
    local cleaned = {}
    local all_locks = redis.call('HGETALL', locks_key)
    
    for i = 1, #all_locks, 2 do
        local lock_key = all_locks[i]
        local lock_info = cjson.decode(all_locks[i+1])
        
        -- Check if lock is expired
        if now - lock_info.last_heartbeat > lock_info.timeout then
            -- Lock is stale, clean it up
            redis.call('HDEL', locks_key, lock_key)
            redis.call('SREM', owners_key .. ':' .. lock_info.owner, lock_key)
            
            table.insert(cleaned, {
                lock = lock_key,
                owner = lock_info.owner,
                reason = 'timeout',
                age = now - lock_info.last_heartbeat
            })
        end
    end
    
    -- Update stats
    redis.call('HINCRBY', stats_key, 'cleaned_locks', #cleaned)
    redis.call('HSET', stats_key, 'last_cleanup', now)
    
    return response(true, 'Cleanup completed', {
        cleaned_count = #cleaned,
        cleaned = cleaned
    })

elseif operation == 'force_release' then
    -- Force release a specific lock (admin operation)
    if not target_lock then
        return response(false, 'Lock required')
    end
    
    local lock_json = redis.call('HGET', locks_key, target_lock)
    if lock_json then
        local lock_info = cjson.decode(lock_json)
        
        -- Actually delete the lock in Redis
        redis.call('DEL', target_lock)
        
        -- Remove from manager
        redis.call('HDEL', locks_key, target_lock)
        redis.call('SREM', owners_key .. ':' .. lock_info.owner, target_lock)
        
        -- Update stats
        redis.call('HINCRBY', stats_key, 'force_released', 1)
        
        return response(true, 'Lock force released', lock_info)
    else
        return response(false, 'Lock not found')
    end

elseif operation == 'heartbeat' then
    -- Update heartbeat for a lock
    if not target_lock or not target_owner then
        return response(false, 'Lock and owner required')
    end
    
    local lock_json = redis.call('HGET', locks_key, target_lock)
    if lock_json then
        local lock_info = cjson.decode(lock_json)
        
        if lock_info.owner == target_owner then
            lock_info.last_heartbeat = now
            redis.call('HSET', locks_key, target_lock, cjson.encode(lock_info))
            
            -- Update actual Redis lock TTL
            redis.call('PEXPIRE', target_lock, lock_info.timeout)
            
            return response(true, 'Heartbeat updated', {
                lock = target_lock,
                last_heartbeat = now
            })
        else
            return response(false, 'Not lock owner')
        end
    else
        return response(false, 'Lock not found')
    end
end

return response(false, 'Unknown operation')