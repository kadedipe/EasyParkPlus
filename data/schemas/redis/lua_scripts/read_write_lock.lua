-- read_write_lock.lua
-- Read/Write lock implementation for concurrent access control

-- KEYS[1] = lock metadata key
-- KEYS[2] = read locks hash
-- KEYS[3] = write lock key
-- ARGV[1] = owner identifier
-- ARGV[2] = lock type: 'read' or 'write'
-- ARGV[3] = timeout in milliseconds
-- ARGV[4] = current timestamp
-- ARGV[5] = operation: 'acquire', 'release', 'upgrade', 'downgrade'

local meta_key = KEYS[1]
local reads_key = KEYS[2]
local write_key = KEYS[3]
local owner = ARGV[1]
local lock_type = ARGV[2]
local timeout = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local operation = ARGV[5]

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Initialize metadata if not exists
redis.call('HSETNX', meta_key, 'write_owner', '')
redis.call('HSETNX', meta_key, 'write_count', 0)
redis.call('HSETNX', meta_key, 'read_count', 0)
redis.call('PEXPIRE', meta_key, timeout)

if operation == 'acquire' then
    if lock_type == 'read' then
        -- Check if write lock is held by someone else
        local write_owner = redis.call('HGET', meta_key, 'write_owner')
        local write_count = tonumber(redis.call('HGET', meta_key, 'write_count')) or 0
        
        if write_count > 0 and write_owner ~= owner then
            return response(false, 'Write lock held by another', {
                write_owner = write_owner
            })
        end
        
        -- Acquire read lock
        local read_count = redis.call('HINCRBY', meta_key, 'read_count', 1)
        redis.call('HSET', reads_key, owner, 1)
        redis.call('PEXPIRE', reads_key, timeout)
        
        return response(true, 'Read lock acquired', {
            read_count = read_count,
            read_owners = redis.call('HGETALL', reads_key)
        })
        
    elseif lock_type == 'write' then
        -- Check if any read locks exist (excluding our own)
        local read_count = tonumber(redis.call('HGET', meta_key, 'read_count')) or 0
        local our_reads = tonumber(redis.call('HGET', reads_key, owner)) or 0
        
        if read_count > our_reads then
            return response(false, 'Read locks exist', {
                read_count = read_count,
                our_reads = our_reads
            })
        end
        
        -- Check if write lock is held by someone else
        local write_owner = redis.call('HGET', meta_key, 'write_owner')
        local write_count = tonumber(redis.call('HGET', meta_key, 'write_count')) or 0
        
        if write_count > 0 and write_owner ~= owner then
            return response(false, 'Write lock held by another', {
                write_owner = write_owner
            })
        end
        
        -- Acquire write lock
        local new_count = redis.call('HINCRBY', meta_key, 'write_count', 1)
        redis.call('HSET', meta_key, 'write_owner', owner)
        redis.call('PEXPIRE', meta_key, timeout)
        
        return response(true, 'Write lock acquired', {
            write_count = new_count
        })
    end

elseif operation == 'release' then
    if lock_type == 'read' then
        local our_reads = tonumber(redis.call('HGET', reads_key, owner)) or 0
        
        if our_reads > 0 then
            if our_reads == 1 then
                redis.call('HDEL', reads_key, owner)
            else
                redis.call('HINCRBY', reads_key, owner, -1)
            end
            
            local read_count = redis.call('HINCRBY', meta_key, 'read_count', -1)
            
            return response(true, 'Read lock released', {
                remaining_reads = read_count
            })
        else
            return response(false, 'No read lock held')
        end
        
    elseif lock_type == 'write' then
        local write_owner = redis.call('HGET', meta_key, 'write_owner')
        local write_count = tonumber(redis.call('HGET', meta_key, 'write_count')) or 0
        
        if write_owner == owner and write_count > 0 then
            local new_count = redis.call('HINCRBY', meta_key, 'write_count', -1)
            
            if new_count == 0 then
                redis.call('HSET', meta_key, 'write_owner', '')
            end
            
            return response(true, 'Write lock released', {
                remaining_writes = new_count
            })
        else
            return response(false, 'No write lock held')
        end
    end

elseif operation == 'upgrade' then
    -- Upgrade read lock to write lock
    local our_reads = tonumber(redis.call('HGET', reads_key, owner)) or 0
    
    if our_reads == 0 then
        return response(false, 'No read lock to upgrade')
    end
    
    -- Check if any other read locks exist
    local total_reads = tonumber(redis.call('HGET', meta_key, 'read_count')) or 0
    
    if total_reads > our_reads {
        return response(false, 'Cannot upgrade - other readers exist', {
            other_readers = total_reads - our_reads
        })
    }
    
    -- Release all read locks
    redis.call('HDEL', reads_key, owner)
    redis.call('HSET', meta_key, 'read_count', 0)
    
    -- Acquire write lock
    redis.call('HINCRBY', meta_key, 'write_count', 1)
    redis.call('HSET', meta_key, 'write_owner', owner)
    
    return response(true, 'Lock upgraded to write')

elseif operation == 'downgrade' then
    -- Downgrade write lock to read lock
    local write_owner = redis.call('HGET', meta_key, 'write_owner')
    local write_count = tonumber(redis.call('HGET', meta_key, 'write_count')) or 0
    
    if write_owner ~= owner or write_count == 0 {
        return response(false, 'No write lock to downgrade')
    }
    
    -- Release write lock
    redis.call('HINCRBY', meta_key, 'write_count', -1)
    if redis.call('HGET', meta_key, 'write_count') == 0 {
        redis.call('HSET', meta_key, 'write_owner', '')
    }
    
    -- Acquire read lock
    redis.call('HINCRBY', meta_key, 'read_count', 1)
    redis.call('HINCRBY', reads_key, owner, 1)
    
    return response(true, 'Lock downgraded to read')
end

return response(false, 'Unknown operation')