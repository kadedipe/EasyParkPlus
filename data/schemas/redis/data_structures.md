Redis Data Structures for Parking Management System
Overview
This document outlines the Redis data structures used in the parking management system. Redis is used for caching, rate limiting, real-time tracking, and session management to ensure high performance and scalability.

Table of Contents
String Data Structures

Hash Data Structures

List Data Structures

Set Data Structures

Sorted Set Data Structures

Geo Data Structures

HyperLogLog Data Structures

Bitmap Data Structures

Stream Data Structures

Key Naming Conventions

Expiration Policies

Memory Optimization

Backup and Persistence

Monitoring and Metrics

String Data Structures
1. Session Tokens
redis
# Format: session:{token}
# Type: String with JSON data
# TTL: 24 hours

SET session:abc123def456 '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "role": "attendant",
    "organization_id": "123e4567-e89b-12d3-a456-426614174000",
    "permissions": ["parking:read", "parking:write"],
    "created_at": "2024-01-15T10:30:00Z",
    "last_activity": "2024-01-15T14:45:00Z",
    "ip_address": "192.168.1.100"
}' EX 86400
2. Rate Limit Counters
redis
# Format: ratelimit:{endpoint}:{user_id}:{date}
# Type: String (integer)
# TTL: End of day

SET ratelimit:api:user123:2024-01-15 42
EXPIRE ratelimit:api:user123:2024-01-15 3600

# Distributed rate limit tracking
SET ratelimit:global:api:2024-01-15 1500
EXPIRE ratelimit:global:api:2024-01-15 86400
3. Configuration Values
redis
# Format: config:{category}:{key}
# Type: String (JSON)

SET config:parking:rates '{
    "standard": 2.50,
    "premium": 5.00,
    "electric": 3.00,
    "handicapped": 1.50,
    "currency": "USD",
    "tax_rate": 0.10
}'

SET config:system:features '{
    "enable_lpr": true,
    "enable_pre_payment": true,
    "max_reservation_days": 30,
    "grace_period_minutes": 15
}'
4. Lock Keys (Distributed Locks)
redis
# Format: lock:{resource}:{operation}
# Type: String (owner ID)
# TTL: 30 seconds (with auto-release)

SET lock:parking_space:A12:reserve "session:abc123" NX EX 30
SET lock:payment:session:12345 "txn_9876" NX EX 10
5. Counter Keys
redis
# Format: counter:{entity}:{type}:{date}
# Type: String (integer)

INCR counter:vehicles:entered:2024-01-15
INCR counter:payments:processed:2024-01-15
INCR counter:reservations:cancelled:2024-01-15
Hash Data Structures
1. User Profiles (Cached)
redis
# Format: user:{user_id}
# Type: Hash
# TTL: 1 hour

HMSET user:550e8400-e29b-41d4-a716-446655440000 \
    username "john_doe" \
    email "john@example.com" \
    first_name "John" \
    last_name "Doe" \
    role "attendant" \
    organization_id "123e4567-e89b-12d3-a456-426614174000" \
    permissions "[\"parking:read\", \"parking:write\"]" \
    last_login "2024-01-15T10:30:00Z" \
    login_count "156" \
    status "active"
EXPIRE user:550e8400-e29b-41d4-a716-446655440000 3600
2. Parking Lot Status
redis
# Format: lot:{lot_id}:status
# Type: Hash
# TTL: 5 minutes (real-time data)

HMSET lot:LOT001:status \
    name "Downtown Parking" \
    total_spaces "500" \
    available_spaces "127" \
    reserved_spaces "23" \
    occupancy_rate "74.6" \
    status "operational" \
    last_updated "2024-01-15T14:45:00Z" \
    peak_hour "17:00" \
    today_entries "342" \
    today_exits "298"

HMSET lot:LOT001:levels:1 \
    total "100" \
    available "45" \
    electric_available "3" \
    handicapped_available "2"
3. Active Parking Sessions
redis
# Format: session:active:{session_id}
# Type: Hash
# TTL: Session duration + grace period

