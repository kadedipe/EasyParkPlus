-- session_migration.lua
-- Tools for migrating sessions between Redis instances or versions

-- KEYS[1] = source key
-- KEYS[2] = destination key
-- KEYS[3] = migration log key
-- ARGV[1] = operation: 'export', 'import', 'validate', 'rollback', 'status'
-- ARGV[2] = parameters (JSON string)
-- ARGV[3] = current timestamp

local source_key = KEYS[1]
local dest_key = KEYS[2]
local log_key = KEYS[3] or 'migration:log'
local operation = ARGV[1]
local params = cjson.decode(ARGV[2] or '{}')
local now = tonumber(ARGV[3]) or redis.call('TIME')[1]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Helper to log migration events
local function log_migration(action, details, status)
    local log_entry = {
        timestamp = now,
        action = action,
        details = details,
        status = status
    }
    
    redis.call('LPUSH', log_key, cjson.encode(log_entry))
    redis.call('LTRIM', log_key, 0, 999)
end

if operation == 'export' then
    -- Export sessions to a serializable format
    local pattern = params.pattern or 'session:*'
    local batch_size = params.batch_size or 100
    local format = params.format or 'json' -- 'json', 'msgpack', 'csv'
    
    local exported = {
        metadata = {
            version = '1.0',
            exported_at = now,
            source_instance = params.instance_id or 'unknown',
            count = 0,
            format = format
        },
        sessions = {}
    }
    
    local cursor = '0'
    local total = 0
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', pattern, 'COUNT', batch_size)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local type = redis.call('TYPE', key)
            local value = nil
            local ttl = redis.call('TTL', key)
            
            if type == 'string' then
                value = redis.call('GET', key)
            elseif type == 'hash' then
                value = redis.call('HGETALL', key)
            elseif type == 'set' then
                value = redis.call('SMEMBERS', key)
            elseif type == 'zset' then
                value = redis.call('ZRANGE', key, 0, -1, 'WITHSCORES')
            end
            
            if value then
                table.insert(exported.sessions, {
                    key = key,
                    type = type,
                    value = value,
                    ttl = ttl,
                    exported_at = now
                })
                total = total + 1
            end
        end
    until cursor == '0' or total >= (params.max_items or 10000)
    
    exported.metadata.count = total
    
    -- Store export data
    local export_id = 'export_' .. redis.sha1hex(now .. params.instance_id)
    redis.call('SETEX', 'migration:export:' .. export_id, 86400, cjson.encode(exported))
    
    log_migration('export', {count = total, export_id = export_id}, 'success')
    
    return response(true, 'Export completed', {
        export_id = export_id,
        count = total,
        metadata = exported.metadata
    })

elseif operation == 'import' then
    -- Import sessions from exported data
    local export_id = params.export_id
    local validate_only = params.validate_only or false
    local conflict_strategy = params.conflict_strategy or 'skip' -- 'skip', 'overwrite', 'merge'
    
    if not export_id then
        return response(false, 'Export ID required')
    end
    
    local export_json = redis.call('GET', 'migration:export:' .. export_id)
    if not export_json then
        return response(false, 'Export not found')
    end
    
    local export = cjson.decode(export_json)
    local imported = 0
    local skipped = 0
    val errors = {}
    
    for _, item in ipairs(export.sessions) do
        -- Check for existing key
        local exists = redis.call('EXISTS', item.key) == 1
        
        if exists and conflict_strategy == 'skip' then
            skipped = skipped + 1
            table.insert(errors, {
                key = item.key,
                error = 'key_exists',
                action = 'skipped'
            })
        else
            -- Import based on type
            local success = false
            
            if not validate_only then
                if item.type == 'string' then
                    success = redis.call('SET', item.key, item.value)
                elseif item.type == 'hash' then
                    success = redis.call('HSET', item.key, unpack(item.value))
                elseif item.type == 'set' then
                    success = redis.call('SADD', item.key, unpack(item.value))
                elseif item.type == 'zset' then
                    local args = {}
                    for i = 1, #item.value, 2 do
                        table.insert(args, item.value[i+1])
                        table.insert(args, item.value[i])
                    end