-- session_security.lua
-- Handles security aspects of session management

-- KEYS[1] = security key
-- KEYS[2] = audit key
-- ARGV[1] = operation: 'detect_anomaly', 'enforce_policy', 'audit_event', 'get_threats', 'rate_limit_check'
-- ARGV[2] = parameters (JSON string)
-- ARGV[3] = current timestamp

local security_key = KEYS[1] or 'security:events'
local audit_key = KEYS[2] or 'security:audit'
local operation = ARGV[1]
local params = cjson.decode(ARGV[2] or '{}')
local now = tonumber(ARGV[3]) or redis.call('TIME')[1]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Threat levels
local THREAT_LEVELS = {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
    CRITICAL = 4
}

-- Helper to log security events
local function log_security_event(event_type, severity, details)
    local event = {
        id = 'sec_' .. redis.sha1hex(event_type .. now .. math.random()),
        type = event_type,
        severity = severity,
        timestamp = now,
        details = details
    }
    
    redis.call('LPUSH', security_key, cjson.encode(event))
    redis.call('LTRIM', security_key, 0, 9999) -- Keep last 10000 events
    
    -- Also add to audit log
    redis.call('RPUSH', audit_key, cjson.encode(event))
    
    return event
end

if operation == 'detect_anomaly' then
    local anomalies = {}
    local user_id = params.user_id
    local session_id = params.session_id
    
    -- 1. Check for impossible travel
    if user_id and params.location then
        local last_location_key = 'user:' .. user_id .. ':last_location'
        local last_location_json = redis.call('GET', last_location_key)
        
        if last_location_json then
            local last = cjson.decode(last_location_json)
            local time_diff = now - last.timestamp
            
            if time_diff < 3600 then -- Within 1 hour
                -- Calculate distance (simplified - would use actual geo calculation)
                local distance = math.abs(params.location.lat - last.lat) + math.abs(params.location.lng - last.lng)
                
                if distance > 10 then -- More than ~10 degrees apart
                    table.insert(anomalies, {
                        type = 'impossible_travel',
                        severity = THREAT_LEVELS.HIGH,
                        details = {
                            time_diff = time_diff,
                            distance = distance,
                            previous = last,
                            current = params.location
                        }
                    })
                    
                    log_security_event('impossible_travel', THREAT_LEVELS.HIGH, {
                        user_id = user_id,
                        time_diff = time_diff,
                        distance = distance
                    })
                end
            end
        end
        
        -- Update last location
        redis.call('SETEX', last_location_key, 86400, cjson.encode({
            timestamp = now,
            lat = params.location.lat,
            lng = params.location.lng,
            city = params.location.city
        }))
    end
    
    -- 2. Check for multiple concurrent sessions from different IPs
    if user_id then
        local user_sessions = redis.call('SMEMBERS', 'user:' .. user_id .. ':sessions')
        local ip_addresses = {}
        
        for _, sess_id in ipairs(user_sessions) do
            local session_json = redis.call('GET', 'session:user:' .. sess_id)
            if session_json then
                local session = cjson.decode(session_json)
                if session.ip_address and session.ip_address ~= params.ip_address then
                    ip_addresses[session.ip_address] = (ip_addresses[session.ip_address] or 0) + 1
                end
            end
        end
        
        if #ip_addresses > 3 then
            table.insert(anomalies, {
                type = 'multiple_ips',
                severity = THREAT_LEVELS.MEDIUM,
                details = {
                    ip_count = #ip_addresses,
                    ips = ip_addresses
                }
            })
            
            log_security_event('multiple_ips', THREAT_LEVELS.MEDIUM, {
                user_id = user_id,
                ip_count = #ip_addresses
            })
        end
    end
    
    -- 3. Check for unusual activity patterns
    if session_id then
        local activity_key = 'activity:session:' .. session_id
        local recent_activity = redis.call('ZCARD', activity_key)
        local time_active = redis.call('ZRANGE', activity_key, -1, -1, 'WITHSCORES')
        
        if #time_active == 2 then
            local last_activity = tonumber(time_active[2])
            local session_duration = now - last_activity
            
            if session_duration < 300 and recent_activity > 100 then -- 5 minutes, >100 activities
                table.insert(anomalies, {
                    type = 'high_activity_rate',
                    severity = THREAT_LEVELS.MEDIUM,
                    details = {
                        activity_count = recent_activity,
                        duration = session_duration,
                        rate = recent_activity / (session_duration / 60)
                    }
                })
                
                log_security_event('high_activity_rate', THREAT_LEVELS.MEDIUM, {
                    session_id = session_id,
                    rate = recent_activity / (session_duration / 60)
                })
            end
        end
    end
    
    -- 4. Check for blacklisted IPs
    if params.ip_address then
        local blacklisted = redis.call('SISMEMBER', 'security:blacklist:ips', params.ip_address)
        if blacklisted == 1 then
            table.insert(anomalies, {
                type = 'blacklisted_ip',
                severity = THREAT_LEVELS.HIGH,
                details = {
                    ip = params.ip_address
                }
            })
            
            log_security_event('blacklisted_ip', THREAT_LEVELS.HIGH, {
                ip = params.ip_address,
                user_id = user_id
            })
        end
    end
    
    -- 5. Check for brute force attempts
    if params.login_attempt and not params.success then
        local fail_key = 'security:failed_logins:' .. (params.ip_address or 'unknown')
        local attempts = redis.call('INCR', fail_key)
        redis.call('EXPIRE', fail_key, 3600) -- 1 hour window
        
        if attempts > 5 then
            table.insert(anomalies, {
                type = 'brute_force',
                severity = THREAT_LEVELS.HIGH,
                details = {
                    ip = params.ip_address,
                    attempts = attempts,
                    window = 3600
                }
            })
            
            log_security_event('brute_force', THREAT_LEVELS.HIGH, {
                ip = params.ip_address,
                attempts = attempts
            })
            
            -- Add to temporary blocklist
            redis.call('SETEX', 'security:blocked:' .. params.ip_address, 1800, 'true')
        end
    end
    
    return response(true, 'Anomaly detection complete', {
        anomalies = anomalies,
        threat_level = #anomalies > 0 and math.max(unpack(anomalies, function(a) return a.severity end)) or 0
    })

