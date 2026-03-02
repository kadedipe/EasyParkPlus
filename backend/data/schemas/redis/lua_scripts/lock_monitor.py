from lock_monitor import LockMonitor

monitor = LockMonitor(r)

# Record lock events
monitor.record_event(
    lock_key='lock:space:A12',
    owner='owner:123',
    event_type='acquire',
    success=True,
    duration=150
)

# Get contention statistics
contention = monitor.get_contention()

# Analyze potential deadlocks
deadlocks = monitor.analyze_deadlock()

# Health check
health = monitor.health_check()