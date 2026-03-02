-- user_session.lua
-- Manages user sessions with support for multiple concurrent sessions,
-- session validation, and automatic expiration

-- KEYS[1] = user session key (e.g., "session:user:{userId}")
-- KEYS[2] = active sessions set for user
-- KEYS[3] = global session index
-- ARGV[1] = operation: 'create', 'validate', 'refresh', 'destroy', 'list', 'kill_all'
-- ARGV[2] = session data (JSON string) - for create/update
-- ARGV[3] = session ID - for specific operations
-- ARGV[4] = session TTL in seconds
-- ARGV[5] = max concurrent sessions per user
-- ARGV[6] = current timestamp

local user_key = KEYS[1]
local sessions_set = KEYS[2] or (user_key .. ':sessions')
local global_index = KEYS[3] or 'sessions:global:index'
local operation = ARGV[1]
local session_data = ARGV[2]
local session_id = ARGV[3]
local session_ttl = tonumber(ARGV[4]) or 86400 -- 24 hours default
local max_sessions = tonumber(ARGV[5]) or 5
local now = tonumber(ARGV[6]) or redis.call('TIME')[1]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Helper to generate session ID
local function generate_session_id()
    local random = redis.call('TIME')[1] .. ':' .. redis.call('INCR', 'session:counter')
    return 'sess_' .. redis.sha1hex(random)
end

-- Helper to clean expired sessions
local function clean_expired_sessions()
    local expired = redis.call('ZRANGEBYSCORE', sessions_set, '-inf', now)
    for _, old_session in ipairs(expired) do
        redis.call('DEL', user_key .. ':' .. old_session)
        redis.call('SREM', sessions_set, old_session)
        redis.call('ZREM', sessions_set, old_session)
        redis.call('SREM', global_index .. ':active', old_session)
    end
end

if operation == 'create' then
    -- Clean expired sessions first
    clean_expired_sessions()
    
    -- Check current active sessions
    local active_count = redis.call('ZCARD', sessions_set)
    
    if active_count >= max_sessions then
        -- Remove oldest session if at limit
        local oldest = redis.call('ZRANGE', sessions_set, 0, 0)
        if #oldest > 0 then
            redis.call('DEL', user_key .. ':' .. oldest[1])
            redis.call('ZREM', sessions_set, oldest[1])
            redis.call('SREM', global_index .. ':active', oldest[1])
        end
    end
    
    -- Create new session
    local new_session_id = session_id or generate_session_id()
    local expires_at = now + session_ttl
    
    -- Store session data
    local session = {
        id = new_session_id,
        user_id = user_key:match('session:user:(.+)'),
        created_at = now,
        expires_at = expires_at,
        last_activity = now,
        data = cjson.decode(session_data or '{}'),
        ip_address = session_data and cjson.decode(session_data).ip_address,
        user_agent = session_data and cjson.decode(session_data).user_agent
    }
    
    redis.call('SETEX', user_key .. ':' .. new_session_id, session_ttl, cjson.encode(session))
    redis.call('ZADD', sessions_set, expires_at, new_session_id)
    redis.call('SADD', global_index .. ':active', new_session_id)
    
    -- Update user's last active
    redis.call('HSET', 'user:' .. session.user_id, 'last_session', new_session_id, 'last_active', now)
    
    return response(true, 'Session created', {
        session_id = new_session_id,
        expires_at = expires_at,
        ttl = session_ttl,
        active_sessions = redis.call('ZCARD', sessions_set)
    })

elseif operation == 'validate' then
    if not session_id then
        return response(false, 'Session ID required')
    end
    
    local session_key = user_key .. ':' .. session_id
    local session_json = redis.call('GET', session_key)
    
    if not session_json then
        -- Check if expired and clean up
        redis.call('ZREM', sessions_set, session_id)
        redis.call('SREM', global_index .. ':active', session_id)
        return response(false, 'Session not found or expired')
    end
    
    local session = cjson.decode(session_json)
    
    if session.expires_at < now then
        -- Session expired, clean up
        redis.call('DEL', session_key)
        redis.call('ZREM', sessions_set, session_id)
        redis.call('SREM', global_index .. ':active', session_id)
        return response(false, 'Session expired')
    end
    
    -- Validate additional constraints if provided
    if session_data then
        local constraints = cjson.decode(session_data)
        if constraints.ip_address and session.ip_address ~= constraints.ip_address then
            return response(false, 'IP address mismatch', {
                expected = constraints.ip_address,
                actual = session.ip_address
            })
        end
        if constraints.user_agent and session.user_agent ~= constraints.user_agent then
            return response(false, 'User agent mismatch')
        end
    end
    
    return response(true, 'Session valid', session)

elseif operation == 'refresh' then
    if not session_id then
        return response(false, 'Session ID required')
    end
    
    local session_key = user_key .. ':' .. session_id
    local session_json = redis.call('GET', session_key)
    
    if not session_json then
        return response(false, 'Session not found')
    end
    
    local session = cjson.decode(session_json)
    local new_expires = now + session_ttl
    
    -- Update session
    session.last_activity = now
    session.expires_at = new_expires
    
    -- Update in Redis
    redis.call('SETEX', session_key, session_ttl, cjson.encode(session))
    redis.call('ZADD', sessions_set, new_expires, session_id)
    
    return response(true, 'Session refreshed', {
        session_id = session_id,
        expires_at = new_expires,
        ttl = session_ttl
    })

elseif operation == 'destroy' then
    if not session_id then
        return response(false, 'Session ID required')
    end
    
    local session_key = user_key .. ':' .. session_id
    local session_json = redis.call('GET', session_key)
    
    redis.call('DEL', session_key)
    redis.call('ZREM', sessions_set, session_id)
    redis.call('SREM', global_index .. ':active', session_id)
    
    if session_json then
        local session = cjson.decode(session_json)
        return response(true, 'Session destroyed', session)
    else
        return response(true, 'Session destroyed (not found)')
    end

elseif operation == 'list' then
    clean_expired_sessions()
    
    local active_sessions = {}
    local sessions = redis.call('ZRANGE', sessions_set, 0, -1, 'WITHSCORES')
    
    for i = 1, #sessions, 2 do
        local sess_id = sessions[i]
        local expires = tonumber(sessions[i+1])
        local session_key = user_key .. ':' .. sess_id
        local session_json = redis.call('GET', session_key)
        
        if session_json then
            local session = cjson.decode(session_json)
            table.insert(active_sessions, {
                session_id = sess_id,
                created_at = session.created_at,
                expires_at = expires,
                last_activity = session.last_activity,
                data = session.data,
                ttl = expires - now
            })
        end
    end
    
    return response(true, 'Sessions listed', {
        count = #active_sessions,
        sessions = active_sessions,
        max_sessions = max_sessions
    })

elseif operation == 'kill_all' then
    local sessions = redis.call('ZRANGE', sessions_set, 0, -1)
    local killed = 0
    
    for _, sess_id in ipairs(sessions) do
        redis.call('DEL', user_key .. ':' .. sess_id)
        killed = killed + 1
    end
    
    redis.call('DEL', sessions_set)
    redis.call('SREM', global_index .. ':active', unpack(sessions))
    
    return response(true, 'All sessions killed', {
        count = killed
    })

elseif operation == 'get_active_count' then
    clean_expired_sessions()
    local count = redis.call('ZCARD', sessions_set)
    
    return response(true, 'Active count retrieved', {
        user_id = user_key:match('session:user:(.+)'),
        active_sessions = count,
        max_sessions = max_sessions,
        slots_available = max_sessions - count
    })
end

return response(false, 'Unknown operation')