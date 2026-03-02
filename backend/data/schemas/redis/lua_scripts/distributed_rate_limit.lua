-- distributed_rate_limit.lua
-- Distributed rate limiter using Redis Cluster with failover support

-- KEYS[1..N] = rate limit keys across shards
-- ARGV[1] = limit
-- ARGV[2] = window
-- ARGV[3] = current timestamp
-- ARGV[4] = min_shards (minimum shards required for decision)
-- ARGV[5] = consistency_level: "quorum", "all", "majority"

local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local min_shards = tonumber(ARGV[4]) or math.ceil(#KEYS / 2)
local consistency = ARGV[5] or "quorum"

local shard_results = {}
local total_current = 0
local success_count = 0

-- Query all shards
for i, key in ipairs(KEYS) do
    local current = tonumber(redis.call("GET", key)) or 0
    local ttl = redis.call("TTL", key)
    
    shard_results[i] = {
        key = key,
        current = current,
        ttl = ttl
    }
    
    total_current = total_current + current
    success_count = success_count + 1
end

-- Check consistency requirements
local allowed = false
local required_success = 0

if consistency == "all" then
    required_success = #KEYS
elseif consistency == "quorum" then
    required_success = min_shards
elseif consistency == "majority" then
    required_success = math.floor(#KEYS / 2) + 1
end

if success_count >= required_success then
    -- We have enough shard responses
    if total_current < limit then
        allowed = true
        
        -- Increment all shards that responded
        for i, result in ipairs(shard_results) do
            if result.current ~= nil then
                local new_value = redis.call("INCR", result.key)
                if new_value == 1 then
                    redis.call("EXPIRE", result.key, window)
                end
            end
        end
    end
end

-- Calculate distributed rate limit info
local reset_time = now + window
local remaining = math.max(0, limit - (total_current + (allowed and 1 or 0)))

return {
    allowed = allowed and 1 or 0,
    current = total_current,
    remaining = remaining,
    reset = reset_time,
    limit = limit,
    shards_responded = success_count,
    shards_total = #KEYS,
    consistency_used = consistency,
    distributed_id = redis.call("INCR", "distributed:counter") -- Unique ID for this request
}