HMSET session:active:SESS123456 \
    vehicle_id "VEH789" \
    license_plate "ABC123" \
    entry_time "2024-01-15T13:30:00Z" \
    parking_space_id "SPACE-A12" \
    parking_lot_id "LOT001" \
    rate_id "RATE001" \
    estimated_duration "120" \
    estimated_amount "5.00" \
    entry_image_url "https://storage.example.com/sessions/SESS123456/entry.jpg" \
    entry_lpr_confidence "0.98"
4. Vehicle Information (Cached)
redis
# Format: vehicle:{license_plate_normalized}
# Type: Hash
# TTL: 24 hours

HMSET vehicle:ABC123 \
    vehicle_id "VEH789" \
    make "Toyota" \
    model "Camry" \
    color "Silver" \
    year "2022" \
    vehicle_type "car" \
    is_electric "0" \
    is_handicapped "0" \
    owner_id "550e8400-e29b-41d4-a716-446655440000" \
    owner_name "John Doe" \
    total_visits "23" \
    last_visit "2024-01-10T09:15:00Z" \
    blacklisted "0"
5. Rate Configuration
redis
# Format: rate:{rate_id}
# Type: Hash
# TTL: Until rate changes (cached from DB)

HMSET rate:RATE001 \
    name "Standard Hourly" \
    rate_type "hourly" \
    base_rate "2.50" \
    currency "USD" \
    vehicle_types "[\"car\", \"suv\"]" \
    time_rules "{\"weekday\": \"0-23\", \"weekend\": \"0-23\"}" \
    is_active "1" \
    grace_period "15"
6. Gate Status
redis
# Format: gate:{gate_id}:status
# Type: Hash
# TTL: 1 minute

HMSET gate:GATE001:status \
    name "Main Entrance" \
    status "open" \
    mode "automatic" \
    last_activity "2024-01-15T14:48:00Z" \
    last_vehicle "ABC123" \
    today_opens "234" \
    today_closes "198" \
    error_count "0"
List Data Structures
1. Recent Activity Log
redis
# Format: activity:recent:{entity_type}
# Type: List (LPUSH/LTRIM)
# Max length: 1000

LPUSH activity:recent:sessions '{
    "session_id": "SESS123456",
    "vehicle": "ABC123",
    "action": "entry",
    "timestamp": "2024-01-15T14:48:00Z",
    "lot": "LOT001"
}'
LTRIM activity:recent:sessions 0 999

LPUSH activity:recent:payments '{
    "payment_id": "PAY789",
    "amount": "5.00",
    "method": "credit_card",
    "timestamp": "2024-01-15T14:45:00Z"
}'
LTRIM activity:recent:payments 0 499
2. Notification Queue
redis
# Format: queue:notifications:{priority}
# Type: List (RPUSH for queue, LPOP for processing)

RPUSH queue:notifications:high '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "session_expiring",
    "title": "Parking session expiring soon",
    "message": "Your session will expire in 15 minutes",
    "created_at": "2024-01-15T14:45:00Z"
}'

RPUSH queue:notifications:normal '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "payment_receipt",
    "title": "Payment received",
    "message": "Thank you for your payment of $5.00",
    "created_at": "2024-01-15T14:46:00Z"
}'
3. Event Processing Queue
redis
# Format: queue:events:{type}
# Type: List

RPUSH queue:events:lpr '{
    "camera_id": "CAM001",
    "plate": "ABC123",
    "confidence": 0.98,
    "timestamp": "2024-01-15T14:48:00Z",
    "image_url": "https://storage.example.com/cameras/CAM001/2024-01-15/14-48-00.jpg"
}'

RPUSH queue:events:sensor '{
    "sensor_id": "SENSOR-A12",
    "space_id": "SPACE-A12",
    "occupied": true,
    "timestamp": "2024-01-15T14:48:00Z"
}'
4. Audit Trail Buffer
redis
# Format: audit:buffer:{date}
# Type: List
# TTL: 1 hour (before being written to DB)

LPUSH audit:buffer:2024-01-15 '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "SESSION_START",
    "entity_type": "parking_session",
    "entity_id": "SESS123456",
    "timestamp": "2024-01-15T14:48:00Z",
    "ip_address": "192.168.1.100"
}'
EXPIRE audit:buffer:2024-01-15 3600
5. Command History
redis
# Format: history:commands:{user_id}
# Type: List
# Max length: 50

