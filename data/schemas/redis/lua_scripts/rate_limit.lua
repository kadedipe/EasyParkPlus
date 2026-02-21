-- rate_limit.lua
-- Redis Lua script for rate limiting in parking management system
-- Supports multiple rate limiting strategies: token bucket, sliding window, fixed window
-- Returns: {
--   allowed: boolean,
--   remaining: number,
--   reset: number,
--   retry_after: number,
--   limit: number,
--   current: number
-- }

-- KEYS[1] = rate limit key (e.g., "rate_limit:api:user:123")
-- KEYS[2] = counter key for sliding window (optional)
-- ARGV[1] = limit (maximum number of requests)
-- ARGV[2] = window size in seconds
-- ARGV[3] = current timestamp (Unix time)
-- ARGV[4] = strategy: "fixed_window", "sliding_window", "token_bucket"
-- ARGV[5] = cost (default: 1) - for token bucket
-- ARGV[6] = burst size (default: limit) - for token bucket

local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local strategy = ARGV[4] or "fixed_window"
local cost = tonumber(ARGV[5]) or 1
local burst = tonumber(ARGV[6]) or limit

-- Helper function to return rate limit info
local function result(allowed, remaining, reset, current)
    return {
        allowed = allowed,
        remaining = remaining,
        reset = reset,
        retry_after = math.max(0, reset - now),
        limit = limit,
        current = current
    }
end

-- Fixed Window strategy
if strategy == "fixed_window" then
    local current = redis.call("INCR", key)
    if current == 1 then
        redis.call("EXPIRE", key, window)
    end
    
    local ttl = redis.call("TTL", key)
    if ttl < 0 then
        ttl = window
    end
    
    if current <= limit then
        return result(true, limit - current, now + ttl, current)
    else
        return result(false, 0, now + ttl, current)
    end

-- Sliding Window strategy
elseif strategy == "sliding_window" then
    local counter_key = KEYS[2] or key .. ":counter"
    local window_start = now - window
    
    -- Remove old entries
    redis.call("ZREMRANGEBYSCORE", key, 0, window_start)
    
    -- Count requests in current window
    local current = redis.call("ZCOUNT", key, window_start, now)
    
    -- Check if under limit
    if current < limit then
        -- Add current request
        redis.call("ZADD", key, now, now .. ":" .. math.random())
        redis.call("EXPIRE", key, window * 2) -- Keep for cleanup
        
        -- Update counter
        redis.call("SET", counter_key, current + 1)
        redis.call("EXPIRE", counter_key, window)
        
        return result(true, limit - (current + 1), window_start + window, current + 1)
    else
        -- Get oldest request time for retry_after calculation
        local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
        local reset_time = tonumber(oldest[2]) + window
        
        return result(false, 0, reset_time, current)
    end

-- Token Bucket strategy
elseif strategy == "token_bucket" then
    -- Get current bucket state
    local bucket = redis.call("HMGET", key, "tokens", "last_refill")
    local tokens = tonumber(bucket[1]) or burst
    local last_refill = tonumber(bucket[2]) or now
    
    -- Calculate tokens to add based on time passed
    local time_passed = now - last_refill
    local tokens_to_add = math.floor(time_passed * (limit / window))
    
    if tokens_to_add > 0 then
        tokens = math.min(burst, tokens + tokens_to_add)
        last_refill = now
    end
    
    -- Check if enough tokens
    if tokens >= cost then
        tokens = tokens - cost
        redis.call("HMSET", key, "tokens", tokens, "last_refill", last_refill)
        redis.call("EXPIRE", key, window * 2)
        
        -- Calculate time until next token
        local time_to_next_token = math.ceil((window / limit) * 1000) / 1000
        local reset_time = now + time_to_next_token
        
        return result(true, math.floor(tokens), reset_time, burst - tokens)
    else
        -- Calculate time until enough tokens are available
        local tokens_needed = cost - tokens
        local time_to_wait = math.ceil((tokens_needed * (window / limit)) * 1000) / 1000
        
        return result(false, 0, now + time_to_wait, burst - tokens)
    end

-- Generic/Default strategy (fixed window with decay)
else
    -- Implement a generic rate limiter with exponential decay
    local decay_factor = 0.9 -- 90% decay per window
    local current = tonumber(redis.call("GET", key)) or 0
    
    -- Apply decay based on time passed
    local last_reset = tonumber(redis.call("GET", key .. ":last_reset")) or now
    local time_passed = now - last_reset
    
    if time_passed > 0 then
        local decay = math.pow(decay_factor, time_passed / window)
        current = math.floor(current * decay)
    end
    
    -- Check if under limit
    if current < limit then
        current = current + cost
        redis.call("SETEX", key, window * 2, current)
        redis.call("SETEX", key .. ":last_reset", window * 2, now)
        
        return result(true, limit - current, now + window, current)
    else
        return result(false, 0, last_reset + window, current)
    end
end