# Parking Management System Database Documentation

## Overview
The Parking Management System uses PostgreSQL as its primary database. This document provides comprehensive information about the database schema, relationships, and data models.

## Database Configuration

### Connection Details
- **Database Type**: PostgreSQL 15+
- **Database Name**: parking_db
- **Default Port**: 5432
- **Connection String**: `postgresql://user:password@localhost:5432/parking_db`

### Environment Variables
```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=parking_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
DB_ECHO=false  # Set to true for SQL logging
Schema Overview
Entity Relationship Diagram (ERD)
text
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    users    │───────│  vehicles   │       │parking_spots│
└─────────────┘       └─────────────┘       └─────────────┘
       │                      │                      │
       │                      │                      │
       ▼                      ▼                      ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│reservations │───────│  payments   │       │maintenance  │
└─────────────┘       └─────────────┘       │   records   │
       │                                      └─────────────┘
       │
       ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  reviews    │       │notifications│       │waitlist     │
└─────────────┘       └─────────────┘       │   entries   │
                                            └─────────────┘
       ┌──────────────────────────────────────────┐
       ▼                  ▼                       ▼
┌─────────────┐    ┌─────────────┐         ┌─────────────┐
│ price_rules │    │  discounts  │         │loyalty      │
└─────────────┘    └─────────────┘         │ programs    │
                                           └─────────────┘
Table Schemas
users
Stores user account information.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique user identifier
email	VARCHAR(255)	UNIQUE NOT NULL	User's email address
password_hash	VARCHAR(255)	NOT NULL	Bcrypt hashed password
full_name	VARCHAR(100)	NOT NULL	User's full name
phone	VARCHAR(20)		Phone number
role	user_role	NOT NULL DEFAULT 'user'	User role (user, admin, manager)
is_active	BOOLEAN	NOT NULL DEFAULT true	Account status
email_verified	BOOLEAN	NOT NULL DEFAULT false	Email verification status
phone_verified	BOOLEAN	NOT NULL DEFAULT false	Phone verification status
last_login	TIMESTAMPTZ		Last login timestamp
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record creation timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record update timestamp
deleted_at	TIMESTAMPTZ		Soft delete timestamp
Indexes:

idx_users_email ON users(email)

idx_users_role ON users(role)

idx_users_created_at ON users(created_at)

vehicles
Stores user vehicle information.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique vehicle identifier
user_id	UUID	FOREIGN KEY REFERENCES users(id)	Owner's user ID
license_plate	VARCHAR(20)	NOT NULL	Vehicle license plate
vehicle_type	vehicle_type	NOT NULL	Type (car, motorcycle, truck, ev)
make	VARCHAR(50)		Vehicle make
model	VARCHAR(50)		Vehicle model
color	VARCHAR(30)		Vehicle color
is_default	BOOLEAN	DEFAULT false	Default vehicle for user
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record creation timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record update timestamp
Indexes:

idx_vehicles_user_id ON vehicles(user_id)

idx_vehicles_license_plate ON vehicles(license_plate)

idx_vehicles_user_default ON vehicles(user_id, is_default) WHERE is_default = true

Foreign Keys:

fk_vehicles_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

parking_spots
Stores parking spot information.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique spot identifier
spot_number	VARCHAR(20)	UNIQUE NOT NULL	Spot identifier (e.g., "A101")
spot_type	spot_type	NOT NULL	Type (standard, handicapped, ev, motorcycle)
floor	INTEGER	NOT NULL	Floor number
section	VARCHAR(10)	NOT NULL	Section identifier
status	spot_status	NOT NULL DEFAULT 'available'	Current status
price_per_hour	DECIMAL(10,2)	NOT NULL	Base price per hour
features	TEXT[]		Array of features (covered, ev_charging, etc.)
dimensions	JSONB		Length, width, height in meters
coordinates	JSONB		X, Y coordinates on map
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record creation timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record update timestamp
Indexes:

idx_parking_spots_spot_number ON parking_spots(spot_number)

idx_parking_spots_status ON parking_spots(status)

idx_parking_spots_type_status ON parking_spots(spot_type, status)

idx_parking_spots_floor_section ON parking_spots(floor, section)

reservations
Stores parking reservations.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique reservation identifier
user_id	UUID	FOREIGN KEY REFERENCES users(id) NOT NULL	User who made reservation
spot_id	UUID	FOREIGN KEY REFERENCES parking_spots(id) NOT NULL	Reserved parking spot
vehicle_id	UUID	FOREIGN KEY REFERENCES vehicles(id) NOT NULL	Vehicle for reservation
start_time	TIMESTAMPTZ	NOT NULL	Reservation start time
end_time	TIMESTAMPTZ	NOT NULL	Reservation end time
status	reservation_status	NOT NULL DEFAULT 'pending'	Reservation status
total_price	DECIMAL(10,2)	NOT NULL	Total price for reservation
check_in_time	TIMESTAMPTZ		Actual check-in time
check_out_time	TIMESTAMPTZ		Actual check-out time
notes	TEXT		Additional notes
qr_code	TEXT		QR code data for check-in
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record creation timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record update timestamp
cancelled_at	TIMESTAMPTZ		Cancellation timestamp
cancellation_reason	TEXT		Reason for cancellation
Indexes:

idx_reservations_user_id ON reservations(user_id)

idx_reservations_spot_id ON reservations(spot_id)

idx_reservations_time_range ON reservations(start_time, end_time)

idx_reservations_status ON reservations(status)

idx_reservations_user_status ON reservations(user_id, status)

Foreign Keys:

fk_reservations_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

fk_reservations_spot_id FOREIGN KEY (spot_id) REFERENCES parking_spots(id) ON DELETE CASCADE

fk_reservations_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE

Constraints:

chk_reservations_time_range CHECK (end_time > start_time)

chk_reservations_future CHECK (start_time > NOW() OR status IN ('active', 'completed'))

payments
Stores payment transactions.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique payment identifier
reservation_id	UUID	FOREIGN KEY REFERENCES reservations(id)	Associated reservation
user_id	UUID	FOREIGN KEY REFERENCES users(id) NOT NULL	User who made payment
amount	DECIMAL(10,2)	NOT NULL	Payment amount
currency	VARCHAR(3)	NOT NULL DEFAULT 'USD'	Currency code
status	payment_status	NOT NULL DEFAULT 'pending'	Payment status
payment_method	payment_method	NOT NULL	Payment method used
payment_method_id	UUID		Reference to saved payment method
transaction_id	VARCHAR(100)		External transaction ID
receipt_url	TEXT		URL to payment receipt
metadata	JSONB		Additional payment data
refunded_amount	DECIMAL(10,2)	DEFAULT 0	Amount refunded
refund_reason	TEXT		Reason for refund
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Payment timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record update timestamp
Indexes:

idx_payments_reservation_id ON payments(reservation_id)

idx_payments_user_id ON payments(user_id)

idx_payments_status ON payments(status)

idx_payments_transaction_id ON payments(transaction_id)

idx_payments_created_at ON payments(created_at)

notifications
Stores user notifications.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique notification identifier
user_id	UUID	FOREIGN KEY REFERENCES users(id) NOT NULL	Recipient user ID
type	notification_type	NOT NULL	Notification type
title	VARCHAR(200)	NOT NULL	Notification title
content	TEXT	NOT NULL	Notification content
data	JSONB		Additional data
is_read	BOOLEAN	DEFAULT false	Read status
read_at	TIMESTAMPTZ		When notification was read
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Creation timestamp
Indexes:

idx_notifications_user_id ON notifications(user_id)

idx_notifications_user_unread ON notifications(user_id) WHERE is_read = false

idx_notifications_created_at ON notifications(created_at)

reviews
Stores user reviews for parking spots.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique review identifier
user_id	UUID	FOREIGN KEY REFERENCES users(id) NOT NULL	Review author
spot_id	UUID	FOREIGN KEY REFERENCES parking_spots(id) NOT NULL	Reviewed spot
reservation_id	UUID	FOREIGN KEY REFERENCES reservations(id) UNIQUE	Associated reservation
rating	INTEGER	NOT NULL CHECK (rating >= 1 AND rating <= 5)	Rating (1-5)
comment	TEXT		Review comment
is_verified	BOOLEAN	DEFAULT false	Verified stay
helpful_count	INTEGER	DEFAULT 0	Number of helpful votes
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Creation timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Update timestamp
Indexes:

idx_reviews_spot_id ON reviews(spot_id)

idx_reviews_user_id ON reviews(user_id)

idx_reviews_rating ON reviews(rating)

idx_reviews_spot_rating ON reviews(spot_id, rating)

waitlist_entries
Stores users waiting for specific spot types.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique entry identifier
user_id	UUID	FOREIGN KEY REFERENCES users(id) NOT NULL	Waiting user
spot_type	spot_type	NOT NULL	Desired spot type
preferred_time	TIMESTAMPTZ		Preferred time
status	waitlist_status	NOT NULL DEFAULT 'waiting'	Waitlist status
position	INTEGER		Current position in queue
notified_at	TIMESTAMPTZ		When user was notified
expires_at	TIMESTAMPTZ		When entry expires
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Creation timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Update timestamp
Indexes:

idx_waitlist_user_id ON waitlist_entries(user_id)

idx_waitlist_status ON waitlist_entries(status)

idx_waitlist_type_position ON waitlist_entries(spot_type, position)

maintenance_records
Stores parking spot maintenance history.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique record identifier
spot_id	UUID	FOREIGN KEY REFERENCES parking_spots(id) NOT NULL	Maintained spot
reported_by	UUID	FOREIGN KEY REFERENCES users(id)	Who reported issue
issue_type	maintenance_type	NOT NULL	Type of maintenance
description	TEXT	NOT NULL	Issue description
severity	severity_level	NOT NULL	Issue severity
status	maintenance_status	NOT NULL DEFAULT 'reported'	Current status
scheduled_date	TIMESTAMPTZ		Scheduled maintenance date
completed_date	TIMESTAMPTZ		Completion date
cost	DECIMAL(10,2)		Maintenance cost
notes	TEXT		Additional notes
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Creation timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Update timestamp
Indexes:

idx_maintenance_spot_id ON maintenance_records(spot_id)

idx_maintenance_status ON maintenance_records(status)

idx_maintenance_scheduled_date ON maintenance_records(scheduled_date)

price_rules
Stores dynamic pricing rules.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique rule identifier
name	VARCHAR(100)	NOT NULL	Rule name
rule_type	rule_type	NOT NULL	Type of rule
conditions	JSONB	NOT NULL	Rule conditions
adjustment	JSONB	NOT NULL	Price adjustment
applicable_to	spot_type[]		Applicable spot types
priority	INTEGER	NOT NULL DEFAULT 0	Rule priority
is_active	BOOLEAN	DEFAULT true	Active status
start_date	TIMESTAMPTZ		Rule start date
end_date	TIMESTAMPTZ		Rule end date
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Creation timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Update timestamp
Indexes:

idx_price_rules_active ON price_rules(is_active)

idx_price_rules_date_range ON price_rules(start_date, end_date)

discounts
Stores discount codes and offers.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique discount identifier
code	VARCHAR(50)	UNIQUE NOT NULL	Discount code
description	TEXT		Discount description
discount_type	discount_type	NOT NULL	Type of discount
value	DECIMAL(10,2)	NOT NULL	Discount value
min_purchase	DECIMAL(10,2)		Minimum purchase amount
max_discount	DECIMAL(10,2)		Maximum discount amount
usage_limit	INTEGER		Maximum number of uses
used_count	INTEGER	DEFAULT 0	Current usage count
per_user_limit	INTEGER	DEFAULT 1	Usage limit per user
applicable_spot_types	spot_type[]		Applicable spot types
start_date	TIMESTAMPTZ	NOT NULL	Offer start date
end_date	TIMESTAMPTZ	NOT NULL	Offer end date
is_active	BOOLEAN	DEFAULT true	Active status
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Creation timestamp
Indexes:

idx_discounts_code ON discounts(code)

idx_discounts_active_date ON discounts(is_active, start_date, end_date)

loyalty_programs
Stores user loyalty program data.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique record identifier
user_id	UUID	FOREIGN KEY REFERENCES users(id) UNIQUE NOT NULL	User ID
points	INTEGER	DEFAULT 0	Current loyalty points
tier	loyalty_tier	DEFAULT 'bronze'	Membership tier
total_spent	DECIMAL(10,2)	DEFAULT 0	Total amount spent
total_reservations	INTEGER	DEFAULT 0	Total reservations made
joined_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Program join date
last_activity	TIMESTAMPTZ		Last activity timestamp
updated_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Record update timestamp
Indexes:

idx_loyalty_user_id ON loyalty_programs(user_id)

idx_loyalty_tier_points ON loyalty_programs(tier, points)

audit_logs
Stores audit trail for administrative actions.

Column	Type	Constraints	Description
id	UUID	PRIMARY KEY DEFAULT gen_random_uuid()	Unique log identifier
user_id	UUID	FOREIGN KEY REFERENCES users(id)	User who performed action
action	VARCHAR(50)	NOT NULL	Action performed
resource	VARCHAR(50)	NOT NULL	Resource type
resource_id	UUID		Resource identifier
details	JSONB		Action details
changes	JSONB		Before/after changes
ip_address	INET		Client IP address
user_agent	TEXT		Client user agent
created_at	TIMESTAMPTZ	NOT NULL DEFAULT NOW()	Action timestamp
Indexes:

idx_audit_logs_user_id ON audit_logs(user_id)

idx_audit_logs_resource ON audit_logs(resource, resource_id)

idx_audit_logs_action ON audit_logs(action)

idx_audit_logs_created_at ON audit_logs(created_at)

Enums
sql
-- User role enum
CREATE TYPE user_role AS ENUM ('user', 'admin', 'manager');

-- Vehicle type enum
CREATE TYPE vehicle_type AS ENUM ('car', 'motorcycle', 'truck', 'ev');

-- Spot type enum
CREATE TYPE spot_type AS ENUM ('standard', 'handicapped', 'ev', 'motorcycle');

-- Spot status enum
CREATE TYPE spot_status AS ENUM ('available', 'occupied', 'reserved', 'maintenance');

-- Reservation status enum
CREATE TYPE reservation_status AS ENUM ('pending', 'confirmed', 'active', 'completed', 'cancelled');

-- Payment status enum
CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');

-- Payment method enum
CREATE TYPE payment_method AS ENUM ('credit_card', 'debit_card', 'paypal', 'apple_pay', 'google_pay');

-- Notification type enum
CREATE TYPE notification_type AS ENUM ('reservation_confirmation', 'reminder', 'payment_receipt', 'promotion', 'alert');

-- Waitlist status enum
CREATE TYPE waitlist_status AS ENUM ('waiting', 'notified',