LPUSH history:commands:550e8400-e29b-41d4-a716-446655440000 '{
    "command": "end_session",
    "params": {"session_id": "SESS123456"},
    "timestamp": "2024-01-15T14:50:00Z",
    "result": "success"
}'
LTRIM history:commands:550e8400-e29b-41d4-a716-446655440000 0 49
Set Data Structures
1. Online Users/Attendants
redis
# Format: online:{organization_id}:{role}
# Type: Set
# TTL: Updated with heartbeat

SADD online:ORG001:attendants "user:550e8400-e29b-41d4-a716-446655440000"
SADD online:ORG001:managers "user:660e8400-e29b-41d4-a716-446655440000"
EXPIRE online:ORG001:attendants 300
EXPIRE online:ORG001:managers 300

# Heartbeat update (every 2 minutes)
SADD online:ORG001:attendants "user:550e8400-e29b-41d4-a716-446655440000"
EXPIRE online:ORG001:attendants 300
2. Active Vehicle Tags/RFIDs
redis
# Format: active:tags:{lot_id}
# Type: Set

SADD active:tags:LOT001 "RFID:123456789"
SADD active:tags:LOT001 "RFID:987654321"
SADD active:tags:LOT001 "TAG:ABC123"
3. Blacklisted Vehicles (Quick Lookup)
redis
# Format: blacklist:{organization_id}
# Type: Set
# TTL: Until next sync

SADD blacklist:ORG001 "ABC123"
SADD blacklist:ORG001 "XYZ789"
SADD blacklist:ORG001 "DEF456"
4. Reserved Parking Spaces
redis
# Format: reserved:spaces:{lot_id}:{date}
# Type: Set
# TTL: End of day

SADD reserved:spaces:LOT001:2024-01-15 "SPACE-A12"
SADD reserved:spaces:LOT001:2024-01-15 "SPACE-B05"
SADD reserved:spaces:LOT001:2024-01-15 "SPACE-C10"
EXPIRE reserved:spaces:LOT001:2024-01-15 86400
5. User Permissions (Denormalized)
redis
# Format: permissions:{user_id}
# Type: Set

SADD permissions:550e8400-e29b-41d4-a716-446655440000 "parking:read"
SADD permissions:550e8400-e29b-41d4-a716-446655440000 "parking:write"
SADD permissions:550e8400-e29b-41d4-a716-446655440000 "reports:read"
SADD permissions:550e8400-e29b-41d4-a716-446655440000 "users:read"
6. Feature Flags
redis
# Format: features:enabled:{organization_id}
# Type: Set

SADD features:enabled:ORG001 "lpr"
SADD features:enabled:ORG001 "pre_payment"
SADD features:enabled:ORG001 "reservations"
SADD features:enabled:ORG001 "dynamic_pricing"
Sorted Set Data Structures
1. Leaderboard - Top Users by Activity
redis
# Format: leaderboard:activity:{period} (daily, weekly, monthly)
# Type: Sorted Set (score = activity count)

# Daily leaderboard
ZINCRBY leaderboard:daily:2024-01-15 1 "user:550e8400-e29b-41d4-a716-446655440000"
ZINCRBY leaderboard:daily:2024-01-15 1 "user:660e8400-e29b-41d4-a716-446655440000"

# Weekly leaderboard
ZINCRBY leaderboard:weekly:2024-W03 1 "user:550e8400-e29b-41d4-a716-446655440000"

# Get top 10
ZREVRANGE leaderboard:daily:2024-01-15 0 9 WITHSCORES
2. Session Expiry Tracking
redis
# Format: sessions:expiring:{lot_id}
# Type: Sorted Set (score = expiry timestamp)

# Add session with expiry time
ZADD sessions:expiring:LOT001 1705333800 "session:SESS123456"
ZADD sessions:expiring:LOT001 1705337400 "session:SESS123457"

# Get sessions expiring in next 15 minutes
ZRANGEBYSCORE sessions:expiring:LOT001 -inf 1705334700

# Remove expired session
ZREM sessions:expiring:LOT001 "session:SESS123456"
3. Reservation Timeline
redis
# Format: reservations:timeline:{lot_id}:{date}
# Type: Sorted Set (score = start time)

ZADD reservations:timeline:LOT001:2024-01-15 1705334400 "res:RES123456"
ZADD reservations:timeline:LOT001:2024-01-15 1705341600 "res:RES123457"
ZADD reservations:timeline:LOT001:2024-01-15 1705348800 "res:RES123458"

