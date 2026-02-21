-- api_quota.lua
-- API rate limiting with monthly/daily quotas

-- KEYS[1] = api key (e.g., "quota:api:key123")
-- KEYS[2] = daily counter key
-- KEYS[3] = monthly counter key
-- ARGV[1] = daily limit
-- ARGV[2] = monthly limit
-- ARGV[3] = cost (request weight)
-- ARGV[4] = current timestamp
-- ARGV[5] = reset behavior: "strict", "soft"

local api_key = KEYS[1]
local daily_key = KEYS[2]
local monthly_key = KEYS[3]
local daily_limit = tonumber(ARGV[1])
local monthly_limit = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local reset_behavior = ARGV[5] or "strict"

-- Get current counts
local daily_used = tonumber(redis.call("GET", daily_key)) or 0
local monthly_used = tonumber(redis.call("GET", monthly_key)) or 0

-- Calculate time to next reset
local daily_reset = 86400 - (now % 86400) -- Reset at midnight UTC
local monthly_reset = (30 * 86400) - (now % (30 * 86400)) -- Simplified monthly reset

-- Check quotas
local daily_remaining = math.max(0, daily_limit - daily_used)
local monthly_remaining = math.max(0, monthly_limit - monthly_used)

if monthly_used + cost > monthly_limit then
    -- Monthly quota exceeded
    return {
        allowed = 0,
        reason = "monthly_quota_exceeded",
        monthly_used = monthly_used,
        monthly_limit = monthly_limit,
        monthly_reset = monthly_reset,
        daily_used = daily_used,
        daily_limit = daily_limit,
        daily_reset = daily_reset
    }
end

if daily_used + cost > daily_limit then
    if reset_behavior == "strict" then
        -- Daily quota exceeded, reject
        return {
            allowed = 0,
            reason = "daily_quota_exceeded",
            monthly_used = monthly_used,
            monthly_limit = monthly_limit,
            monthly_reset = monthly_reset,
            daily_used = daily_used,
            daily_limit = daily_limit,
            daily_reset = daily_reset,
            retry_after = daily_reset
        }
    else
        -- Soft mode: allow but use monthly quota
        if monthly_used + cost <= monthly_limit then
            -- Use monthly quota instead
            local new_monthly = redis.call("INCRBY", monthly_key, cost)
            if new_monthly == cost then
                redis.call("EXPIRE", monthly_key, 30 * 86400)
            end
            
            return {
                allowed = 1,
                quota_type = "monthly",
                monthly_used = new_monthly,
                monthly_limit = monthly_limit,
                monthly_remaining = monthly_limit - new_monthly,
                daily_used = daily_used,
                daily_limit = daily_limit,
                daily_reset = daily_reset,
                monthly_reset = monthly_reset
            }
        else
            return {
                allowed = 0,
                reason = "all_quotas_exceeded",
                monthly_used = monthly_used,
                monthly_limit = monthly_limit,
                monthly_reset = monthly_reset,
                daily_used = daily_used,
                daily_limit = daily_limit,
                daily_reset = daily_reset
            }
        end
    end
end

-- Update daily counter
local new_daily = redis.call("INCRBY", daily_key, cost)
if new_daily == cost then
    redis.call("EXPIRE", daily_key, 86400)
end

-- Update monthly counter
local new_monthly = redis.call("INCRBY", monthly_key, cost)
if new_monthly == cost then
    redis.call("EXPIRE", monthly_key, 30 * 86400)
end

return {
    allowed = 1,
    quota_type = "daily",
    daily_used = new_daily,
    daily_limit = daily_limit,
    daily_remaining = daily_limit - new_daily,
    monthly_used = new_monthly,
    monthly_limit = monthly_limit,
    monthly_remaining = monthly_limit - new_monthly,
    daily_reset = daily_reset,
    monthly_reset = monthly_reset
}