-- redlock.lua
-- RedLock algorithm implementation for distributed locking across multiple Redis instances
-- Note: This script runs on each Redis instance independently

-- KEYS[1] = lock key
-- ARGV[1] = resource name (for consistent hashing)
-- ARGV[2] = owner identifier
-- ARGV[3] = lock timeout in milliseconds
-- ARGV[4] = current timestamp
-- ARGV[5] = operation: 'acquire', 'release', 'validate'
-- ARGV[6] = quorum size (for validation)

local lock_key = KEYS[1]
local resource = ARGV[1]
local owner = ARGV[2]
local timeout = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local operation = ARGV[5]
local quorum = tonumber(ARGV[6]) or 3

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

if operation == 'acquire' then
    -- Try to acquire the lock with timeout
    local result = redis.call('SET', lock_key, owner, 'NX', 'PX', timeout)
    
    if result then
        -- Lock acquired, store metadata
        redis.call('HMSET', lock_key .. ':meta',
            'owner', owner,
            'resource', resource,
            'acquired_at', now,
            'timeout', timeout,
            'instance', server.id or 'unknown'
        )
        redis.call('PEXPIRE', lock_key .. ':meta', timeout)
        
        return response(true, 'Lock acquired', {
            owner = owner,
            validity = timeout,
            acquired_at = now,
            expires_at = now + timeout
        })
    else
        -- Lock not acquired
        local current_owner = redis.call('GET', lock_key)
        local ttl = redis.call('PTTL', lock_key)
        
        return response(false, 'Lock not acquired', {
            current_owner = current_owner,
            ttl = ttl,
            retry_after = ttl
        })
    end

elseif operation == 'release' then
    -- Only release if we are the owner (prevent releasing locks owned by others)
    local current = redis.call('GET', lock_key)
    
    if current == owner then
        -- Delete the lock and metadata
        redis.call('DEL', lock_key, lock_key .. ':meta')
        
        -- Record release for audit
        redis.call('RPUSH', 'redlock:audit', cjson.encode({
            action = 'release',
            resource = resource,
            owner = owner,
            timestamp = now,
            instance = server.id or 'unknown'
        }))
        redis.call('LTRIM', 'redlock:audit', -1000, -1) -- Keep last 1000
        
        return response(true, 'Lock released')
    else
        return response(false, 'Cannot release lock - not owner or lock lost', {
            current_owner = current
        })
    end

elseif operation == 'validate' then
    -- Validate if we still hold the lock (for RedLock algorithm)
    local current = redis.call('GET', lock_key)
    local meta = redis.call('HGETALL', lock_key .. ':meta')
    local ttl = redis.call('PTTL', lock_key)
    
    if current == owner then
        -- We still hold the lock
        return response(true, 'Lock is valid', {
            owner = current,
            ttl = ttl,
            meta = meta,
            expires_at = now + ttl
        })
    elseif current then
        -- Lock held by someone else
        return response(false, 'Lock held by another', {
            current_owner = current,
            ttl = ttl,
            meta = meta
        })
    else
        -- Lock is lost
        return response(false, 'Lock is lost')
    end
end

return response(false, 'Unknown operation')