# Get reservations for a time range
ZRANGEBYSCORE reservations:timeline:LOT001:2024-01-15 1705334400 1705341600 WITHSCORES
4. Rate Limit Tracking (Sliding Window)
redis
# Format: ratelimit:sliding:{user_id}:{endpoint}
# Type: Sorted Set (score = timestamp)

# Add request timestamp
ZADD ratelimit:sliding:user123:api 1705333800 "req:1705333800"
ZADD ratelimit:sliding:user123:api 1705333810 "req:1705333810"

# Count requests in last minute
ZCOUNT ratelimit:sliding:user123:api 1705333740 1705333800

# Clean up old entries
ZREMRANGEBYSCORE ratelimit:sliding:user123:api -inf 1705333740
EXPIRE ratelimit:sliding:user123:api 3600
5. Parking Space Occupancy Timeline
redis
# Format: occupancy:timeline:{space_id}
# Type: Sorted Set (score = timestamp)

# Record occupancy changes
ZADD occupancy:timeline:SPACE-A12 1705333800 "occupied:VEH789"
ZADD occupancy:timeline:SPACE-A12 1705337400 "vacant"

# Get occupancy history
ZRANGEBYSCORE occupancy:timeline:SPACE-A12 1705333800 1705337400 WITHSCORES
6. Revenue Rankings
redis
# Format: revenue:ranking:{period}:{organization_id}
# Type: Sorted Set (score = revenue amount)

# Daily revenue by lot
ZINCRBY revenue:daily:2024-01-15:ORG001 1250.50 "lot:LOT001"
ZINCRBY revenue:daily:2024-01-15:ORG001 875.25 "lot:LOT002"

# Monthly revenue by lot
ZINCRBY revenue:monthly:2024-01:ORG001 45230.75 "lot:LOT001"
ZINCRBY revenue:monthly:2024-01:ORG001 38940.50 "lot:LOT002"
7. Vehicle Frequency Rankings
redis
# Format: vehicles:frequent:{lot_id}:{period}
# Type: Sorted Set (score = visit count)

ZINCRBY vehicles:frequent:LOT001:daily 1 "ABC123"
ZINCRBY vehicles:frequent:LOT001:daily 1 "XYZ789"
ZINCRBY vehicles:frequent:LOT001:weekly 1 "ABC123"

# Get most frequent vehicles
ZREVRANGE vehicles:frequent:LOT001:monthly 0 9 WITHSCORES
Geo Data Structures
1. Parking Lot Locations
redis
# Format: geo:parking_lots
# Type: Geo set

GEOADD geo:parking_lots -122.4194 37.7749 "lot:LOT001"  # San Francisco
GEOADD geo:parking_lots -122.4313 37.7853 "lot:LOT002"  # San Francisco
GEOADD geo:parking_lots -122.4089 37.7833 "lot:LOT003"  # San Francisco

# Find nearby lots within 2km
GEORADIUS geo:parking_lots -122.4194 37.7749 2 km WITHDIST WITHCOORD

# Get distance between lots
GEODIST geo:parking_lots "lot:LOT001" "lot:LOT002" km
2. Real-time Vehicle Locations (for valet)
redis
# Format: geo:vehicles:{lot_id}
# Type: Geo set
# TTL: 5 minutes

GEOADD geo:vehicles:LOT001 -122.4195 37.7750 "vehicle:ABC123"
GEOADD geo:vehicles:LOT001 -122.4200 37.7745 "vehicle:XYZ789"
EXPIRE geo:vehicles:LOT001 300

# Find vehicles near entrance
GEORADIUS geo:vehicles:LOT001 -122.4194 37.7749 50 m
3. Valet/Attendant Locations
redis
# Format: geo:attendants:{lot_id}
# Type: Geo set
# TTL: 1 minute (updated by heartbeat)

GEOADD geo:attendants:LOT001 -122.4195 37.7750 "attendant:john_doe"
GEOADD geo:attendants:LOT001 -122.4200 37.7745 "attendant:jane_smith"
EXPIRE geo:attendants:LOT001 60

