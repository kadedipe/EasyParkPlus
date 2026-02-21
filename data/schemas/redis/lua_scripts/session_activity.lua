-- session_activity.lua
-- Tracks user activity within sessions for analytics and monitoring

-- KEYS[1] = activity key (e.g., "activity:session:{sessionId}")
-- KEYS[2] = user activity timeline
-- KEYS[3] = global activity stream
-- ARGV[1] = operation: 'log_activity', 'get_session_activity', 'get_user_timeline', 'get_activity_stats', 'get_active_users'
-- ARGV[2] = activity data (JSON string)
-- ARGV[3] = session ID
-- ARGV[4] = user ID
-- ARGV[5] = current timestamp
-- ARGV[6] = time range (for queries)

local activity_key = KEYS[1]
local user_timeline = KEYS[2]
local global_stream = KEYS[3] or 'activity:global'
local operation = ARGV[1]
local activity_data = ARGV[2]
local session_id = ARGV[3]
local user_id = ARGV[4]
local now = tonumber(ARGV[5]) or redis.call('TIME')[1]
local time_range = tonumber(ARGV[6]) or 3600

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Activity types
local ACTIVITY_TYPES = {
    PAGE_VIEW = 'page_view',
    API_CALL = 'api_call',
    BUTTON_CLICK = 'button_click',
    FORM_SUBMIT = 'form_submit',
    ERROR = 'error',
    LOGIN = 'login',
    LOGOUT = 'logout',
    PAYMENT = 'payment',
    RESERVATION = 'reservation',
    GATE_OPERATION = 'gate_operation'
}

if operation == 'log_activity' then
    if not activity_data then
        return response(false, 'Activity data required')
    end
    
    local data = cjson.decode(activity_data)
    local activity = {
        id = 'act_' .. redis.sha1hex(session_id .. now .. math.random()),
        session_id = session_id or data.session_id,
        user_id = user_id or data.user_id,
        type = data.type or ACTIVITY_TYPES.API_CALL,
        action = data.action,
        resource = data.resource,
        details = data.details or {},
        timestamp = now,
        duration = data.duration,
        ip_address = data.ip_address,
        user_agent = data.user_agent,
        location = data.location,
        result = data.result or 'success',
        error = data.error
    }
    
    local activity_json = cjson.encode(activity)
    
    -- Store in session activity log
    if session_id then
        redis.call('ZADD', activity_key .. ':' .. session_id, now, activity.id .. ':' .. now)
        redis.call('EXPIRE', activity_key .. ':' .. session_id, 86400) -- 24 hours
    end
    
    -- Store in user timeline
    if user_id then
        redis.call('ZADD', user_timeline .. ':' .. user_id, now, activity.id)
        redis.call('EXPIRE', user_timeline .. ':' .. user_id, 604800) -- 7 days
    end
    
    -- Add to global stream (with capped size)
    redis.call('ZADD', global_stream, now, activity.id)
    redis.call('ZREMRANGEBYRANK', global_stream, 0, -10001) -- Keep last 10000
    
    -- Store activity details (with TTL)
    redis.call('SETEX', 'activity:detail:' .. activity.id, 86400, activity_json)
    
    -- Update session last activity
    if session_id then
        redis.call('HSET', 'session:' .. session_id, 'last_activity', now)
    end
    
    -- Update counters
    local date_key = os.date('!%Y-%m-%d', now)
    redis.call('HINCRBY', 'stats:activity:' .. date_key, data.type or 'unknown', 1)
    
    return response(true, 'Activity logged', {
        activity_id = activity.id,
        timestamp = now
    })

elseif operation == 'get_session_activity' then
    if not session_id then
        return response(false, 'Session ID required')
    end
    
    local limit = tonumber(activity_data) or 100
    local start = now - time_range
    local end_time = now
    
    local activity_ids = redis.call('ZRANGEBYSCORE', activity_key .. ':' .. session_id, start, end_time, 'LIMIT', 0, limit)
    local activities = {}
    
    for _, activity_ref in ipairs(activity_ids) do
        local activity_id = activity_ref:match('^([^:]+)')
        local activity_json = redis.call('GET', 'activity:detail:' .. activity_id)
        if activity_json then
            table.insert(activities, cjson.decode(activity_json))
        end
    end
    
    return response(true, 'Session activity retrieved', {
        session_id = session_id,
        count = #activities,
        activities = activities,
        time_range = {start = start, end = end_time}
    })

