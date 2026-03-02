import redis
import time
import uuid

class DistributedLock:
    def __init__(self, redis_client, lock_key, timeout_ms=30000):
        self.redis = redis_client
        self.lock_key = lock_key
        self.timeout_ms = timeout_ms
        self.owner = str(uuid.uuid4())
        self.lua_script = None
        
    def _load_script(self):
        with open('distributed_lock.lua', 'r') as f:
            self.lua_script = self.redis.register_script(f.read())
    
    def acquire(self, block=True, retry_interval_ms=100):
        if not self.lua_script:
            self._load_script()
            
        now = int(time.time() * 1000)
        
        while True:
            result = self.lua_script(
                keys=[self.lock_key],
                args=[self.owner, self.timeout_ms, now, 'acquire']
            )
            
            if result[b'success'] == 1:
                return True
                
            if not block:
                return False
                
            # Wait for retry_interval or until lock expires
            retry_after = result.get(b'data', {}).get(b'retry_after', retry_interval_ms)
            time.sleep(min(retry_after, retry_interval_ms) / 1000)
    
    def release(self):
        if not self.lua_script:
            self._load_script()
            
        now = int(time.time() * 1000)
        result = self.lua_script(
            keys=[self.lock_key],
            args=[self.owner, self.timeout_ms, now, 'release']
        )
        
        return result[b'success'] == 1
    
    def renew(self):
        if not self.lua_script:
            self._load_script()
            
        now = int(time.time() * 1000)
        result = self.lua_script(
            keys=[self.lock_key],
            args=[self.owner, self.timeout_ms, now, 'renew']
        )
        
        return result[b'success'] == 1
    
    def check(self):
        if not self.lua_script:
            self._load_script()
            
        now = int(time.time() * 1000)
        result = self.lua_script(
            keys=[self.lock_key],
            args=[self.owner, self.timeout_ms, now, 'check']
        )
        
        return {
            'is_owner': result[b'success'] == 1,
            'owner': result.get(b'data', {}).get(b'owner'),
            'ttl': result.get(b'data', {}).get(b'ttl', 0)
        }