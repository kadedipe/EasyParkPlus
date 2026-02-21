-- parking_session.lua
-- Manages active parking sessions with real-time tracking and billing

-- KEYS[1] = parking session key (e.g., "parking:session:{sessionId}")
-- KEYS[2] = lot sessions set
-- KEYS[3] = vehicle sessions index
-- KEYS[4] = space occupancy index
-- ARGV[1] = operation: 'start', 'end', 'update', 'get', 'list_by_lot', 'list_by_vehicle', 'calculate_fee'
-- ARGV[2] = session data (JSON string)
-- ARGV[3] = session ID
-- ARGV[4] = current timestamp
-- ARGV[5] = rate configuration (JSON string)

local session_key = KEYS[1]
local lot_sessions = KEYS[2] or (session_key .. ':lot')
local vehicle_sessions = KEYS[3] or (session_key .. ':vehicle')
local space_occupancy = KEYS[4] or (session_key .. ':space')
local operation = ARGV[1]
local session_data = ARGV[2]
local session_id = ARGV[3]
local now = tonumber(ARGV[4]) or redis.call('TIME')[1]
local rate_config = ARGV[5]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Calculate parking fee based on duration and rates
local function calculate_fee(entry_time, exit_time, vehicle_type, rate_config)
    local duration_minutes = (exit_time - entry_time) / 60
    local config = cjson.decode(rate_config or '{}')
    
    local base_rate = config.base_rate or 2.50
    local hourly_rate = config.hourly_rate or base_rate
    local daily_max = config.daily_max or 25.00
    local grace_period = config.grace_period or 15
    
    -- Apply grace period
    if duration_minutes <= grace_period then
        return 0
    end
    
    -- Calculate hours (round up)
    local hours = math.ceil(duration_minutes / 60)
    
    -- Apply vehicle type multiplier
    local multipliers = {
        car = 1.0,
        motorcycle = 0.5,
        truck = 2.0,
        bus = 3.0,
        electric = 0.8
    }
    local multiplier = multipliers[vehicle_type] or 1.0
    
    -- Calculate fee
    local fee = hours * hourly_rate * multiplier
    
    -- Apply daily max
    if fee > daily_max then
        fee = daily_max
    end
    
    return fee
end

if operation == 'start' then
    if not session_data then
        return response(false, 'Session data required')
    end
    
    local data = cjson.decode(session_data)
    local new_session_id = session_id or ('ps_' .. redis.sha1hex(session_data .. now))
    
    -- Check if space is available
    local space_key = 'space:' .. (data.space_id or 'unknown')
    local space_status = redis.call('GET', space_key)
    
    if space_status and space_status ~= 'available' then
        return response(false, 'Space not available', {
            space_id = data.space_id,
            status = space_status
        })
    end
    
    -- Check if vehicle already has active session
    if data.vehicle_id then
        local existing = redis.call('GET', vehicle_sessions .. ':' .. data.vehicle_id)
        if existing then
            return response(false, 'Vehicle already has active session', {
                vehicle_id = data.vehicle_id,
                existing_session = cjson.decode(existing)
            })
        end
    end
    
    -- Create session
    local session = {
        id = new_session_id,
        lot_id = data.lot_id,
        space_id = data.space_id,
        vehicle_id = data.vehicle_id,
        license_plate = data.license_plate,
        vehicle_type = data.vehicle_type,
        entry_time = now,
        expected_exit = data.expected_exit,
        status = 'active',
        created_by = data.created_by,
        entry_gate = data.entry_gate,
        entry_image = data.entry_image,
        entry_lpr_plate = data.entry_lpr_plate,
        entry_lpr_confidence = data.entry_lpr_confidence,
        rate_id = data.rate_id,
        base_rate = data.base_rate,
        metadata = data.metadata or {}
    }
    
    local session_json = cjson.encode(session)
    
    -- Store session
    redis.call('SETEX', session_key .. ':' .. new_session_id, 86400, session_json)
    
    -- Update indexes
    if data.lot_id then
        redis.call('SADD', lot_sessions .. ':' .. data.lot_id, new_session_id)
        redis.call('EXPIRE', lot_sessions .. ':' .. data.lot_id, 86400)
    end
    
    if data.vehicle_id then
        redis.call('SETEX', vehicle_sessions .. ':' .. data.vehicle_id, 86400, new_session_id)
    end
    
    if data.space_id then
        redis.call('SETEX', space_occupancy .. ':' .. data.space_id, 86400, new_session_id)
        redis.call('SET', space_key, 'occupied')
    end
    
    -- Update lot counters
    if data.lot_id then
        redis.call('HINCRBY', 'lot:' .. data.lot_id .. ':stats', 'active_sessions', 1)
        redis.call('HINCRBY', 'lot:' .. data.lot_id .. ':stats', 'today_entries', 1)
    end
    
    return response(true, 'Parking session started', {
        session_id = new_session_id,
        entry_time = now,
        space_id = data.space_id
    })

