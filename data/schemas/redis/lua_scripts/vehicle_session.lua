-- vehicle_session.lua
-- Manages vehicle tracking across multiple parking sessions

-- KEYS[1] = vehicle key (e.g., "vehicle:{licensePlate}")
-- KEYS[2] = vehicle history key
-- KEYS[3] = active vehicle set
-- ARGV[1] = operation: 'track', 'update_location', 'get_history', 'get_current', 'check_blacklist', 'update_status'
-- ARGV[2] = vehicle data (JSON string)
-- ARGV[3] = license plate
-- ARGV[4] = current timestamp
-- ARGV[5] = TTL for location data

local vehicle_key = KEYS[1]
local history_key = KEYS[2] or (vehicle_key .. ':history')
local active_set = KEYS[3] or 'vehicles:active'
local operation = ARGV[1]
local vehicle_data = ARGV[2]
local license_plate = ARGV[3]
local now = tonumber(ARGV[4]) or redis.call('TIME')[1]
local location_ttl = tonumber(ARGV[5]) or 300 -- 5 minutes default

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Helper to normalize license plate
local function normalize_plate(plate)
    return string.upper(string.gsub(plate, '[^A-Z0-9]', ''))
end

if operation == 'track' then
    if not license_plate or not vehicle_data then
        return response(false, 'License plate and vehicle data required')
    end
    
    local normalized = normalize_plate(license_plate)
    local data = cjson.decode(vehicle_data)
    
    -- Store current vehicle info
    local vehicle_info = {
        license_plate = license_plate,
        normalized = normalized,
        make = data.make,
        model = data.model,
        color = data.color,
        year = data.year,
        vehicle_type = data.vehicle_type,
        is_electric = data.is_electric or false,
        is_handicapped = data.is_handicapped or false,
        owner_id = data.owner_id,
        last_seen = now,
        last_location = data.location,
        last_lot_id = data.lot_id,
        status = data.status or 'active',
        session_id = data.session_id,
        tags = data.tags or {}
    }
    
    -- Store in Redis
    redis.call('SETEX', vehicle_key .. ':' .. normalized, location_ttl, cjson.encode(vehicle_info))
    
    -- Add to active set
    redis.call('SADD', active_set, normalized)
    
    -- Add to history (sorted by timestamp)
    redis.call('ZADD', history_key .. ':' .. normalized, now, now .. ':' .. (data.session_id or 'unknown'))
    redis.call('EXPIRE', history_key .. ':' .. normalized, 2592000) -- 30 days
    
    -- Update lot-specific vehicle set
    if data.lot_id then
        redis.call('SADD', 'lot:' .. data.lot_id .. ':vehicles', normalized)
        redis.call('EXPIRE', 'lot:' .. data.lot_id .. ':vehicles', 86400)
    end
    
    return response(true, 'Vehicle tracked', {
        license_plate = license_plate,
        normalized = normalized,
        last_seen = now
    })

elseif operation == 'update_location' then
    if not license_plate or not vehicle_data then
        return response(false, 'License plate and location data required')
    end
    
    local normalized = normalize_plate(license_plate)
    local data = cjson.decode(vehicle_data)
    local vehicle_info_key = vehicle_key .. ':' .. normalized
    
    local vehicle_json = redis.call('GET', vehicle_info_key)
    
    if vehicle_json then
        local vehicle = cjson.decode(vehicle_json)
        
        -- Update location
        vehicle.last_seen = now
        vehicle.last_location = data.location
        vehicle.last_lot_id = data.lot_id
        vehicle.last_gate = data.gate_id
        
        if data.status then
            vehicle.status = data.status
        end
        
        redis.call('SETEX', vehicle_info_key, location_ttl, cjson.encode(vehicle))
        
        -- Record location history
        local location_history = vehicle_key .. ':location:' .. normalized
        redis.call('ZADD', location_history, now, cjson.encode({
            timestamp = now,
            location = data.location,
            lot_id = data.lot_id,
            gate_id = data.gate_id
        }))
        redis.call('EXPIRE', location_history, 86400) -- Keep 24 hours of location history
        
        return response(true, 'Vehicle location updated', {
            license_plate = license_plate,
            last_seen = now,
            location = data.location
        })
    else
        return response(false, 'Vehicle not found')
    end

