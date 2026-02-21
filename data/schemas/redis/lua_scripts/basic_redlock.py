import redis
import time
import uuid
import threading

class RedLock:
    def __init__(self, redis_connections, resource, timeout_ms=30000, quorum=None):
        """
        Initialize RedLock with multiple Redis connections
        
        Args:
            redis_connections: List of Redis client connections
            resource: Resource name to lock
            timeout_ms: Lock timeout in milliseconds
            quorum: Number of successful responses needed (defaults to majority)
        """
        self.connections = redis_connections
        self.resource = resource
        self.timeout_ms = timeout_ms
        self.quorum = quorum or (len(connections) // 2 + 1)
        self.owner = str(uuid.uuid4())
        self.lock_key = f"redlock:{resource}"
        self.lua_scripts = {}
        
    def _load_scripts(self):
        with open('redlock.lua', 'r') as f:
            script = f.read()
            
        for i, conn in enumerate(self.connections):
            self.lua_scripts[i] = conn.register_script(script)
    
    def acquire(self, retry_count=3, retry_delay_ms=200):
        """
        Acquire lock using RedLock algorithm
        
        Returns:
            dict: Lock info if acquired, None otherwise
        """
        if not self.lua_scripts:
            self._load_scripts()
            
        start_time = int(time.time() * 1000)
        
        for attempt in range(retry_count):
            acquired = []
            errors = []
            now = int(time.time() * 1000)
            
            # Try to acquire on all instances
            for i, conn in enumerate(self.connections):
                try:
                    result = self.lua_scripts[i](
                        keys=[self.lock_key],
                        args=[self.resource, self.owner, self.timeout_ms, now, 'acquire', self.quorum]
                    )
                    
                    if result[b'success'] == 1:
                        acquired.append({
                            'instance': i,
                            'validity': result[b'data'][b'validity'],
                            'expires_at': result[b'data'][b'expires_at']
                        })
                    else:
                        errors.append({
                            'instance': i,
                            'error': result[b'message']
                        })
                        
                except Exception as e:
                    errors.append({'instance': i, 'error': str(e)})
            
            # Check if we have quorum
            if len(acquired) >= self.quorum:
                # Calculate actual validity time (minus elapsed time)
                elapsed = int(time.time() * 1000) - start_time
                validity = self.timeout_ms - elapsed
                
                if validity > 0:
                    return {
                        'acquired': True,
                        'owner': self.owner,
                        'validity': validity,
                        'quorum': len(acquired),
                        'total_instances': len(self.connections),
                        'acquired_instances': acquired,
                        'errors': errors
                    }
            
            # Release any acquired locks
            self.release(acquired_instances=[a['instance'] for a in acquired])
            
            if attempt < retry_count - 1:
                time.sleep(retry_delay_ms / 1000)
        
        return None
    
    def release(self, acquired_instances=None):
        """
        Release the lock on all instances
        """
        if not self.lua_scripts:
            self._load_scripts()
            
        results = []
        now = int(time.time() * 1000)
        
        instances_to_release = acquired_instances or range(len(self.connections))
        
        for i in instances_to_release:
            try:
                result = self.lua_scripts[i](
                    keys=[self.lock_key],
                    args=[self.resource, self.owner, self.timeout_ms, now, 'release', self.quorum]
                )
                results.append({
                    'instance': i,
                    'success': result[b'success'] == 1,
                    'message': result[b'message']
                })
            except Exception as e:
                results.append({'instance': i, 'success': False, 'error': str(e)})
        
        return results
    
    def validate(self):
        """
        Validate if we still hold the lock on majority of instances
        """
        if not self.lua_scripts:
            self._load_scripts()
            
        valid_instances = []
        now = int(time.time() * 1000)
        
        for i, conn in enumerate(self.connections):
            try:
                result = self.lua_scripts[i](
                    keys=[self.lock_key],
                    args=[self.resource, self.owner, self.timeout_ms, now, 'validate', self.quorum]
                )
                
                if result[b'success'] == 1:
                    valid_instances.append(i)
                    
            except Exception:
                pass
        
        return len(valid_instances) >= self.quorum