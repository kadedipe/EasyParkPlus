-- session_token.lua
-- Manages session tokens with JWT-like capabilities in Redis

-- KEYS[1] = token key (e.g., "token:{tokenId}")
-- KEYS[2] = user tokens set
-- KEYS[3] = revoked tokens set
-- ARGV[1] = operation: 'create', 'validate', 'revoke', 'refresh', 'list_user_tokens', 'cleanup'
-- ARGV[2] = token data (JSON string)
-- ARGV[3] = token ID
-- ARGV[4] = current timestamp
-- ARGV[5] = token TTL

local token_key = KEYS[1]
local user_tokens = KEYS[2]
local revoked_set = KEYS[3] or 'tokens:revoked'
local operation = ARGV[1]
local token_data = ARGV[2]
local token_id = ARGV[3]
local now = tonumber(ARGV[4]) or redis.call('TIME')[1]
local token_ttl = tonumber(ARGV[5]) or 3600

local function response(success, message, data)
    return {success = success and 1 or 0, message = message, data = data}
end

-- Generate a unique token ID
local function generate_token_id()
    return 'tok_' .. redis.sha1hex(redis.call('TIME')[1] .. ':' .. redis.call('INCR', 'token:counter'))
end

-- Create token hash with claims
local function create_token_hash(data, expires_at)
    local claims = {
        jti = data.jti or generate_token_id(),
        iss = data.iss or 'parking-system',
        sub = data.sub,
        aud = data.aud,
        exp = expires_at,
        iat = now,
        nbf = data.nbf or now,
        user_id = data.user_id,
        role = data.role,
        permissions = data.permissions,
        metadata = data.metadata or {}
    }
    
    -- Create signature (simplified - in production use proper JWT)
    local header = cjson.encode({alg = 'HS256', typ = 'JWT'})
    local payload = cjson.encode(claims)
    local signature = redis.sha1hex(header .. payload .. 'secret-key')
    
    return {
        token = header .. '.' .. payload .. '.' .. signature,
        claims = claims,
        jti = claims.jti
    }
end

if operation == 'create' then
    if not token_data then
        return response(false, 'Token data required')
    end
    
    local data = cjson.decode(token_data)
    local expires_at = now + token_ttl
    
    -- Create token
    local token_info = create_token_hash(data, expires_at)
    local token_id = token_info.jti
    
    -- Store token data
    local token_record = {
        jti = token_id,
        token = token_info.token,
        user_id = data.user_id,
        created_at = now,
        expires_at = expires_at,
        last_used = now,
        usage_count = 0,
        metadata = data.metadata or {},
        revoked = false
    }
    
    redis.call('SETEX', token_key .. ':' .. token_id, token_ttl, cjson.encode(token_record))
    
    -- Add to user's tokens set
    if data.user_id then
        redis.call('ZADD', user_tokens .. ':' .. data.user_id, expires_at, token_id)
    end
    
    return response(true, 'Token created', {
        token_id = token_id,
        token = token_info.token,
        expires_at = expires_at,
        ttl = token_ttl
    })

elseif operation == 'validate' then
    if not token_id then
        return response(false, 'Token ID required')
    end
    
    -- Check if revoked
    if redis.call('SISMEMBER', revoked_set, token_id) == 1 then
        return response(false, 'Token has been revoked')
    end
    
    local token_record_json = redis.call('GET', token_key .. ':' .. token_id)
    
    if not token_record_json then
        return response(false, 'Token not found or expired')
    end
    
    local token_record = cjson.decode(token_record_json)
    
    -- Check expiration
    if token_record.expires_at < now then
        redis.call('DEL', token_key .. ':' .. token_id)
        return response(false, 'Token expired')
    end
    
    -- Update usage metrics
    token_record.last_used = now
    token_record.usage_count = (token_record.usage_count or 0) + 1
    redis.call('SETEX', token_key .. ':' .. token_id, token_record.expires_at - now, cjson.encode(token_record))
    
    return response(true, 'Token valid', token_record)

