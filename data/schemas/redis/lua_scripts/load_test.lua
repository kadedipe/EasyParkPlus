-- load_test.lua
-- Script for load testing rate limiters

-- KEYS[1] = test key
-- ARGV[1] = requests per second
-- ARGV[2] = duration in seconds
-- ARGV[3] = burst size
-- ARGV[4] = current timestamp

local test_key = KEYS[1]
local rps = tonumber(ARGV[1])
local duration = tonumber(ARGV[2])
local burst = tonumber(ARGV[3]) or rps
local now = tonumber(ARGV[4])

-- Initialize test if not exists
local test_start = redis.call("GET", test_key .. ":start")
if not test_start then
    redis.call("SETEX", test_key .. ":start", duration, now)
    redis.call("SETEX", test_key .. ":count", duration, 0)
    redis.call("SETEX", test_key .. ":accepted", duration, 0)
    redis.call("SETEX", test_key .. ":rejected", duration, 0)
    test_start = now
end

-- Calculate elapsed time
local elapsed = now - tonumber(test_start)

if elapsed > duration then
    -- Test complete, return results
    local total = tonumber(redis.call("GET", test_key .. ":count")) or 0
    local accepted = tonumber(redis.call("GET", test_key .. ":accepted")) or 0
    local rejected = tonumber(redis.call("GET", test_key .. ":rejected")) or 0
    
    return {
        complete = 1,
        duration = duration,
        total_requests = total,
        accepted = accepted,
        rejected = rejected,
        actual_rps = total / duration,
        target_rps = rps,
        success_rate = (accepted / total) * 100
    }
end

-- Simulate token bucket for load generation
local bucket_key = test_key .. ":bucket"
local bucket = redis.call("HMGET", bucket_key, "tokens", "last_refill")
local tokens = tonumber(bucket[1]) or burst
local last_refill = tonumber(bucket[2]) or now

-- Calculate token refill
local time_passed = now - last_refill
local tokens_to_add = math.floor(time_passed * (rps / 1)) -- 1 second window

if tokens_to_add > 0 then
    tokens = math.min(burst, tokens + tokens_to_add)
    last_refill = now
end

-- Generate request based on available tokens
local request_count = 0
local request_accepted = 0

while tokens >= 1 and request_count < math.min(10, rps) do
    tokens = tokens - 1
    request_count = request_count + 1
    request_accepted = request_accepted + 1
end

-- Update counters
redis.call("INCRBY", test_key .. ":count", request_count)
redis.call("INCRBY", test_key .. ":accepted", request_accepted)
redis.call("INCRBY", test_key .. ":rejected", request_count - request_accepted)

-- Update bucket
redis.call("HMSET", bucket_key, "tokens", tokens, "last_refill", last_refill)
redis.call("EXPIRE", bucket_key, duration * 2)

return {
    complete = 0,
    elapsed = elapsed,
    remaining = duration - elapsed,
    requests_this_second = request_count,
    accepted_this_second = request_accepted,
    tokens_remaining = tokens,
    rps = rps
}