elseif operation == 'get_user_timeline' then
    if not user_id then
        return response(false, 'User ID required')
    end
    
    local data = cjson.decode(activity_data or '{}')
    local limit = data.limit or 50
    local offset = data.offset or 0
    local activity_type = data.type
    
    local start = data.start_time or (now - 86400 * 7) -- Default to last 7 days
    local end_time = data.end_time or now
    
    local activity_ids = redis.call('ZREVRANGEBYSCORE', user_timeline .. ':' .. user_id, end_time, start, 'LIMIT', offset, limit)
    local activities = {}
    
    for _, activity_id in ipairs(activity_ids) do
        local activity_json = redis.call('GET', 'activity:detail:' .. activity_id)
        if activity_json then
            local activity = cjson.decode(activity_json)
            if not activity_type or activity.type == activity_type then
                table.insert(activities, activity)
            end
        end
    end
    
    return response(true, 'User timeline retrieved', {
        user_id = user_id,
        count = #activities,
        activities = activities,
        has_more = #activity_ids == limit
    })

elseif operation == 'get_activity_stats' then
    local data = cjson.decode(activity_data or '{}')
    local period = data.period or 'hour' -- 'hour', 'day', 'week', 'month'
    local activity_type = data.type
    
    local stats = {}
    local now_ts = now
    
    if period == 'hour' then
        for i = 0, 23 do
            local hour_start = now_ts - (i * 3600)
            local hour_end = hour_start + 3600
            local count = redis.call('ZCOUNT', global_stream, hour_start, hour_end)
            
            if activity_type then
                -- Filter by type (would need more complex query)
                count = 0
                local ids = redis.call('ZRANGEBYSCORE', global_stream, hour_start, hour_end)
                for _, id in ipairs(ids) do
                    local activity_json = redis.call('GET', 'activity:detail:' .. id)
                    if activity_json then
                        local act = cjson.decode(activity_json)
                        if act.type == activity_type then
                            count = count + 1
                        end
                    end
                end
            end
            
            table.insert(stats, {
                hour = os.date('!%H:00', hour_start),
                timestamp = hour_start,
                count = count
            })
        end
    elseif period == 'day' then
        for i = 0, 6 do
            local day_start = now_ts - (i * 86400)
            local day_end = day_start + 86400
            local count = redis.call('ZCOUNT', global_stream, day_start, day_end)
            
            table.insert(stats, {
                date = os.date('!%Y-%m-%d', day_start),
                timestamp = day_start,
                count = count
            })
        end
    end
    
    return response(true, 'Activity stats retrieved', {
        period = period,
        stats = stats
    })

elseif operation == 'get_active_users' then
    local data = cjson.decode(activity_data or '{}')
    local minutes = data.minutes or 5
    local threshold = now - (minutes * 60)
    
    -- Get unique users from recent activity
    local active_users = {}
    local activity_ids = redis.call('ZRANGEBYSCORE', global_stream, threshold, now)
    
    for _, activity_id in ipairs(activity_ids) do
        local activity_json = redis.call('GET', 'activity:detail:' .. activity_id)
        if activity_json then
            local activity = cjson.decode(activity_json)
            if activity.user_id then
                active_users[activity.user_id] = {
                    last_seen = activity.timestamp,
                    session_id = activity.session_id,
                    location = activity.location
                }
            end
        end
    end
    
    -- Convert to array
    local users = {}
    for uid, info in pairs(active_users) do
        table.insert(users, {
            user_id = uid,
            last_seen = info.last_seen,
            session_id = info.session_id,
            location = info.location
        })
    end
    
    return response(true, 'Active users retrieved', {
        minutes = minutes,
        count = #users,
        users = users
    })

elseif operation == 'get_session_summary' then
    if not session_id then
        return response(false, 'Session ID required')
    end
    
    local activity_ids = redis.call('ZRANGE', activity_key .. ':' .. session_id, 0, -1)
    local summary = {
        session_id = session_id,
        total_activities = #activity_ids,
        first_activity = nil,
        last_activity = nil,
        activity_types = {},
        api_calls = 0,
        errors = 0,
        duration = 0
    }
    
    for _, activity_ref in ipairs(activity_ids) do
        local activity_id = activity_ref:match('^([^:]+)')
        local activity_json = redis.call('GET', 'activity:detail:' .. activity_id)
        if activity_json then
            local activity = cjson.decode(activity_json)
            
            if not summary.first_activity or activity.timestamp < summary.first_activity then
                summary.first_activity = activity.timestamp
            end
            if not summary.last_activity or activity.timestamp > summary.last_activity then
                summary.last_activity = activity.timestamp
            end
            
            summary.activity_types[activity.type] = (summary.activity_types[activity.type] or 0) + 1
            
            if activity.type == ACTIVITY_TYPES.API_CALL then
                summary.api_calls = summary.api_calls + 1
            end
            
            if activity.result == 'error' then
                summary.errors = summary.errors + 1
            end
        end
    end
    
    if summary.first_activity and summary.last_activity then
        summary.duration = summary.last_activity - summary.first_activity
    end
    
    return response(true, 'Session summary retrieved', summary)
end

return response(false, 'Unknown operation')