elseif operation == 'revoke' then
    if not token_id then
        return response(false, 'Token ID required')
    end
    
    local reason = token_data and cjson.decode(token_data).reason or 'user_initiated'
    
    -- Add to revoked set
    redis.call('SADD', revoked_set, token_id)
    redis.call('EXPIRE', revoked_set, 86400 * 30) -- Keep revocation records for 30 days
    
    -- Store revocation info
    local revocation = {
        token_id = token_id,
        revoked_at = now,
        reason = reason,
        revoked_by = token_data and cjson.decode(token_data).revoked_by
    }
    redis.call('SETEX', 'token:revoked:' .. token_id, 86400 * 30, cjson.encode(revocation))
    
    -- Delete token
    local token_record_json = redis.call('GET', token_key .. ':' .. token_id)
    redis.call('DEL', token_key .. ':' .. token_id)
    
    if token_record_json then
        local token_record = cjson.decode(token_record_json)
        
        -- Remove from user's tokens set
        if token_record.user_id then
            redis.call('ZREM', user_tokens .. ':' .. token_record.user_id, token_id)
        end
        
        return response(true, 'Token revoked', {
            token_id = token_id,
            user_id = token_record.user_id,
            reason = reason
        })
    end
    
    return response(true, 'Token revoked (not found)', {
        token_id = token_id,
        reason = reason
    })

elseif operation == 'refresh' then
    if not token_id then
        return response(false, 'Token ID required')
    end
    
    local token_record_json = redis.call('GET', token_key .. ':' .. token_id)
    
    if not token_record_json then
        return response(false, 'Token not found or expired')
    end
    
    local token_record = cjson.decode(token_record_json)
    
    -- Check if token is eligible for refresh (e.g., within refresh window)
    local refresh_window = token_ttl * 0.2 -- 20% of original TTL
    if token_record.expires_at - now > refresh_window then
        return response(false, 'Token still valid, refresh not needed', {
            expires_in = token_record.expires_at - now
        })
    end
    
    -- Create new token
    local new_token_id = generate_token_id()
    local new_expires = now + token_ttl
    
    local new_token_record = {
        jti = new_token_id,
        user_id = token_record.user_id,
        created_at = now,
        expires_at = new_expires,
        metadata = token_record.metadata,
        refreshed_from = token_id
    }
    
    redis.call('SETEX', token_key .. ':' .. new_token_id, token_ttl, cjson.encode(new_token_record))
    
    -- Update user's tokens
    if token_record.user_id then
        redis.call('ZADD', user_tokens .. ':' .. token_record.user_id, new_expires, new_token_id)
    end
    
    -- Optionally revoke old token
    if token_data and cjson.decode(token_data).revoke_old then
        redis.call('SADD', revoked_set, token_id)
    end
    
    return response(true, 'Token refreshed', {
        old_token_id = token_id,
        new_token_id = new_token_id,
        expires_at = new_expires
    })

elseif operation == 'list_user_tokens' then
    if not token_data then
        return response(false, 'User ID required')
    end
    
    local data = cjson.decode(token_data)
    local user_id = data.user_id
    local include_revoked = data.include_revoked or false
    
    local token_ids = redis.call('ZRANGE', user_tokens .. ':' .. user_id, 0, -1)
    local tokens = {}
    
    for _, tid in ipairs(token_ids) do
        if include_revoked or redis.call('SISMEMBER', revoked_set, tid) == 0 then
            local token_json = redis.call('GET', token_key .. ':' .. tid)
            if token_json then
                table.insert(tokens, cjson.decode(token_json))
            end
        end
    end
    
    return response(true, 'User tokens retrieved', {
        user_id = user_id,
        count = #tokens,
        tokens = tokens
    })

elseif operation == 'cleanup' then
    -- Clean up expired tokens
    local cleaned = 0
    local cursor = '0'
    
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', token_key .. ':*', 'COUNT', 100)
        cursor = result[1]
        
        for _, key in ipairs(result[2]) do
            local token_json = redis.call('GET', key)
            if token_json then
                local token = cjson.decode(token_json)
                if token.expires_at < now then
                    redis.call('DEL', key)
                    
                    -- Remove from user's set
                    if token.user_id then
                        redis.call('ZREM', user_tokens .. ':' .. token.user_id, token.jti)
                    end
                    
                    cleaned = cleaned + 1
                end
            end
        end
    until cursor == '0'
    
    return response(true, 'Cleanup completed', {
        cleaned = cleaned
    })
end

return response(false, 'Unknown operation')