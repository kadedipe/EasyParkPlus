from reentrant_lock import ReentrantLock

r_lock = ReentrantLock(r, 'lock:payment:12345', timeout_ms=10000)

def process_payment():
    with r_lock as lock:
        # First level
        update_payment_status()
        
        with lock:  # Reentrant acquisition
            # Second level - same thread can acquire again
            log_payment_audit()

process_payment()