# Find nearest attendant
GEORADIUS geo:attendants:LOT001 -122.4194 37.7749 100 m WITHCOORD WITHDIST
HyperLogLog Data Structures
1. Unique Vehicle Counts
redis
# Format: hll:unique_vehicles:{period}:{organization_id}
# Type: HyperLogLog
# Use for: Approximate unique vehicle counts (saves memory)

PFADD hll:unique_vehicles:daily:2024-01-15:ORG001 "ABC123" "XYZ789" "DEF456"
PFADD hll:unique_vehicles:daily:2024-01-15:ORG001 "ABC123" "GHI789"

# Get approximate unique count
PFCOUNT hll:unique_vehicles:daily:2024-01-15:ORG001

# Merge for weekly count
PFMERGE hll:unique_vehicles:weekly:2024-W03:ORG001 \
    hll:unique_vehicles:daily:2024-01-15:ORG001 \
    hll:unique_vehicles:daily:2024-01-16:ORG001 \
    hll:unique_vehicles:daily:2024-01-17:ORG001
2. Unique User Sessions
redis
# Format: hll:unique_users:{period}:{organization_id}
# Type: HyperLogLog

PFADD hll:unique_users:hourly:14:ORG001 "user:550e8400" "user:660e8400"
PFADD hll:unique_users:hourly:15:ORG001 "user:550e8400" "user:770e8400"

# Daily unique users
PFCOUNT hll:unique_users:daily:2024-01-15:ORG001
3. API Request Fingerprints
redis
# Format: hll:api_requests:{endpoint}:{date}
# Type: HyperLogLog
# Use for: Approximate unique request patterns

PFADD hll:api_requests:/api/parking/sessions:2024-01-15 \
    "req:abc123" "req:def456" "req:ghi789"
Bitmap Data Structures
1. Daily User Activity
redis
# Format: bitmap:active:{date}:{organization_id}
# Type: Bitmap (offset = user_id hash % 1M)

# Mark user active on a day (offset based on user ID hash)
SETBIT bitmap:active:2024-01-15:ORG001 123456 1
SETBIT bitmap:active:2024-01-15:ORG001 789012 1

# Check if user was active
GETBIT bitmap:active:2024-01-15:ORG001 123456

# Count active users
BITCOUNT bitmap:active:2024-01-15:ORG001

# Find users active on multiple days
BITOP AND bitmap:active:weekend:ORG001 \
    bitmap:active:2024-01-15:ORG001 \
    bitmap:active:2024-01-16:ORG001
2. Parking Space Availability Grid
redis
# Format: bitmap:spaces:{lot_id}:{level}
# Type: Bitmap (1 = available, 0 = occupied)

# Set space 5 as available
SETBIT bitmap:spaces:LOT001:1 5 1
# Set space 6 as occupied
SETBIT bitmap:spaces:LOT001:1 6 0

# Check space 5 availability
GETBIT bitmap:spaces:LOT001:1 5

# Count available spaces on level 1
BITCOUNT bitmap:spaces:LOT001:1

# Find first available space
BITPOS bitmap:spaces:LOT001:1 1
3. Feature Flags per Organization
redis
# Format: bitmap:features:{organization_id}
# Type: Bitmap (bit position = feature ID)

# Feature ID mapping:
# 1 = lpr
# 2 = pre_payment
# 3 = reservations
# 4 = dynamic_pricing

# Enable features for organization
SETBIT bitmap:features:ORG001 1 1
SETBIT bitmap:features:ORG001 2 1
SETBIT bitmap:features:ORG001 3 1

# Check if feature enabled
GETBIT bitmap:features:ORG001 1
4. Peak Hour Tracking
redis
# Format: bitmap:peak_hours:{lot_id}:{date}
# Type: Bitmap (24 bits, one per hour)

# Mark hour 14 (2 PM) as peak
SETBIT bitmap:peak_hours:LOT001:2024-01-15 14 1

# Get peak hours bitmap
GET bitmap:peak_hours:LOT001:2024-01-15
Stream Data Structures
1. Real-time Event Stream
redis
# Format: stream:events:{lot_id}
# Type: Stream
# Use: Real-time event processing, CDC

XADD stream:events:LOT001 MAXLEN ~ 10000 * \
    event_type "vehicle_entry" \
    vehicle_id "VEH789" \
    license_plate "ABC123" \
    space_id "SPACE-A12" \
    timestamp "1705333800" \
    image_url "https://storage.example.com/entry/ABC123.jpg"

