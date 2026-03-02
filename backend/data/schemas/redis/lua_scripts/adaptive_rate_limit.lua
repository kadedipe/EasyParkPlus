-- adaptive_rate_limit.lua
-- Rate limiter that adapts based on system load and error rates

-- KEYS[1] = rate limit key
-- KEYS[2] = error counter key
-- KEYS[3] = latency key
-- ARGV[1] = base limit
-- ARGV[2] = window
-- ARGV[3] = current timestamp
-- ARGV[4] = error threshold (percentage)
-- ARGV[5] = latency threshold (ms)
-- ARGV[6] = adaptation factor

local rate_key = KEYS[1]
local error_key = KEYS[2]
local latency_key = KEYS[3]

local base_limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local error_threshold = tonumber(ARGV[4]) or 10 -- 10% error rate
local latency_threshold = tonumber(ARGV[5]) or 500 -- 500ms
local adaptation_factor = tonumber(ARGV[6]) or 0.8 -- Reduce by 20%

-- Get current stats
local current_count = tonumber(redis.call("GET", rate_key)) or 0
local error_count = tonumber(redis.call("GET", error_key)) or 0
local avg_latency = tonumber(redis.call("GET", latency_key)) or 0

-- Calculate error rate
local error_rate = 0
if current_count > 0 then
    error_rate = (error_count / current_count) * 100
end

-- Adapt limit based on system health
local adaptive_limit = base_limit

if error_rate > error_threshold or avg_latency > latency_threshold then
    -- System under stress, reduce limit
    adaptive_limit = math.floor(base_limit * adaptation_factor)
    
    -- Store adaptation info
    redis.call("SETEX", rate_key .. ":adapted", window, adaptive_limit)
    redis.call("SETEX", rate_key .. ":reason", window, 
        error_rate > error_threshold and "high_error_rate" or "high_latency")
end

-- Apply rate limiting with adaptive limit
if current_count < adaptive_limit then
    -- Allow request
    local new_count = redis.call("INCR", rate_key)
    if new_count == 1 then
        redis.call("EXPIRE", rate_key, window)
    end
    
    return {
        allowed = 1,
        current = new_count,
        limit = adaptive_limit,
        base_limit = base_limit,
        remaining = adaptive_limit - new_count,
        error_rate = error_rate,
        avg_latency = avg_latency,
        adapted = (adaptive_limit < base_limit)
    }
else
    -- Reject request
    return {
        allowed = 0,
        current = current_count,
        limit = adaptive_limit,
        base_limit = base_limit,
        remaining = 0,
        error_rate = error_rate,
        avg_latency = avg_latency,
        adapted = (adaptive_limit < base_limit),
        retry_after = window - (now % window)
    }
end