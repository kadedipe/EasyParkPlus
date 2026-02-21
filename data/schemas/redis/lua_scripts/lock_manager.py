from lock_manager import LockManager

manager = LockManager(r)

# Register a lock
manager.register_lock('lock:space:A12', 'owner:123')

# List all locks
all_locks = manager.list_locks()

# Get statistics
stats = manager.get_stats()

# Clean up stale locks
cleaned = manager.cleanup_stale()