-- session_analytics.lua
-- Provides analytics and insights on session data

-- KEYS[1] = analytics key
-- KEYS[2] = time series key
-- ARGV[1] = operation: 'get_metrics', 'get_trends', 'get_heatmap', 'get_funnels', 'get_retention'
-- ARGV[2] = parameters (JSON string)
-- ARGV[3] = current timestamp

local analytics_key = KEYS[1] or 'analytics:sessions'
local timeseries_key = KEYS[2] or 'timeseries:sessions'
local operation = ARGV[1]
local params = cjson.decode(ARGV[2] or '{}')
local now = tonumber(ARGV[3]) or redis.call('TIME')[1]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

if operation == 'get_metrics' then
    local period = params.period or 'day' -- 'hour', 'day', 'week', 'month'
    local start_time = params.start_time or (now - 86400 * 7)
    local end_time = params.end_time or now
    
    local metrics = {
        total_sessions = 0,
        active_sessions = 0,
        avg_duration = 0,
        peak_concurrent = 0,
        session_types = {},
        device_breakdown = {},
        geographic = {}
    }
    
    -- Get session metrics from time series
    local session_data = redis.call('ZRANGEBYSCORE', timeseries_key, start_time, end_time, 'WITHSCORES')
    
    local total_duration = 0
    local session_count = 0
    
    for i = 1, #session_data, 2 do
        local session_json = session_data[i]
        local timestamp = tonumber(session_data[i+1])
        
        local session = cjson.decode(session_json)
        session_count = session_count + 1
        
        if session.duration then
            total_duration = total_duration + session.duration
        end
        
        if session.type then
            metrics.session_types[session.type] = (metrics.session_types[session.type] or 0) + 1
        end
        
        if session.device_type then
            metrics.device_breakdown[session.device_type] = (metrics.device_breakdown[session.device_type] or 0) + 1
        end
        
        if session.location and session.location.city then
            metrics.geographic[session.location.city] = (metrics.geographic[session.location.city] or 0) + 1
        end
    end
    
    metrics.total_sessions = session_count
    metrics.avg_duration = session_count > 0 and total_duration / session_count or 0
    
    -- Get current active sessions
    metrics.active_sessions = redis.call('SCARD', 'sessions:global:active') or 0
    
    -- Get peak concurrent from history
    local peak_key = 'stats:peak_concurrent'
    metrics.peak_concurrent = tonumber(redis.call('GET', peak_key)) or 0
    
    return response(true, 'Metrics retrieved', metrics)

elseif operation == 'get_trends' then
    local metric = params.metric or 'sessions' -- 'sessions', 'duration', 'users'
    local interval = params.interval or 3600 -- 1 hour
    local points = params.points or 24
    
    local trends = {}
    local current = now
    
    for i = 1, points do
        local end_ts = current - ((i-1) * interval)
        local start_ts = end_ts - interval
        
        local count = 0
        
        if metric == 'sessions' then
            count = redis.call('ZCOUNT', timeseries_key, start_ts, end_ts)
        elseif metric == 'users' then
            -- Count unique users in interval
            local user_set = 'temp:users:' .. start_ts
            local sessions = redis.call('ZRANGEBYSCORE', timeseries_key, start_ts, end_ts)
            
            for _, session_json in ipairs(sessions) do
                local session = cjson.decode(session_json)
                if session.user_id then
                    redis.call('SADD', user_set, session.user_id)
                end
            end
            
            count = redis.call('SCARD', user_set)
            redis.call('DEL', user_set)
        end
        
        table.insert(trends, 1, {
            timestamp = start_ts,
            value = count,
            label = os.date('!%Y-%m-%d %H:%M', start_ts)
        })
    end
    
    return response(true, 'Trends retrieved', {
        metric = metric,
        interval = interval,
        data = trends
    })

elseif operation == 'get_heatmap' then
    -- Generate heatmap of session activity by hour and day
    local days = params.days or 7
    local heatmap = {}
    
    for day = 0, days - 1 do
        local day_start = now - (day * 86400)
        local day_end = day_start + 86400
        local day_data = {}
        
        for hour = 0, 23 do
            local hour_start = day_start + (hour * 3600)
            local hour_end = hour_start + 3600
            
            local count = redis.call('ZCOUNT', timeseries_key, hour_start, hour_end)
            
            table.insert(day_data, {
                hour = hour,
                count = count,
                intensity = count > 0 and math.min(1, count / 100) or 0
            })
        end
        
        table.insert(heatmap, {
            date = os.date('!%Y-%m-%d', day_start),
            day_of_week = tonumber(os.date('!%w', day_start)),
            hours = day_data
        })
    end
    
    return response(true, 'Heatmap generated', {
        days = days,
        data = heatmap
    })