elseif operation == 'enforce_policy' then
    local policy = params.policy or 'default'
    local user_id = params.user_id
    local session_id = params.session_id
    
    local violations = {}
    local actions = {}
    
    -- Get user's current sessions
    local user_sessions = redis.call('SMEMBERS', 'user:' .. user_id .. ':sessions')
    
    -- Policy: Maximum concurrent sessions
    local max_concurrent = params.max_concurrent or 5
    if #user_sessions > max_concurrent then
        -- Terminate oldest sessions
        local sessions_to_terminate = #user_sessions - max_concurrent
        
        for i = 1, sessions_to_terminate do
            local oldest = redis.call('ZRANGE', 'user:' .. user_id .. ':session_ages', 0, 0)
            if #oldest > 0 then
                local sess_id = oldest[1]
                table.insert(actions, {
                    type = 'terminate_session',
                    session_id = sess_id,
                    reason = 'max_concurrent_exceeded'
                })
                
                -- Actually terminate the session
                redis.call('DEL', 'session:user:' .. sess_id)
                redis.call('SREM', 'user:' .. user_id .. ':sessions', sess_id)
            end
        end
        
        table.insert(violations, {
            policy = 'max_concurrent_sessions',
            current = #user_sessions,
            limit = max_concurrent,
            action = 'terminated_oldest'
        })
    end
    
    -- Policy: Session idle timeout
    local idle_timeout = params.idle_timeout or 3600 -- 1 hour
    for _, sess_id in ipairs(user_sessions) do
        local session_json = redis.call('GET', 'session:user:' .. sess_id)
        if session_json then
            local session = cjson.decode(session_json)
            if session.last_activity and (now - session.last_activity) > idle_timeout then
                table.insert(actions, {
                    type = 'terminate_session',
                    session_id = sess_id,
                    reason = 'idle_timeout'
                })
                
                redis.call('DEL', 'session:user:' .. sess_id)
                redis.call('SREM', 'user:' .. user_id .. ':sessions', sess_id)
                
                table.insert(violations, {
                    policy = 'idle_timeout',
                    session_id = sess_id,
                    idle_time = now - session.last_activity,
                    limit = idle_timeout,
                    action = 'terminated'
                })
            end
        end
    end
    
    -- Policy: Geolocation restrictions
    if params.allowed_countries and params.location and params.location.country then
        if not params.allowed_countries[params.location.country] then
            table.insert(actions, {
                type = 'terminate_session',
                session_id = session_id,
                reason = 'geolocation_restriction'
            })
            
            redis.call('DEL', 'session:user:' .. session_id)
            redis.call('SREM', 'user:' .. user_id .. ':sessions', session_id)
            
            table.insert(violations, {
                policy = 'geolocation_restriction',
                country = params.location.country,
                allowed = params.allowed_countries,
                action = 'terminated'
            })
            
            log_security_event('geo_violation', THREAT_LEVELS.MEDIUM, {
                user_id = user_id,
                country = params.location.country
            })
        end
    end
    
    return response(true, 'Policy enforcement complete', {
        violations = violations,
        actions_taken = actions
    })

