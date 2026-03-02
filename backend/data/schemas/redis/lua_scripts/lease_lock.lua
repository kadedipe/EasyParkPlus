-- lease_lock.lua
-- Lock with lease time that can be extended and has automatic expiration callbacks

-- KEYS[1] = lock key
-- KEYS[2] = lease info key
-- KEYS[3] = callback queue key (optional)
-- ARGV[1] = owner identifier
-- ARGV[2] = lease duration in milliseconds
-- ARGV[3] = current timestamp
-- ARGV[4] = operation: 'acquire', 'release', 'extend', 'status', 'expire'
-- ARGV[5] = callback data (JSON string) - optional

local lock_key = KEYS[1]
local lease_key = KEYS[2]
local callback_key = KEYS[3]
local owner = ARGV[1]
local lease_duration = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local operation = ARGV[4]
local callback_data = ARGV[5]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

local function store_lease_info(expires_at)
    local lease_info = {
        owner = owner,
        acquired_at = now,
        expires_at = expires_at,
        lease_duration = lease_duration,
        extensions = 0,
        callback_data = callback_data
    }
    
    redis.call('HSET', lease_key, 
        'owner', owner,
        'acquired_at', now,
        'expires_at', expires_at,
        'lease_duration', lease_duration,
        'extensions', 0,
        'callback_data', callback_data or ''
    )
    redis.call('PEXPIRE', lease_key, lease_duration * 2)
end

if operation == 'acquire' then
    -- Try to acquire the lock
    local result = redis.call('SET', lock_key, owner, 'NX', 'PX', lease_duration)
    
    if result then
        local expires_at = now + lease_duration
        store_lease_info(expires_at)
        
        return response(true, 'Lock acquired with lease', {
            owner = owner,
            expires_at = expires_at,
            lease_duration = lease_duration,
            ttl = lease_duration
        })
    else
        -- Get current lease info
        local current_owner = redis.call('GET', lock_key)
        local lease_info = redis.call('HGETALL', lease_key)
        local ttl = redis.call('PTTL', lock_key)
        
        return response(false, 'Lock already held', {
            owner = current_owner,
            lease_info = lease_info,
            ttl = ttl
        })
    end

elseif operation == 'release' then
    local current = redis.call('GET', lock_key)
    
    if current == owner then
        -- Execute release callback if exists
        if callback_key then
            local callback = {
                type = 'release',
                owner = owner,
                resource = lock_key,
                timestamp = now,
                lease_info = redis.call('HGETALL', lease_key),
                callback_data = callback_data
            }
            redis.call('RPUSH', callback_key, cjson.encode(callback))
        end
        
        -- Delete lock and lease info
        redis.call('DEL', lock_key, lease_key)
        
        return response(true, 'Lock released', {
            lease_duration = lease_duration,
            held_for = now - (tonumber(redis.call('HGET', lease_key, 'acquired_at')) or now)
        })
    else
        return response(false, 'Cannot release lock - not owner')
    end

elseif operation == 'extend' then
    local current = redis.call('GET', lock_key)
    
    if current == owner then
        -- Extend the lock
        local new_expires = now + lease_duration
        redis.call('PEXPIRE', lock_key, lease_duration)
        
        -- Update lease info
        local extensions = tonumber(redis.call('HINCRBY', lease_key, 'extensions', 1))
        redis.call('HSET', lease_key, 'expires_at', new_expires)
        redis.call('PEXPIRE', lease_key, lease_duration * 2)
        
        -- Execute extend callback if exists
        if callback_key then
            local callback = {
                type = 'extend',
                owner = owner,
                resource = lock_key,
                timestamp = now,
                new_expires = new_expires,
                extensions = extensions,
                callback_data = callback_data
            }
            redis.call('RPUSH', callback_key, cjson.encode(callback))
        end
        
        return response(true, 'Lock extended', {
            owner = owner,
            expires_at = new_expires,
            extensions = extensions,
            ttl = lease_duration
        })
    else
        return response(false, 'Cannot extend lock - not owner')
    end

elseif operation == 'status' then
    local current = redis.call('GET', lock_key)
    local lease_info = redis.call('HGETALL', lease_key)
    local ttl = redis.call('PTTL', lock_key)
    
    if current == owner then
        return response(true, 'Lock status', {
            owner = current,
            lease_info = lease_info,
            ttl = ttl,
            is_owner = true
        })
    elseif current then
        return response(false, 'Lock held by another', {
            owner = current,
            lease_info = lease_info,
            ttl = ttl,
            is_owner = false
        })
    else
        return response(false, 'Lock is free')
    end

elseif operation == 'expire' then
    -- Force expire the lock (for cleanup)
    local current = redis.call('GET', lock_key)
    
    if current then
        -- Execute expire callback if exists
        if callback_key then
            local callback = {
                type = 'expire',
                owner = current,
                resource = lock_key,
                timestamp = now,
                lease_info = redis.call('HGETALL', lease_key),
                reason = 'timeout'
            }
            redis.call('RPUSH', callback_key, cjson.encode(callback))
        end
        
        redis.call('DEL', lock_key, lease_key)
        return response(true, 'Lock expired', {
            previous_owner = current
        })
    else
        return response(false, 'Lock already expired')
    end
end

return response(false, 'Unknown operation')