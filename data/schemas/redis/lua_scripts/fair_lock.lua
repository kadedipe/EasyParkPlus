-- fair_lock.lua
-- Fair lock implementation with FIFO queue to prevent starvation

-- KEYS[1] = lock key
-- KEYS[2] = queue key (sorted set for waiting clients)
-- KEYS[3] = timeout set key
-- ARGV[1] = owner identifier
-- ARGV[2] = timeout in milliseconds
-- ARGV[3] = current timestamp
-- ARGV[4] = operation: 'acquire', 'release', 'queue_position', 'cancel'

local lock_key = KEYS[1]
local queue_key = KEYS[2]
local timeout_key = KEYS[3] or (lock_key .. ':timeouts')
local owner = ARGV[1]
local timeout = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local operation = ARGV[4]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Clean up expired waiting clients
redis.call('ZREMRANGEBYSCORE', queue_key, '-inf', now)

if operation == 'acquire' then
    -- Check if lock is free
    local current_owner = redis.call('GET', lock_key)
    
    if not current_owner then
        -- Lock is free, check if we're at the front of the queue
        local front = redis.call('ZRANGE', queue_key, 0, 0, 'WITHSCORES')
        
        if #front == 0 or front[1] == owner then
            -- We're first in queue or queue is empty, acquire lock
            if #front > 0 then
                redis.call('ZREM', queue_key, owner)
            end
            
            redis.call('SET', lock_key, owner, 'PX', timeout)
            redis.call('HSET', timeout_key, owner, now + timeout)
            redis.call('PEXPIRE', timeout_key, timeout)
            
            return response(true, 'Lock acquired', {
                queue_length = redis.call('ZCARD', queue_key)
            })
        end
    end
    
    -- Add to queue if not already waiting
    local rank = redis.call('ZSCORE', queue_key, owner)
    if not rank then
        redis.call('ZADD', queue_key, now, owner)
    end
    
    -- Get queue position
    local position = redis.call('ZRANK', queue_key, owner)
    local queue_length = redis.call('ZCARD', queue_key)
    
    -- Get current lock info
    current_owner = redis.call('GET', lock_key)
    local ttl = redis.call('PTTL', lock_key)
    
    return response(false, 'Added to waiting queue', {
        position = position,
        queue_length = queue_length,
        current_owner = current_owner,
        lock_ttl = ttl,
        estimated_wait = (position + 1) * (timeout / 2) -- Rough estimate
    })

elseif operation == 'release' then
    local current = redis.call('GET', lock_key)
    
    if current == owner then
        -- Release the lock
        redis.call('DEL', lock_key)
        redis.call('HDEL', timeout_key, owner)
        
        -- Get next waiter
        local next_waiter = redis.call('ZRANGE', queue_key, 0, 0)
        
        if #next_waiter > 0 then
            return response(true, 'Lock released, next waiter available', {
                next_waiter = next_waiter[1]
            })
        else
            return response(true, 'Lock released, no waiters')
        end
    else
        return response(false, 'Cannot release lock - not owner')
    end

elseif operation == 'queue_position' then
    local position = redis.call('ZRANK', queue_key, owner)
    local queue_length = redis.call('ZCARD', queue_key)
    local current_owner = redis.call('GET', lock_key)
    
    if position then
        return response(true, 'Queue position retrieved', {
            position = position,
            queue_length = queue_length,
            current_owner = current_owner,
            is_front = position == 0
        })
    else
        -- Check if we own the lock
        if current_owner == owner then
            return response(true, 'Currently holding lock', {
                holds_lock = true,
                ttl = redis.call('PTTL', lock_key)
            })
        else
            return response(false, 'Not in queue and not holding lock')
        end
    end

elseif operation == 'cancel' then
    local removed = redis.call('ZREM', queue_key, owner)
    
    if removed > 0 then
        return response(true, 'Cancelled waiting request')
    else
        return response(false, 'Not in waiting queue')
    end
end

return response(false, 'Unknown operation')