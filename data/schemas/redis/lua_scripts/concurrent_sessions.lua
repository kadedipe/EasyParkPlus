-- concurrent_sessions.lua
-- Limit concurrent active sessions per user/vehicle

-- KEYS[1] = user session key (e.g., "sessions:user:123")
-- KEYS[2] = global session counter
-- ARGV[1] = max concurrent sessions
-- ARGV[2] = session ID
-- ARGV[3] = session TTL in seconds
-- ARGV[4] = action: "start", "end", "check"
-- ARGV[5] = current timestamp

local user_key = KEYS[1]
local global_key = KEYS[2]
local max_sessions = tonumber(ARGV[1])
local session_id = ARGV[2]
local session_ttl = tonumber(ARGV[3])
local action = ARGV[4]
local now = tonumber(ARGV[5])

-- Clean up expired sessions first
redis.call("ZREMRANGEBYSCORE", user_key, 0, now)

if action == "start" then
    -- Count current active sessions
    local active = redis.call("ZCARD", user_key)
    
    if active < max_sessions then
        -- Start new session
        redis.call("ZADD", user_key, now + session_ttl, session_id)
        redis.call("EXPIRE", user_key, session_ttl * 2)
        
        -- Update global counter
        redis.call("INCR", global_key)
        redis.call("EXPIRE", global_key, 3600)
        
        return {1, active + 1, max_sessions - active - 1, now + session_ttl}
    else
        -- Get earliest session expiry for retry_after
        local oldest = redis.call("ZRANGE", user_key, 0, 0, "WITHSCORES")
        local retry_after = tonumber(oldest[2]) - now
        
        return {0, active, 0, now + retry_after, retry_after}
    end
    
elseif action == "end" then
    -- End session
    local removed = redis.call("ZREM", user_key, session_id)
    
    if removed > 0 then
        redis.call("DECR", global_key)
    end
    
    local remaining = redis.call("ZCARD", user_key)
    return {1, remaining, max_sessions - remaining, 0}
    
elseif action == "check" then
    -- Just check current count
    local active = redis.call("ZCARD", user_key)
    return {1, active, max_sessions - active, 0}
end

return {0, 0, 0, 0}