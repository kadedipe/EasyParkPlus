-- reentrant_lock.lua
-- Reentrant lock that allows the same owner to acquire multiple times

-- KEYS[1] = lock key
-- KEYS[2] = counter key (for reentrancy count)
-- ARGV[1] = lock owner identifier
-- ARGV[2] = lock timeout in milliseconds
-- ARGV[3] = current timestamp
-- ARGV[4] = operation: 'acquire', 'release', 'get_count'

local lock_key = KEYS[1]
local counter_key = KEYS[2] or (lock_key .. ':count')
local owner = ARGV[1]
local timeout = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local operation = ARGV[4]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

if operation == 'acquire' then
    -- Check current lock owner
    local current = redis.call('GET', lock_key)
    
    if not current then
        -- Lock is free, acquire it
        redis.call('SET', lock_key, owner, 'PX', timeout)
        redis.call('SET', counter_key, 1, 'PX', timeout)
        return response(true, 'Lock acquired', {count = 1})
        
    elseif current == owner then
        -- Already own the lock, increment counter
        local count = redis.call('INCR', counter_key)
        -- Refresh expiration
        redis.call('PEXPIRE', lock_key, timeout)
        redis.call('PEXPIRE', counter_key, timeout)
        return response(true, 'Lock re-acquired', {count = count})
        
    else
        -- Lock held by someone else
        local ttl = redis.call('PTTL', lock_key)
        return response(false, 'Lock held by another', {
            owner = current,
            ttl = ttl
        })
    end

elseif operation == 'release' then
    local current = redis.call('GET', lock_key)
    
    if not current then
        return response(false, 'Lock does not exist')
    end
    
    if current ~= owner then
        return response(false, 'Cannot release lock owned by another', {
            current_owner = current
        })
    end
    
    local count = redis.call('DECR', counter_key)
    
    if count <= 0 then
        -- Last release, delete the lock
        redis.call('DEL', lock_key, counter_key)
        return response(true, 'Lock fully released', {count = 0})
    else
        -- Still have remaining reentrant locks
        -- Refresh expiration
        redis.call('PEXPIRE', lock_key, timeout)
        redis.call('PEXPIRE', counter_key, timeout)
        return response(true, 'Lock released (reentrant)', {count = count})
    end

elseif operation == 'get_count' then
    local current = redis.call('GET', lock_key)
    local count = tonumber(redis.call('GET', counter_key)) or 0
    
    if current == owner then
        return response(true, 'Lock count retrieved', {
            owner = current,
            count = count
        })
    elseif current then
        return response(false, 'Lock held by another', {
            owner = current,
            count = count
        })
    else
        return response(false, 'Lock is free', {count = 0})
    end
end

return response(false, 'Unknown operation')