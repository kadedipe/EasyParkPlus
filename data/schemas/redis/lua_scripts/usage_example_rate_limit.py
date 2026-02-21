# Example Python usage for rate_limit.lua
import redis
import time

r = redis.Redis(host='localhost', port=6379, db=0)

# Load the script
with open('rate_limit.lua', 'r') as f:
    rate_limit_script = f.read()

# Register the script
rate_limit_sha = r.script_load(rate_limit_script)

# Function to check rate limit
def check_rate_limit(user_id, limit=100, window=60, strategy='sliding_window'):
    key = f"rate_limit:api:{user_id}"
    now = int(time.time())
    
    result = r.evalsha(
        rate_limit_sha,
        1,  # number of keys
        key,  # KEYS[1]
        limit,  # ARGV[1]
        window,  # ARGV[2]
        now,  # ARGV[3]
        strategy  # ARGV[4]
    )
    
    return {
        'allowed': result[0] == 1,
        'remaining': result[1],
        'reset': result[2],
        'retry_after': result[3],
        'limit': result[4],
        'current': result[5]
    }

# Example usage
result = check_rate_limit('user123', limit=10, window=60)
if result['allowed']:
    print(f"Request allowed. {result['remaining']} remaining")
else:
    print(f"Rate limited. Retry after {result['retry_after']} seconds")