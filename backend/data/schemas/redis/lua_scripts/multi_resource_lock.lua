-- multi_resource_lock.lua
-- Lock that can acquire multiple resources atomically

-- KEYS = list of resource keys to lock
-- ARGV[1] = owner identifier
-- ARGV[2] = timeout in milliseconds
-- ARGV[3] = current timestamp
-- ARGV[4] = operation: 'acquire_all', 'release_all', 'acquire_any', 'check_held'

local owner = ARGV[1]
local timeout = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local operation = ARGV[4]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Helper to check if we own a specific resource
local function is_owner(key)
    return redis.call('GET', key) == owner
end

-- Helper to acquire a single resource
local function acquire_resource(key)
    return redis.call('SET', key, owner, 'NX', 'PX', timeout)
end

-- Helper to release a single resource
local function release_resource(key)
    if is_owner(key) then
        redis.call('DEL', key)
        return true
    end
    return false
end

if operation == 'acquire_all' then
    local acquired = {}
    local failed = {}
    
    -- Try to acquire all resources
    for i, key in ipairs(KEYS) do
        if acquire_resource(key) then
            table.insert(acquired, key)
        else
            table.insert(failed, {
                resource = key,
                owner = redis.call('GET', key),
                ttl = redis.call('PTTL', key)
            })
        end
    end
    
    -- If any failed, release all acquired resources
    if #failed > 0 then
        for _, key in ipairs(acquired) do
            release_resource(key)
        end
        
        return response(false, 'Failed to acquire all resources', {
            acquired = acquired,
            failed = failed
        })
    end
    
    return response(true, 'All resources acquired', {
        resources = acquired,
        count = #acquired
    })

elseif operation == 'release_all' then
    local released = {}
    local not_owned = {}
    
    for i, key in ipairs(KEYS) do
        if release_resource(key) then
            table.insert(released, key)
        else
            table.insert(not_owned, {
                resource = key,
                owner = redis.call('GET', key)
            })
        end
    end
    
    return response(true, 'Resources released', {
        released = released,
        not_owned = not_owned
    })

elseif operation == 'acquire_any' then
    local min_count = tonumber(ARGV[5]) or 1
    local acquired = {}
    local failed = {}
    
    -- Shuffle keys to prevent starvation
    local shuffled = {}
    for i, key in ipairs(KEYS) do
        table.insert(shuffled, key)
    end
    
    -- Simple shuffle
    for i = #shuffled, 2, -1 do
        local j = math.random(i)
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    end
    
    -- Try to acquire resources
    for _, key in ipairs(shuffled) do
        if acquire_resource(key) then
            table.insert(acquired, key)
            if #acquired >= min_count then
                break
            end
        else
            table.insert(failed, {
                resource = key,
                owner = redis.call('GET', key)
            })
        end
    end
    
    if #acquired >= min_count then
        return response(true, 'Minimum resources acquired', {
            acquired = acquired,
            count = #acquired,
            failed = failed
        })
    else
        -- Release any acquired resources
        for _, key in ipairs(acquired) do
            release_resource(key)
        end
        
        return response(false, 'Could not acquire minimum resources', {
            acquired = acquired,
            failed = failed,
            needed = min_count,
            got = #acquired
        })
    end

elseif operation == 'check_held' then
    local held = {}
    local free = {}
    local owned_by_other = {}
    
    for i, key in ipairs(KEYS) do
        local current_owner = redis.call('GET', key)
        if not current_owner then
            table.insert(free, key)
        elseif current_owner == owner then
            table.insert(held, {
                resource = key,
                ttl = redis.call('PTTL', key)
            })
        else
            table.insert(owned_by_other, {
                resource = key,
                owner = current_owner,
                ttl = redis.call('PTTL', key)
            })
        end
    end
    
    return response(true, 'Resource status', {
        held = held,
        free = free,
        owned_by_other = owned_by_other
    })
end

return response(false, 'Unknown operation')