XADD stream:events:LOT001 MAXLEN ~ 10000 * \
    event_type "payment_completed" \
    session_id "SESS123456" \
    amount "5.00" \
    method "credit_card" \
    timestamp "1705337400"

# Consumer group for processing
XGROUP CREATE stream:events:LOT001 processors $ MKSTREAM

# Read from stream
XREADGROUP GROUP processors consumer1 COUNT 10 BLOCK 5000 \
    STREAMS stream:events:LOT001 >
2. Sensor Data Stream
redis
# Format: stream:sensors:{lot_id}
# Type: Stream
# TTL: Auto-expire old messages (MAXLEN)

XADD stream:sensors:LOT001 MAXLEN ~ 50000 * \
    sensor_id "SENSOR-A12" \
    space_id "SPACE-A12" \
    occupied "1" \
    timestamp "1705333800" \
    confidence "0.99"

XADD stream:sensors:LOT001 MAXLEN ~ 50000 * \
    sensor_id "SENSOR-B05" \
    space_id "SPACE-B05" \
    occupied "0" \
    timestamp "1705333801"
3. Notification Stream
redis
# Format: stream:notifications:{user_id}
# Type: Stream
# TTL: 7 days

XADD stream:notifications:550e8400 MAXLEN ~ 1000 * \
    type "session_expiring" \
    title "Parking session expiring soon" \
    message "Your session in lot DOWNTOWN will expire in 15 minutes" \
    priority "high" \
    timestamp "1705333800" \
    read "false"

# Acknowledge notification
XACK stream:notifications:550e8400 processors 1705333800-0
4. Audit Log Stream
redis
# Format: stream:audit:{date}
# Type: Stream
# Use: Centralized audit logging

XADD stream:audit:2024-01-15 MAXLEN ~ 100000 * \
    user_id "550e8400" \
    action "SESSION_START" \
    entity_type "parking_session" \
    entity_id "SESS123456" \
    old_values "{}" \
    new_values "{\"vehicle\":\"ABC123\",\"space\":\"A12\"}" \
    ip_address "192.168.1.100" \
    user_agent "Mozilla/5.0" \
    timestamp "1705333800"
Key Naming Conventions
Namespace Structure
text
{namespace}:{entity}:{identifier}:{sub-entity}:{qualifier}
Common Namespaces
Namespace	Description	Example
session	User sessions	session:abc123
user	User data	user:550e8400
vehicle	Vehicle data	vehicle:ABC123
lot	Parking lot data	lot:LOT001
space	Parking space	space:SPACE-A12
rate	Rate configurations	rate:RATE001
payment	Payment records	payment:PAY789
reservation	Reservations	reservation:RES456
gate	Gate status	gate:GATE001
camera	Camera data	camera:CAM001
sensor	Sensor data	sensor:SENSOR-A12
queue	Message queues	queue:notifications
stream	Event streams	stream:events:LOT001
ratelimit	Rate limiting	ratelimit:api:user123
counter	Counters	counter:vehicles:entered
lock	Distributed locks	lock:space:A12
config	Configuration	config:system:features
cache	Cached data	cache:rates:standard
geo	Geospatial data	geo:parking_lots
hll	HyperLogLog	hll:unique_vehicles
bitmap	Bitmap data	bitmap:active:2024-01-15
Key Format Examples
text
# User-related
user:550e8400-e29b-41d4-a716-446655440000
user:550e8400-e29b-41d4-a716-446655440000:sessions
user:550e8400-e29b-41d4-a716-446655440000:permissions

# Parking lot related
lot:LOT001:status
lot:LOT001:levels:1
lot:LOT001:spaces:available
lot:LOT001:revenue:daily:2024-01-15

# Time-based
ratelimit:api:user123:2024-01-15
counter:vehicles:entered:2024-01-15:14
leaderboard:daily:2024-01-15
reservations:timeline:LOT001:2024-01-15