elseif operation == 'get_funnels' then
    -- Analyze user funnel through key actions
    local funnel_name = params.funnel or 'parking'
    local start_date = params.start_date or (now - 86400 * 30)
    local end_date = params.end_date or now
    
    local funnels = {
        parking = {
            steps = {'enter_lot', 'park_vehicle', 'make_payment', 'exit_lot'},
            data = {}
        },
        reservation = {
            steps = {'search', 'select_space', 'confirm', 'pay_deposit', 'arrive'},
            data = {}
        }
    }
    
    local selected = funnels[funnel_name]
    if not selected then
        return response(false, 'Unknown funnel')
    end
    
    -- Get unique users who completed each step
    local step_data = {}
    for i, step in ipairs(selected.steps) do
        local user_set = 'temp:funnel:' .. step .. ':' .. start_date
        local count = 0
        
        -- Find activities matching this step
        local activity_pattern = 'activity:detail:*'
        local cursor = '0'
        
        repeat
            local result = redis.call('SCAN', cursor, 'MATCH', activity_pattern, 'COUNT', 1000)
            cursor = result[1]
            
            for _, key in ipairs(result[2]) do
                local activity_json = redis.call('GET', key)
                if activity_json then
                    local activity = cjson.decode(activity_json)
                    if activity.action == step and activity.timestamp >= start_date and activity.timestamp <= end_date then
                        if activity.user_id then
                            redis.call('SADD', user_set, activity.user_id)
                        end
                    end
                end
            end
        until cursor == '0'
        
        step_data[i] = {
            step = step,
            users = redis.call('SCARD', user_set),
            conversion_rate = 0
        }
        
        redis.call('DEL', user_set)
    end
    
    -- Calculate conversion rates
    for i = 1, #step_data do
        if i > 1 and step_data[i-1].users > 0 then
            step_data[i].conversion_rate = (step_data[i].users / step_data[i-1].users) * 100
        else
            step_data[i].conversion_rate = 100
        end
    end
    
    return response(true, 'Funnel data retrieved', {
        funnel = funnel_name,
        steps = step_data,
        overall_conversion = step_data[#step_data] and step_data[#step_data].users / step_data[1].users * 100 or 0
    })

elseif operation == 'get_retention' then
    -- Cohort retention analysis
    local cohort_period = params.cohort_period or 'week' -- 'day', 'week', 'month'
    local cohorts = params.cohorts or 4
    
    local retention_data = {}
    local now_ts = now
    
    for c = 0, cohorts - 1 do
        local cohort_start = now_ts - (c * 7 * 86400) -- Weekly cohorts
        local cohort_end = cohort_start + (7 * 86400)
        
        -- Get users who first appeared in this cohort
        local cohort_users = 'temp:cohort:' .. cohort_start
        local activity_pattern = 'activity:detail:*'
        local cursor = '0'
        
        repeat
            local result = redis.call('SCAN', cursor, 'MATCH', activity_pattern, 'COUNT', 1000)
            cursor = result[1]
            
            for _, key in ipairs(result[2]) do
                local activity_json = redis.call('GET', key)
                if activity_json then
                    local activity = cjson.decode(activity_json)
                    if activity.timestamp >= cohort_start and activity.timestamp < cohort_end then
                        if activity.user_id then
                            redis.call('SADD', cohort_users, activity.user_id)
                        end
                    end
                end
            end
        until cursor == '0'
        
        local cohort_size = redis.call('SCARD', cohort_users)
        local retention = {}
        
        -- Calculate retention for subsequent periods
        for period = 0, 3 do
            local period_start = cohort_start + (period * 7 * 86400)
            local period_end = period_start + (7 * 86400)
            
            if period_start <= now_ts then
                local retained = 0
                local users = redis.call('SMEMBERS', cohort_users)
                
                for _, user_id in ipairs(users) do
                    -- Check if user was active in this period
                    local user_activity = redis.call('ZCOUNT', 'user:' .. user_id .. ':timeline', period_start, period_end)
                    if user_activity > 0 then
                        retained = retained + 1
                    end
                end
                
                table.insert(retention, {
                    period = period,
                    retained = retained,
                    rate = cohort_size > 0 and (retained / cohort_size * 100) or 0
                })
            end
        end
        
        table.insert(retention_data, {
            cohort = os.date('!%Y-%m-%d', cohort_start),
            size = cohort_size,
            retention = retention
        })
        
        redis.call('DEL', cohort_users)
    end
    
    return response(true, 'Retention data retrieved', {
        cohort_period = cohort_period,
        data = retention_data
    })
end

return response(false, 'Unknown operation')