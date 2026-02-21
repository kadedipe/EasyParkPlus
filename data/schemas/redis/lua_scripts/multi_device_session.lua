-- multi_device_session.lua
-- Manages user sessions across multiple devices with sync capabilities

-- KEYS[1] = user base key (e.g., "user:{userId}:devices")
-- KEYS[2] = device sessions key
-- KEYS[3] = sync queue key
-- ARGV[1] = operation: 'register_device', 'unregister_device', 'sync_state', 'get_devices', 'broadcast', 'get_device_session'
-- ARGV[2] = user ID
-- ARGV[3] = device data (JSON string)
-- ARGV[4] = current timestamp
-- ARGV[5] = session TTL

local user_key = KEYS[1]
local device_key = KEYS[2] or (user_key .. ':devices')
local sync_key = KEYS[3] or (user_key .. ':sync')
local operation = ARGV[1]
local user_id = ARGV[2]
local device_data = ARGV[3]
local now = tonumber(ARGV[4]) or redis.call('TIME')[1]
local session_ttl = tonumber(ARGV[5]) or 86400

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Helper to generate device ID
local function generate_device_id(device_info)
    return 'dev_' .. redis.sha1hex(device_info .. now)
end

if operation == 'register_device' then
    if not user_id or not device_data then
        return response(false, 'User ID and device data required')
    end
    
    local data = cjson.decode(device_data)
    local device_id = data.device_id or generate_device_id(device_data)
    
    -- Device info
    local device_info = {
        device_id = device_id,
        user_id = user_id,
        device_type = data.device_type, -- 'mobile', 'web', 'kiosk', 'gate'
        device_name = data.device_name,
        platform = data.platform,
        os_version = data.os_version,
        app_version = data.app_version,
        push_token = data.push_token,
        ip_address = data.ip_address,
        location = data.location,
        last_seen = now,
        registered_at = now,
        session_id = data.session_id,
        capabilities = data.capabilities or {},
        is_active = true
    }
    
    -- Store device info
    redis.call('SETEX', device_key .. ':' .. device_id, session_ttl, cjson.encode(device_info))
    
    -- Add to user's device set
    redis.call('SADD', user_key .. ':devices', device_id)
    
    -- Create device-specific session
    local device_session = {
        device_id = device_id,
        user_id = user_id,
        created_at = now,
        last_activity = now,
        current_session_id = data.session_id,
        state = data.initial_state or {}
    }
    redis.call('SETEX', device_key .. ':session:' .. device_id, session_ttl, cjson.encode(device_session))
    
    return response(true, 'Device registered', {
        device_id = device_id,
        user_id = user_id,
        expires_at = now + session_ttl
    })

elseif operation == 'unregister_device' then
    if not device_data then
        return response(false, 'Device ID required')
    end
    
    local data = cjson.decode(device_data)
    local device_id = data.device_id
    
    -- Get device info for cleanup
    local device_json = redis.call('GET', device_key .. ':' .. device_id)
    
    -- Remove all device data
    redis.call('DEL', device_key .. ':' .. device_id)
    redis.call('DEL', device_key .. ':session:' .. device_id)
    redis.call('SREM', user_key .. ':devices', device_id)
    
    -- Send logout notification if needed
    if data.notify and device_json then
        local device = cjson.decode(device_json)
        local logout_msg = {
            type = 'device_logout',
            device_id = device_id,
            user_id = user_id,
            timestamp = now,
            reason = data.reason or 'user_initiated'
        }
        redis.call('RPUSH', sync_key .. ':outgoing', cjson.encode(logout_msg))
    end
    
    return response(true, 'Device unregistered', {
        device_id = device_id,
        user_id = user_id
    })