elseif operation == 'audit_event' then
    -- Log security audit event
    local event = {
        id = 'aud_' .. redis.sha1hex(params.type .. now .. math.random()),
        type = params.type,
        user_id = params.user_id,
        session_id = params.session_id,
        action = params.action,
        resource = params.resource,
        result = params.result,
        timestamp = now,
        ip_address = params.ip_address,
        user_agent = params.user_agent,
        details = params.details
    }
    
    redis.call('RPUSH', audit_key .. ':log', cjson.encode(event))
    redis.call('LTRIM', audit_key .. ':log', -10000, -1) -- Keep last 10000
    
    -- Also store in user's audit trail
    if params.user_id then
        redis.call('RPUSH', audit_key .. ':user:' .. params.user_id, cjson.encode(event))
        redis.call('LTRIM', audit_key .. ':user:' .. params.user_id, -1000, -1)
    end
    
    return response(true, 'Audit event logged', {
        event_id = event.id,
        timestamp = now
    })

elseif operation == 'get_threats' then
    local time_range = params.time_range or 3600 -- Last hour
    local threshold = params.threshold or THREAT_LEVELS.MEDIUM
    local start_time = now - time_range
    
    local threats = {}
    local events = redis.call('LRANGE', security_key, 0, -1)
    
    for _, event_json in ipairs(events) do
        local event = cjson.decode(event_json)
        if event.timestamp >= start_time and event.severity >= threshold then
            table.insert(threats, event)
        end
    end
    
    -- Group by type and severity
    local summary = {}
    for _, threat in ipairs(threats) do
        local key = threat.type .. ':' .. threat.severity
        summary[key] = (summary[key] or 0) + 1
    end
    
    return response(true, 'Threats retrieved', {
        count = #threats,
        threats = threats,
        summary = summary,
        time_range = time_range
    })

elseif operation == 'rate_limit_check' then
    -- Enhanced rate limiting with security context
    local key = params.key
    local limit = params.limit
    local window = params.window or 60
    local user_id = params.user_id
    
    if not key or not limit then
        return response(false, 'Key and limit required')
    end
    
    local current = tonumber(redis.call('GET', key)) or 0
    local ttl = redis.call('TTL', key)
    
    if current >= limit then
        -- Rate limit exceeded, log as security event if suspicious
        if user_id and current > limit * 2 then
            log_security_event('rate_limit_abuse', THREAT_LEVELS.MEDIUM, {
                user_id = user_id,
                key = key,
                attempts = current,
                limit = limit,
                window = window
            })
        end
        
        return response(false, 'Rate limit exceeded', {
            current = current,
            limit = limit,
            reset_in = ttl,
            retry_after = ttl
        })
    end
    
    -- Increment counter
    local new_value = redis.call('INCR', key)
    if new_value == 1 then
        redis.call('EXPIRE', key, window)
    end
    
    return response(true, 'Rate limit check passed', {
        current = new_value,
        remaining = limit - new_value,
        limit = limit,
        reset_in = window
    })
end

return response(false, 'Unknown operation')