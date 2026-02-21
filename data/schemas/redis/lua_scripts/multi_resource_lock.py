from multi_resource_lock import MultiResourceLock

# Lock multiple parking spaces atomically
multi_lock = MultiResourceLock(r, [
    'lock:space:A12',
    'lock:space:A13',
    'lock:space:A14'
], timeout_ms=20000)

# Acquire all resources
if multi_lock.acquire_all():
    try:
        # Reserve all three spaces together
        reserve_spaces(['A12', 'A13', 'A14'])
    finally:
        multi_lock.release_all()

# Or acquire any 2 of them
if multi_lock.acquire_any(min_count=2):
    try:
        # Proceed with partial reservation
        pass
    finally:
        multi_lock.release_all()