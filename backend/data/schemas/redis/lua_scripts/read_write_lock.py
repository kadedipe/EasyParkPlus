from read_write_lock import ReadWriteLock

rw_lock = ReadWriteLock(r, 'lock:config:rates')

# Multiple readers can access simultaneously
def read_rates():
    with rw_lock.read_lock():
        return get_rates_from_db()

def update_rates():
    with rw_lock.write_lock():
        # Exclusive access
        update_rates_in_db()