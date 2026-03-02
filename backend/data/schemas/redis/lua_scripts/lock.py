import redis
import time
from distributed_lock import DistributedLock

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Create a lock for parking space A12
lock = DistributedLock(r, 'lock:space:A12', timeout_ms=30000)

# Try to acquire the lock
if lock.acquire(block=True):
    try:
        # Critical section - reserve the parking space
        print("Lock acquired, performing critical operation")
        time.sleep(5)
    finally:
        # Always release the lock
        lock.release()
else:
    print("Failed to acquire lock")