# Queue/Stream
queue:notifications:high
queue:events:lpr
stream:events:LOT001
stream:sensors:LOT001
Expiration Policies
TTL by Data Type
Data Type	TTL	Rationale
Session tokens	24 hours	User session duration
Rate limit counters	End of day	Daily reset
Cache (user profiles)	1 hour	Balance freshness/performance
Real-time status	5 minutes	Frequently updated
Active sessions	Session duration + grace	Until session ends
Locks	30 seconds	Auto-release for deadlocks
Queued messages	7 days	Processing window
Stream data	7-30 days	Based on retention policy
Leaderboards	End of period	Daily/weekly/monthly reset
Geospatial data	1-5 minutes	Real-time location tracking
HyperLogLog	End of period	Aggregated statistics
Expiration Strategies
redis
# 1. Simple EXPIRE
SET cache:user:550e8400 "data" EX 3600

# 2. EXPIREAT for specific time
EXPIREAT ratelimit:api:user123:2024-01-15 1705334400

# 3. Dynamic TTL based on data
local ttl = redis.call("TTL", "active:session:123")
if ttl < 300 then
    redis.call("EXPIRE", "active:session:123", 600)
end

# 4. Volatile-ttl eviction (when memory pressure)
# Configure in redis.conf: maxmemory-policy volatile-ttl
Batch Expiration
redis
# Use SCAN with pattern to expire multiple keys
SCAN 0 MATCH session:inactive:* COUNT 100
EXPIRE session:inactive:abc123 0  # Immediate expiration
DEL session:inactive:abc123        # Immediate deletion
Memory Optimization
1. Data Structure Selection
Use Case	Recommended Structure	Memory Efficiency
Unique counts (approx)	HyperLogLog	Excellent (~12KB per key)
Boolean flags	Bitmap	Excellent (1 bit per flag)
Real-time counters	String	Good
Object cache	Hash	Good (field-level access)
Time-series data	Sorted Set	Moderate
Message queue	List/Stream	Moderate
Geospatial	Geo set	Moderate
Activity feed	List (trimmed)	Good with LTRIM
2. Compression Techniques
redis
# 1. Use shorter keys
# Instead of:
SET "parking_lot:status:downtown:available_spaces" 42
# Use:
SET "lot:DTN:avail" 42

# 2. Use integer IDs instead of UUIDs where possible
# Instead of:
SET "user:550e8400-e29b-41d4-a716-446655440000:name" "John"
# Use:
SET "user:12345:name" "John"

# 3. Store JSON as compressed string (client-side compression)
SET lot:DTN:config COMPRESSED_DATA

# 4. Use message packing (MessagePack, BSON)
# Instead of JSON strings, use binary formats
3. Memory Monitoring
redis
# Check memory usage
INFO memory

# Get memory usage of a key
MEMORY USAGE user:550e8400

# Get memory stats
MEMORY STATS

# Set max memory
CONFIG SET maxmemory 2gb
CONFIG SET maxmemory-policy allkeys-lru
4. Optimization Examples
redis
# Instead of storing full objects, store only needed fields
# Bad:
HMSET session:123 \
    user_id "550e8400" \
    user_name "John Doe" \
    user_email "john@example.com" \
    user_role "attendant" \
    permissions "[\"read\",\"write\"]" \
    login_time "2024-01-15T14:30:00Z" \
    last_activity "2024-01-15T14:45:00Z" \
    ip_address "192.168.1.100" \
    user_agent "Mozilla/5.0"

# Good (store minimal data, reference DB for details):
HMSET session:123 \
    uid "550e8400" \
    role "attendant" \
    exp "1705334400"
Backup and Persistence
RDB Snapshots
redis
# redis.conf
save 900 1      # Save if at least 1 key changed in 900 seconds
save 300 10     # Save if at least 10 keys changed in 300 seconds
save 60 10000   # Save if at least 10000 keys changed in 60 seconds

# Manual save
SAVE
BGSAVE
AOF Persistence
redis
# redis.conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
Backup Strategy
bash
#!/bin/bash
# backup_redis.sh

# RDB backup
cp /var/lib/redis/dump.rdb /backup/redis/dump.$(date +%Y%m%d-%H%M%S).rdb

# AOF backup
cp /var/lib/redis/appendonly.aof /backup/redis/appendonly.$(date +%Y%m%d-%H%M%S).aof

# Redis dump with password
redis-cli -a yourpassword SAVE
redis-cli -a yourpassword --rdb /backup/redis/dump.rdb