elseif operation == 'end' then
    if not session_id then
        return response(false, 'Session ID required')
    end
    
    local full_key = session_key .. ':' .. session_id
    local session_json = redis.call('GET', full_key)
    
    if not session_json then
        return response(false, 'Session not found')
    end
    
    local session = cjson.decode(session_json)
    
    if session.status ~= 'active' then
        return response(false, 'Session is not active', {
            status = session.status
        })
    end
    
    local exit_data = cjson.decode(session_data or '{}')
    
    -- Calculate fee
    local fee = calculate_fee(
        session.entry_time,
        now,
        session.vehicle_type,
        rate_config
    )
    
    -- Update session
    session.status = 'completed'
    session.exit_time = now
    session.duration_minutes = (now - session.entry_time) / 60
    session.exit_gate = exit_data.exit_gate
    session.exit_image = exit_data.exit_image
    session.exit_lpr_plate = exit_data.exit_lpr_plate
    session.exit_lpr_confidence = exit_data.exit_lpr_confidence
    session.base_amount = fee
    session.tax_amount = fee * 0.1
    session.total_amount = fee * 1.1
    session.payment_status = exit_data.payment_status or 'pending'
    session.ended_by = exit_data.ended_by
    
    -- Update in Redis with shorter TTL for completed sessions
    redis.call('SETEX', full_key, 259200, cjson.encode(session)) -- 3 days
    
    -- Clean up indexes
    if session.lot_id then
        redis.call('SREM', lot_sessions .. ':' .. session.lot_id, session_id)
        redis.call('HINCRBY', 'lot:' .. session.lot_id .. ':stats', 'active_sessions', -1)
        redis.call('HINCRBY', 'lot:' .. session.lot_id .. ':stats', 'today_exits', 1)
        redis.call('HINCRBY', 'lot:' .. session.lot_id .. ':stats', 'today_revenue', session.total_amount)
    end
    
    if session.vehicle_id then
        redis.call('DEL', vehicle_sessions .. ':' .. session.vehicle_id)
    end
    
    if session.space_id then
        redis.call('DEL', space_occupancy .. ':' .. session.space_id)
        redis.call('SET', 'space:' .. session.space_id, 'available')
    end
    
    return response(true, 'Parking session ended', {
        session_id = session_id,
        duration_minutes = session.duration_minutes,
        amount = session.total_amount,
        exit_time = now
    })

elseif operation == 'update' then
    if not session_id or not session_data then
        return response(false, 'Session ID and data required')
    end
    
    local full_key = session_key .. ':' .. session_id
    local session_json = redis.call('GET', full_key)
    
    if not session_json then
        return response(false, 'Session not found')
    end
    
    local session = cjson.decode(session_json)
    local updates = cjson.decode(session_data)
    
    -- Apply updates
    for k, v in pairs(updates) do
        session[k] = v
    end
    
    -- Special handling for expected exit update
    if updates.expected_exit then
        session.expected_exit = updates.expected_exit
    end
    
    redis.call('SETEX', full_key, 86400, cjson.encode(session))
    
    return response(true, 'Session updated', session)

elseif operation == 'get' then
    if not session_id then
        return response(false, 'Session ID required')
    end
    
    local session_json = redis.call('GET', session_key .. ':' .. session_id)
    
    if not session_json then
        return response(false, 'Session not found')
    end
    
    return response(true, 'Session retrieved', cjson.decode(session_json))

elseif operation == 'list_by_lot' then
    local lot_id = session_data and cjson.decode(session_data).lot_id
    if not lot_id then
        return response(false, 'Lot ID required')
    end
    
    local status = (session_data and cjson.decode(session_data).status) or 'active'
    local sessions = {}
    local session_ids = redis.call('SMEMBERS', lot_sessions .. ':' .. lot_id)
    
    for _, sid in ipairs(session_ids) do
        local sess_json = redis.call('GET', session_key .. ':' .. sid)
        if sess_json then
            local sess = cjson.decode(sess_json)
            if status == 'all' or sess.status == status then
                table.insert(sessions, sess)
            end
        end
    end
    
    return response(true, 'Sessions retrieved', {
        lot_id = lot_id,
        count = #sessions,
        sessions = sessions
    })

elseif operation == 'list_by_vehicle' then
    local vehicle_id = session_data and cjson.decode(session_data).vehicle_id
    if not vehicle_id then
        return response(false, 'Vehicle ID required')
    end
    
    local active_session_id = redis.call('GET', vehicle_sessions .. ':' .. vehicle_id)
    local sessions = {}
    
    if active_session_id then
        local session_json = redis.call('GET', session_key .. ':' .. active_session_id)
        if session_json then
            table.insert(sessions, cjson.decode(session_json))
        end
    end
    
    -- Also get completed sessions from recent list
    local completed = redis.call('ZREVRANGE', 'vehicle:' .. vehicle_id .. ':history', 0, 9)
    for _, sid in ipairs(completed) do
        local session_json = redis.call('GET', session_key .. ':' .. sid)
        if session_json then
            table.insert(sessions, cjson.decode(session_json))
        end
    end
    
    return response(true, 'Vehicle sessions retrieved', {
        vehicle_id = vehicle_id,
        count = #sessions,
        sessions = sessions
    })

elseif operation == 'calculate_fee' then
    if not session_data then
        return response(false, 'Session data required')
    end
    
    local data = cjson.decode(session_data)
    local fee = calculate_fee(
        data.entry_time or now,
        data.exit_time or now,
        data.vehicle_type or 'car',
        rate_config
    )
    
    return response(true, 'Fee calculated', {
        entry_time = data.entry_time,
        exit_time = data.exit_time,
        duration_minutes = ((data.exit_time or now) - (data.entry_time or now)) / 60,
        fee = fee,
        with_tax = fee * 1.1
    })
end

return response(false, 'Unknown operation')