elseif operation == 'sync_state' then
    if not user_id or not device_data then
        return response(false, 'User ID and device data required')
    end
    
    local data = cjson.decode(device_data)
    local device_id = data.device_id
    local sync_type = data.sync_type -- 'push', 'pull', 'full'
    
    -- Get device session
    local session_json = redis.call('GET', device_key .. ':session:' .. device_id)
    if not session_json then
        return response(false, 'Device session not found')
    end
    
    local session = cjson.decode(session_json)
    session.last_activity = now
    
    local sync_result = {
        changes = {},
        conflicts = {},
        timestamp = now
    }
    
    if sync_type == 'push' or sync_type == 'full' then
        -- Handle incoming changes
        if data.changes then
            for key, value in pairs(data.changes) do
                -- Check for conflicts
                local server_version = session.state[key]
                if server_version and server_version.timestamp > value.timestamp then
                    table.insert(sync_result.conflicts, {
                        key = key,
                        server = server_version,
                        client = value
                    })
                else
                    session.state[key] = value
                end
            end
        end
    end
    
    if sync_type == 'pull' or sync_type == 'full' then
        -- Prepare outgoing changes
        sync_result.changes = session.state
    end
    
    -- Update session
    redis.call('SETEX', device_key .. ':session:' .. device_id, session_ttl, cjson.encode(session))
    
    -- Add to sync queue for other devices
    if data.broadcast and #sync_result.changes > 0 then
        local broadcast_msg = {
            type = 'state_update',
            user_id = user_id,
            source_device = device_id,
            changes = sync_result.changes,
            timestamp = now
        }
        redis.call('RPUSH', sync_key .. ':outgoing', cjson.encode(broadcast_msg))
    end
    
    return response(true, 'State synced', sync_result)

elseif operation == 'get_devices' then
    if not user_id then
        return response(false, 'User ID required')
    end
    
    local device_ids = redis.call('SMEMBERS', user_key .. ':devices')
    local devices = {}
    
    for _, device_id in ipairs(device_ids) do
        local device_json = redis.call('GET', device_key .. ':' .. device_id)
        if device_json then
            local device = cjson.decode(device_json)
            
            -- Get device session info
            local session_json = redis.call('GET', device_key .. ':session:' .. device_id)
            if session_json then
                local session = cjson.decode(session_json)
                device.last_activity = session.last_activity
                device.active_session = session.current_session_id
            end
            
            table.insert(devices, device)
        else
            -- Clean up stale device reference
            redis.call('SREM', user_key .. ':devices', device_id)
        end
    end
    
    return response(true, 'Devices retrieved', {
        user_id = user_id,
        count = #devices,
        devices = devices
    })

elseif operation == 'broadcast' then
    if not user_id or not device_data then
        return response(false, 'User ID and message data required')
    end
    
    local data = cjson.decode(device_data)
    local message = {
        id = 'msg_' .. redis.sha1hex(user_id .. now),
        type = data.message_type,
        sender = data.sender_device,
        content = data.content,
        timestamp = now,
        expires = data.expires,
        requires_ack = data.requires_ack or false
    }
    
    -- Get all devices for user
    local device_ids = redis.call('SMEMBERS', user_key .. ':devices')
    local recipients = {}
    
    for _, device_id in ipairs(device_ids) do
        if device_id ~= data.sender_device then
            -- Queue message for each device
            redis.call('RPUSH', device_key .. ':inbox:' .. device_id, cjson.encode(message))
            redis.call('EXPIRE', device_key .. ':inbox:' .. device_id, 3600) -- 1 hour TTL
            
            if message.requires_ack then
                redis.call('HSET', device_key .. ':pending:' .. message.id, device_id, 0)
            end
            
            table.insert(recipients, device_id)
        end
    end
    
    return response(true, 'Message broadcast', {
        message_id = message.id,
        recipients = recipients,
        count = #recipients
    })

elseif operation == 'get_device_session' then
    if not device_data then
        return response(false, 'Device ID required')
    end
    
    local data = cjson.decode(device_data)
    local session_json = redis.call('GET', device_key .. ':session:' .. data.device_id)
    
    if not session_json then
        return response(false, 'Device session not found')
    end
    
    local session = cjson.decode(session_json)
    
    -- Get pending messages
    local inbox = redis.call('LRANGE', device_key .. ':inbox:' .. data.device_id, 0, -1)
    local messages = {}
    for _, msg_json in ipairs(inbox) do
        table.insert(messages, cjson.decode(msg_json))
    end
    
    -- Clear inbox after reading
    redis.call('DEL', device_key .. ':inbox:' .. data.device_id)
    
    return response(true, 'Device session retrieved', {
        session = session,
        pending_messages = messages,
        message_count = #messages
    })
end

return response(false, 'Unknown operation')