# Keep only last 7 days of backups
find /backup/redis -name "dump.*.rdb" -mtime +7 -delete
find /backup/redis -name "appendonly.*.aof" -mtime +7 -delete
Restore Procedure
redis
# Stop Redis
sudo systemctl stop redis

# Replace dump.rdb
cp /backup/redis/dump.20240115-143000.rdb /var/lib/redis/dump.rdb

# Start Redis
sudo systemctl start redis

# Verify data
redis-cli INFO keyspace
Monitoring and Metrics
Key Metrics to Monitor
redis
# 1. Hit Rate
INFO stats
# Keyspace_hits / (Keyspace_hits + Keyspace_misses)

# 2. Memory Usage
INFO memory
# used_memory, used_memory_peak, mem_fragmentation_ratio

# 3. Connected Clients
INFO clients
# connected_clients, blocked_clients

# 4. Command Statistics
INFO commandstats
# cmdstat_get:calls=123,usec=456

# 5. Replication Lag
INFO replication
# master_repl_offset, slave_repl_offset
Monitoring Script
python
# monitor_redis.py
import redis
import time
import json

r = redis.Redis(host='localhost', port=6379, db=0)

def collect_metrics():
    info = r.info()
    
    metrics = {
        'timestamp': time.time(),
        'used_memory': info['used_memory'],
        'used_memory_peak': info['used_memory_peak'],
        'mem_fragmentation_ratio': info['mem_fragmentation_ratio'],
        'connected_clients': info['connected_clients'],
        'blocked_clients': info['blocked_clients'],
        'total_commands_processed': info['total_commands_processed'],
        'keyspace_hits': info['keyspace_hits'],
        'keyspace_misses': info['keyspace_misses'],
        'hit_rate': info['keyspace_hits'] / (info['keyspace_hits'] + info['keyspace_misses']) if (info['keyspace_hits'] + info['keyspace_misses']) > 0 else 0,
        'evicted_keys': info['evicted_keys'],
        'expired_keys': info['expired_keys'],
    }
    
    # Add database stats
    for i in range(16):
        db_key = f'db{i}'
        if db_key in info:
            metrics[db_key] = info[db_key]
    
    return metrics

# Collect every minute
while True:
    metrics = collect_metrics()
    with open(f"/var/log/redis/metrics.{time.strftime('%Y%m%d')}.json", 'a') as f:
        f.write(json.dumps(metrics) + '\n')
    time.sleep(60)
Alerting Rules
yaml
# alerts.yml
groups:
  - name: redis_alerts
    rules:
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        annotations:
          summary: "Redis instance {{ $labels.instance }} is down"

      - alert: RedisHighMemory
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        annotations:
          summary: "Redis memory usage is above 90%"

      - alert: RedisHighClients
        expr: redis_connected_clients > 1000
        for: 5m
        annotations:
          summary: "Redis has too many connected clients"

      - alert: RedisLowHitRate
        expr: rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) < 0.5
        for: 10m
        annotations:
          summary: "Redis cache hit rate is below 50%"

      - alert: RedisReplicationLag
        expr: redis_master_repl_offset - redis_slave_repl_offset > 1000
        for: 1m
        annotations:
          summary: "Redis replication lag is high"
Performance Testing
bash
# redis-benchmark examples

# Test SET/GET performance
redis-benchmark -h localhost -p 6379 -n 100000 -c 50 -t SET,GET

# Test pipeline performance
redis-benchmark -h localhost -p 6379 -n 100000 -P 16

# Test with JSON data
redis-benchmark -h localhost -p 6379 -n 10000 -d 1024 -t SET

# Test Lua script performance
redis-benchmark -h localhost -p 6379 -n 10000 script load "return redis.call('GET', KEYS[1])"
Best Practices Summary
Key Naming: Use consistent, hierarchical namespaces

TTL Strategy: Always set expiration for temporary data

Memory Optimization: Choose the right data structure for each use case

Persistence: Configure RDB/AOF based on data criticality

Monitoring: Track hit rates, memory usage, and command statistics

Backup: Regular backups with point-in-time recovery capability

Security: Use password authentication and TLS for production

Connection Pooling: Implement in application layer

Pipeline/Batch: Use pipelining for multiple commands

Lua Scripting: Use Lua for atomic operations when needed