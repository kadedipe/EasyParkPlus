-- parking_spot_rate.lua
-- Rate limiting for parking spot reservations per vehicle

-- KEYS[1] = vehicle key (e.g., "rate:vehicle:ABC123")
-- KEYS[2] = spot type key (e.g., "rate:spot_type:electric")
-- KEYS[3] = global rate key
-- ARGV[1] = max reservations per day for vehicle
-- ARGV[2] = max reservations per day for spot type
-- ARGV[3] = max global reservations
-- ARGV[4] = cost (1 reservation)
-- ARGV[5] = current timestamp
-- ARGV[6] = spot type
-- ARGV[7] = vehicle ID

local vehicle_key = KEYS[1]
local spot_type_key = KEYS[2]
local global_key = KEYS[3]

local vehicle_limit = tonumber(ARGV[1])
local spot_type_limit = tonumber(ARGV[2])
local global_limit = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local now = tonumber(ARGV[5])
local spot_type = ARGV[6]
local vehicle_id = ARGV[7]

-- Get current counts
local vehicle_today = tonumber(redis.call("GET", vehicle_key)) or 0
local spot_type_today = tonumber(redis.call("GET", spot_type_key)) or 0
local global_today = tonumber(redis.call("GET", global_key)) or 0

-- Calculate time to reset (midnight)
local reset_time = 86400 - (now % 86400)

-- Check all limits
local violations = {}

if vehicle_today + cost > vehicle_limit then
    table.insert(violations, "vehicle_daily_limit")
end

if spot_type_today + cost > spot_type_limit then
    table.insert(violations, "spot_type_daily_limit")
end

if global_today + cost > global_limit then
    table.insert(violations, "global_daily_limit")
end

if #violations > 0 then
    return {
        allowed = 0,
        reasons = violations,
        vehicle_used = vehicle_today,
        vehicle_limit = vehicle_limit,
        spot_type_used = spot_type_today,
        spot_type_limit = spot_type_limit,
        global_used = global_today,
        global_limit = global_limit,
        reset_in = reset_time,
        spot_type = spot_type,
        vehicle_id = vehicle_id
    }
end

-- Update all counters
local new_vehicle = redis.call("INCRBY", vehicle_key, cost)
if new_vehicle == cost then
    redis.call("EXPIRE", vehicle_key, 86400)
end

local new_spot_type = redis.call("INCRBY", spot_type_key, cost)
if new_spot_type == cost then
    redis.call("EXPIRE", spot_type_key, 86400)
end

local new_global = redis.call("INCRBY", global_key, cost)
if new_global == cost then
    redis.call("EXPIRE", global_key, 86400)
end

-- Store reservation metadata
local reservation_key = "reservation:" .. vehicle_id .. ":" .. now
redis.call("HMSET", reservation_key,
    "spot_type", spot_type,
    "timestamp", now,
    "cost", cost
)
redis.call("EXPIRE", reservation_key, 86400 * 7) -- Keep for 7 days

return {
    allowed = 1,
    vehicle_used = new_vehicle,
    vehicle_limit = vehicle_limit,
    vehicle_remaining = vehicle_limit - new_vehicle,
    spot_type_used = new_spot_type,
    spot_type_limit = spot_type_limit,
    spot_type_remaining = spot_type_limit - new_spot_type,
    global_used = new_global,
    global_limit = global_limit,
    global_remaining = global_limit - new_global,
    reset_in = reset_time,
    spot_type = spot_type,
    vehicle_id = vehicle_id,
    reservation_id = reservation_key
}