-- distributed_lock.lua
-- Basic distributed lock implementation with timeout and auto-release

-- KEYS[1] = lock key
-- ARGV[1] = lock owner identifier (unique per client)
-- ARGV[2] = lock timeout in milliseconds
-- ARGV[3] = current timestamp in milliseconds
-- ARGV[4] = operation: 'acquire', 'release', 'renew', 'check'

local lock_key = KEYS[1]
local owner = ARGV[1]
local timeout = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local operation = ARGV[4]

-- Helper function to format response
local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

if operation == 'acquire' then
    -- Try to acquire the lock using SET NX with expiration
    local result = redis.call('SET', lock_key, owner, 'NX', 'PX', timeout)
    if result then
        return response(true, 'Lock acquired', {
            owner = owner,
            expires_at = now + timeout,
            ttl = timeout
        })
    else
        -- Lock is held by someone else, get current owner and TTL
        local current_owner = redis.call('GET', lock_key)
        local ttl = redis.call('PTTL', lock_key)
        return response(false, 'Lock already held', {
            owner = current_owner,
            ttl = ttl,
            retry_after = ttl
        })
    end

elseif operation == 'release' then
    -- Only release if we are the owner (using Lua for atomicity)
    local current = redis.call('GET', lock_key)
    if current == owner then
        redis.call('DEL', lock_key)
        return response(true, 'Lock released')
    elseif current then
        return response(false, 'Cannot release lock owned by another', {
            current_owner = current
        })
    else
        return response(false, 'Lock does not exist')
    end

elseif operation == 'renew' then
    -- Extend lock expiration if we are the owner
    local current = redis.call('GET', lock_key)
    if current == owner then
        redis.call('PEXPIRE', lock_key, timeout)
        local new_ttl = redis.call('PTTL', lock_key)
        return response(true, 'Lock renewed', {
            owner = owner,
            expires_at = now + new_ttl,
            ttl = new_ttl
        })
    else
        return response(false, 'Cannot renew lock - not owner or lock lost', {
            current_owner = current
        })
    end

elseif operation == 'check' then
    -- Check lock status
    local current = redis.call('GET', lock_key)
    local ttl = redis.call('PTTL', lock_key)
    
    if current == owner then
        return response(true, 'Lock is owned by you', {
            owner = current,
            ttl = ttl,
            expires_at = now + ttl
        })
    elseif current then
        return response(false, 'Lock is held by another', {
            owner = current,
            ttl = ttl
        })
    else
        return response(false, 'Lock is free')
    end

else
    return response(false, 'Unknown operation: ' .. tostring(operation))
end