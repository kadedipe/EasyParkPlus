-- token_bucket_priority.lua
-- Token bucket rate limiter with priority support for different user tiers

-- KEYS[1] = bucket key (e.g., "token_bucket:user:123")
-- KEYS[2] = priority queue key
-- ARGV[1] = limit (tokens per window)
-- ARGV[2] = window size in seconds
-- ARGV[3] = current timestamp
-- ARGV[4] = cost (tokens required)
-- ARGV[5] = priority (1-10, higher = more priority)
-- ARGV[6] = burst size

local bucket_key = KEYS[1]
local priority_key = KEYS[2]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local priority = tonumber(ARGV[5]) or 5
local burst = tonumber(ARGV[6]) or limit

-- Get bucket state
local bucket = redis.call("HMGET", bucket_key, "tokens", "last_refill", "priority_level")
local tokens = tonumber(bucket[1]) or burst
local last_refill = tonumber(bucket[2]) or now
local priority_level = tonumber(bucket[3]) or 1

-- Calculate tokens to add based on time passed
local time_passed = now - last_refill
local tokens_to_add = math.floor(time_passed * (limit / window))

if tokens_to_add > 0 then
    tokens = math.min(burst, tokens + tokens_to_add)
    last_refill = now
end

-- Adjust effective tokens based on priority
local priority_multiplier = 1 + (priority - 5) * 0.1 -- ±10% per priority level
local effective_tokens = math.floor(tokens * priority_multiplier)

-- Check if enough tokens
if effective_tokens >= cost then
    -- Consume tokens
    tokens = tokens - cost
    redis.call("HMSET", bucket_key, 
        "tokens", tokens, 
        "last_refill", last_refill,
        "priority_level", priority
    )
    redis.call("EXPIRE", bucket_key, window * 2)
    
    -- Calculate rate limit info
    local reset_time = now + math.ceil((window / limit) * 1000) / 1000
    local remaining = math.floor(tokens)
    
    return {1, remaining, reset_time, priority}
else
    -- Calculate wait time
    local tokens_needed = cost - effective_tokens
    local wait_time = math.ceil((tokens_needed * (window / limit)) * 1000) / 1000
    
    -- Add to priority queue if specified
    if priority_key then
        redis.call("ZADD", priority_key, now + wait_time, bucket_key)
        redis.call("EXPIRE", priority_key, window)
    end
    
    return {0, 0, now + wait_time, priority, wait_time}
end