elseif operation == 'get_current' then
    if not license_plate then
        return response(false, 'License plate required')
    end
    
    local normalized = normalize_plate(license_plate)
    local vehicle_json = redis.call('GET', vehicle_key .. ':' .. normalized)
    
    if not vehicle_json then
        return response(false, 'Vehicle not found or inactive')
    end
    
    local vehicle = cjson.decode(vehicle_json)
    
    -- Get active parking session if any
    local active_session = nil
    if vehicle.session_id then
        local session_json = redis.call('GET', 'parking:session:' .. vehicle.session_id)
        if session_json then
            active_session = cjson.decode(session_json)
        end
    end
    
    return response(true, 'Vehicle info retrieved', {
        vehicle = vehicle,
        active_session = active_session
    })

elseif operation == 'get_history' then
    if not license_plate then
        return response(false, 'License plate required')
    end
    
    local normalized = normalize_plate(license_plate)
    local limit = tonumber(vehicle_data) or 10
    
    local history = redis.call('ZREVRANGE', history_key .. ':' .. normalized, 0, limit - 1, 'WITHSCORES')
    local sessions = {}
    
    for i = 1, #history, 2 do
        local session_ref = history[i]
        local timestamp = tonumber(history[i+1])
        local session_id = session_ref:match(':(.+)$')
        
        if session_id then
            local session_json = redis.call('GET', 'parking:session:' .. session_id)
            if session_json then
                table.insert(sessions, {
                    timestamp = timestamp,
                    session = cjson.decode(session_json)
                })
            end
        end
    end
    
    return response(true, 'Vehicle history retrieved', {
        license_plate = license_plate,
        count = #sessions,
        sessions = sessions
    })

elseif operation == 'check_blacklist' then
    if not license_plate then
        return response(false, 'License plate required')
    end
    
    local normalized = normalize_plate(license_plate)
    local blacklist_key = 'blacklist:vehicles'
    
    -- Check exact match
    local blacklisted = redis.call('SISMEMBER', blacklist_key, normalized)
    
    -- Check pattern matches (partial blacklist)
    local patterns = redis.call('SMEMBERS', blacklist_key .. ':patterns')
    local pattern_match = false
    local matched_pattern = nil
    
    for _, pattern in ipairs(patterns) do
        if string.match(normalized, pattern) then
            pattern_match = true
            matched_pattern = pattern
            break
        end
    end
    
    -- Get blacklist reason if any
    local reason = nil
    if blacklisted == 1 or pattern_match then
        local reason_key = blacklist_key .. ':reason:' .. (blacklisted == 1 and normalized or matched_pattern)
        reason = redis.call('GET', reason_key)
    end
    
    return response(true, 'Blacklist check complete', {
        license_plate = license_plate,
        normalized = normalized,
        is_blacklisted = (blacklisted == 1) or pattern_match,
        exact_match = blacklisted == 1,
        pattern_match = pattern_match,
        matched_pattern = matched_pattern,
        reason = reason
    })

elseif operation == 'update_status' then
    if not license_plate or not vehicle_data then
        return response(false, 'License plate and status required')
    end
    
    local normalized = normalize_plate(license_plate)
    local data = cjson.decode(vehicle_data)
    local vehicle_info_key = vehicle_key .. ':' .. normalized
    
    local vehicle_json = redis.call('GET', vehicle_info_key)
    
    if vehicle_json then
        local vehicle = cjson.decode(vehicle_json)
        vehicle.status = data.status
        vehicle.status_updated_at = now
        vehicle.status_reason = data.reason
        
        if data.status == 'exited' or data.status == 'completed' then
            -- Remove from active set
            redis.call('SREM', active_set, normalized)
            -- Clear session reference
            vehicle.session_id = nil
        end
        
        redis.call('SETEX', vehicle_info_key, location_ttl, cjson.encode(vehicle))
        
        return response(true, 'Vehicle status updated', {
            license_plate = license_plate,
            status = data.status,
            previous_status = vehicle.status
        })
    else
        return response(false, 'Vehicle not found')
    end

elseif operation == 'get_active_count' then
    local lot_id = vehicle_data and cjson.decode(vehicle_data).lot_id
    
    if lot_id then
        local count = redis.call('SCARD', 'lot:' .. lot_id .. ':vehicles')
        return response(true, 'Active vehicle count retrieved', {
            lot_id = lot_id,
            count = count
        })
    else
        local count = redis.call('SCARD', active_set)
        return response(true, 'Global active vehicle count', {
            count = count
        })
    end
end

return response(false, 'Unknown operation')