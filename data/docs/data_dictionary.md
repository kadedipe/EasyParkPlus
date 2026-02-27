markdown
# Parking Management System - Data Dictionary

## Document Information
| | |
|---|---|
| **Document Version** | 1.0.0 |
| **Last Updated** | 2024-01-15 |
| **Application Version** | 1.0.0 |
| **Database** | PostgreSQL 14+ |
| **Author** | Parking Management System Team |

## Document Purpose
This data dictionary provides comprehensive documentation of all data entities, attributes, relationships, and constraints used in the Parking Management System. It serves as a reference for developers, database administrators, and system integrators.

---

## Table of Contents
1. [Entity Relationship Diagram](#entity-relationship-diagram)
2. [Core Tables](#core-tables)
   - [Users](#users)
   - [Parking Spots](#parking-spots)
   - [Vehicles](#vehicles)
   - [Reservations](#reservations)
3. [Supporting Tables](#supporting-tables)
   - [Recurring Reservations](#recurring-reservations)
   - [Waitlist](#waitlist)
   - [Reservation History](#reservation-history)
   - [Reservation Notes](#reservation-notes)
   - [Reservation Addons](#reservation-addons)
   - [Payments](#payments)
4. [Lookup Tables](#lookup-tables)
5. [Audit Tables](#audit-tables)
6. [Data Types Reference](#data-types-reference)
7. [Enum Values Reference](#enum-values-reference)
8. [Business Rules](#business-rules)
9. [Indexes](#indexes)
10. [Constraints](#constraints)

---

## Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ VEHICLES : owns
    USERS ||--o{ RESERVATIONS : makes
    USERS ||--o{ WAITLIST : joins
    USERS ||--o{ RECURRING_RESERVATIONS : sets_up
    
    PARKING_SPOTS ||--o{ RESERVATIONS : booked_for
    PARKING_SPOTS ||--o{ WAITLIST : requested_for
    PARKING_SPOTS ||--o{ RECURRING_RESERVATIONS : scheduled_for
    
    VEHICLES ||--o{ RESERVATIONS : used_in
    VEHICLES ||--o{ RECURRING_RESERVATIONS : used_in
    
    RESERVATIONS ||--o{ RESERVATION_HISTORY : has
    RESERVATIONS ||--o{ RESERVATION_NOTES : has
    RESERVATIONS ||--o{ RESERVATION_ADDONS : includes
    RESERVATIONS ||--o{ PAYMENTS : has
    
    RECURRING_RESERVATIONS ||--o{ RESERVATIONS : generates
Core Tables
Users
Stores information about system users including customers, staff, and administrators.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique user identifier	5
email	VARCHAR(255)	NOT NULL, UNIQUE	User's email address	john.doe@example.com
full_name	VARCHAR(255)	NOT NULL	User's full name	John Doe
phone	VARCHAR(20)	NULLABLE	Contact phone number	+1234567890
password_hash	VARCHAR(255)	NOT NULL	Bcrypt hashed password	$2b$12$...
role	VARCHAR(50)	NOT NULL, DEFAULT: 'customer'	User role	customer
status	VARCHAR(20)	NOT NULL, DEFAULT: 'active'	Account status	active
verification_status	VARCHAR(20)	NOT NULL, DEFAULT: 'unverified'	Email/phone verification	fully_verified
preferences	JSONB	NULLABLE	User preferences as JSON	{"notifications": true}
metadata	JSONB	NULLABLE	Additional metadata	{"source": "web"}
last_login_at	TIMESTAMPTZ	NULLABLE	Last login timestamp	2024-01-15 10:30:00 UTC
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Record creation timestamp	2023-01-01 10:00:00 UTC
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Record update timestamp	2023-01-01 10:00:00 UTC
Indexes:

idx_users_email on email

idx_users_role on role

idx_users_status on status

idx_users_created_at on created_at

Parking Spots
Stores information about parking spots including location, type, and availability.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique spot identifier	4
spot_number	VARCHAR(10)	NOT NULL, UNIQUE	Physical spot number	A4
spot_type	VARCHAR(50)	NOT NULL, DEFAULT: 'standard'	Type of parking spot	standard
hourly_rate	DECIMAL(10,2)	NOT NULL	Hourly rate in base currency	3.00
charging_fee	DECIMAL(10,2)	NULLABLE	Additional fee for EV charging	1.00
charger_type	VARCHAR(20)	NULLABLE	Type of EV charger	level_2
charger_power	VARCHAR(10)	NULLABLE	Charger power rating	7.2 kW
is_active	BOOLEAN	NOT NULL, DEFAULT: true	Whether spot is active	true
is_covered	BOOLEAN	NOT NULL, DEFAULT: false	Whether spot is covered	true
is_handicap	BOOLEAN	NOT NULL, DEFAULT: false	Handicap accessible	false
is_near_elevator	BOOLEAN	NOT NULL, DEFAULT: false	Near elevator access	true
level	INTEGER	NULLABLE	Parking level/floor	1
section	VARCHAR(10)	NULLABLE	Section identifier	A
row	VARCHAR(10)	NULLABLE	Row identifier	1
coordinates	JSONB	NULLABLE	Geolocation coordinates	{"lat": 37.7749, "lng": -122.4194}
features	JSONB	NULLABLE	Array of spot features	["near_elevator", "covered"]
last_maintenance	DATE	NULLABLE	Last maintenance date	2023-12-01
next_maintenance	DATE	NULLABLE	Next scheduled maintenance	2024-03-01
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Record creation timestamp	2023-01-01 10:00:00 UTC
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Record update timestamp	2023-01-01 10:00:00 UTC
Indexes:

idx_spots_spot_number on spot_number

idx_spots_spot_type on spot_type

idx_spots_is_active on is_active

idx_spots_location on level, section

Vehicles
Stores information about user vehicles.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique vehicle identifier	101
user_id	BIGINT	NOT NULL, FOREIGN KEY (users.id)	Owner user ID	5
license_plate	VARCHAR(20)	NOT NULL, UNIQUE	Vehicle license plate	ABC-1234
vehicle_type	VARCHAR(50)	NOT NULL	Type of vehicle	sedan
make	VARCHAR(50)	NULLABLE	Vehicle manufacturer	Toyota
model	VARCHAR(50)	NULLABLE	Vehicle model	Camry
color	VARCHAR(30)	NULLABLE	Vehicle color	Silver
year	INTEGER	NULLABLE	Vehicle year	2020
is_ev	BOOLEAN	NOT NULL, DEFAULT: false	Whether vehicle is electric	false
battery_capacity	INTEGER	NULLABLE	EV battery capacity in kWh	75
metadata	JSONB	NULLABLE	Additional metadata	{"has_sunroof": true}
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Record creation timestamp	2023-01-01 10:00:00 UTC
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Record update timestamp	2023-01-01 10:00:00 UTC
Indexes:

idx_vehicles_user_id on user_id

idx_vehicles_license_plate on license_plate

idx_vehicles_type on vehicle_type

idx_vehicles_is_ev on is_ev

Reservations
Core table storing all parking reservations.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique reservation identifier	201
user_id	BIGINT	NOT NULL, FOREIGN KEY (users.id)	User who made reservation	5
spot_id	BIGINT	NOT NULL, FOREIGN KEY (parking_spots.id)	Reserved parking spot	4
vehicle_id	BIGINT	NOT NULL, FOREIGN KEY (vehicles.id)	Vehicle used	101
confirmation_code	VARCHAR(20)	NOT NULL, UNIQUE	Unique confirmation code	CONF-001-ABCD
reservation_type	VARCHAR(20)	NOT NULL, DEFAULT: 'standard'	Type of reservation	standard
status	VARCHAR(20)	NOT NULL, DEFAULT: 'pending'	Current reservation status	completed
start_time	TIMESTAMPTZ	NOT NULL	Reservation start time	2023-12-10 09:00:00 UTC
end_time	TIMESTAMPTZ	NOT NULL	Reservation end time	2023-12-10 17:00:00 UTC
total_amount	DECIMAL(10,2)	NOT NULL	Total reservation amount	20.00
charging_fee	DECIMAL(10,2)	NULLABLE	EV charging fee	4.00
energy_used_kwh	DECIMAL(10,2)	NULLABLE	Energy used for charging	32.00
payment_status	VARCHAR(20)	NOT NULL, DEFAULT: 'pending'	Payment status	paid
payment_id	BIGINT	NULLABLE, FOREIGN KEY (payments.id)	Associated payment	301
special_requests	TEXT	NULLABLE	Customer special requests	Near elevator please
cancellation_reason	TEXT	NULLABLE	Reason for cancellation	Change of plans
metadata	JSONB	NULLABLE	Additional metadata	{"source": "mobile_app"}
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Record creation timestamp	2023-12-01 14:30:00 UTC
confirmed_at	TIMESTAMPTZ	NULLABLE	When reservation was confirmed	2023-12-01 14:35:00 UTC
checked_in_at	TIMESTAMPTZ	NULLABLE	When user checked in	2023-12-10 08:45:00 UTC
checked_out_at	TIMESTAMPTZ	NULLABLE	When user checked out	2023-12-10 17:15:00 UTC
completed_at	TIMESTAMPTZ	NULLABLE	When reservation completed	2023-12-10 17:15:00 UTC
cancelled_at	TIMESTAMPTZ	NULLABLE	When reservation cancelled	2023-12-22 09:30:00 UTC
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Record update timestamp	2023-12-10 17:15:00 UTC
Indexes:

idx_reservations_user_id on user_id

idx_reservations_spot_id on spot_id

idx_reservations_confirmation_code on confirmation_code

idx_reservations_status on status

idx_reservations_start_time on start_time

idx_reservations_date_range on start_time, end_time

idx_reservations_payment_status on payment_status

Supporting Tables
Recurring Reservations
Stores patterns for recurring reservations.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique identifier	1
user_id	BIGINT	NOT NULL, FOREIGN KEY (users.id)	User ID	5
spot_id	BIGINT	NOT NULL, FOREIGN KEY (parking_spots.id)	Parking spot ID	4
vehicle_id	BIGINT	NOT NULL, FOREIGN KEY (vehicles.id)	Vehicle ID	101
pattern_id	VARCHAR(20)	NOT NULL, UNIQUE	Unique pattern identifier	REC-001
frequency	VARCHAR(20)	NOT NULL	Frequency type	weekly
start_date	DATE	NOT NULL	Pattern start date	2024-01-08
end_date	DATE	NOT NULL	Pattern end date	2024-03-25
start_time	TIME	NOT NULL	Daily start time	09:00:00
end_time	TIME	NOT NULL	Daily end time	17:00:00
days_of_week	INTEGER[]	NULLABLE	Days of week (1-7)	[1,3,5]
day_of_month	INTEGER	NULLABLE	Day of month (1-31)	5
monthly_option	VARCHAR(20)	NULLABLE	Monthly pattern option	day_of_month
total_amount_per_occurrence	DECIMAL(10,2)	NOT NULL	Amount per occurrence	24.00
is_active	BOOLEAN	NOT NULL, DEFAULT: true	Whether pattern is active	true
paused_periods	JSONB	NULLABLE	Paused date ranges	[{"start": "2024-02-01", "end": "2024-02-15"}]
metadata	JSONB	NULLABLE	Additional metadata	{}
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Creation timestamp	2024-01-01 10:00:00 UTC
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Update timestamp	2024-01-01 10:00:00 UTC
Indexes:

idx_recurring_user_id on user_id

idx_recurring_spot_id on spot_id

idx_recurring_active on is_active

idx_recurring_dates on start_date, end_date

Waitlist
Stores users waiting for specific spots.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique identifier	1
user_id	BIGINT	NOT NULL, FOREIGN KEY (users.id)	User ID	17
spot_id	BIGINT	NOT NULL, FOREIGN KEY (parking_spots.id)	Parking spot ID	18
date_from	TIMESTAMPTZ	NOT NULL	Desired start time	2024-01-20 18:00:00 UTC
date_to	TIMESTAMPTZ	NOT NULL	Desired end time	2024-01-20 22:00:00 UTC
status	VARCHAR(20)	NOT NULL, DEFAULT: 'active'	Waitlist status	active
position	INTEGER	NOT NULL	Position in queue	1
notified_at	TIMESTAMPTZ	NULLABLE	When user was notified	2024-01-18 10:30:00 UTC
expires_at	TIMESTAMPTZ	NULLABLE	When entry expires	2024-01-22 10:30:00 UTC
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Creation timestamp	2024-01-10 09:30:00 UTC
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Update timestamp	2024-01-10 09:30:00 UTC
Indexes:

idx_waitlist_user_id on user_id

idx_waitlist_spot_id on spot_id

idx_waitlist_status on status

idx_waitlist_spot_date on spot_id, date_from

idx_waitlist_position on spot_id, date_from, position

Reservation History
Tracks status changes for reservations.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique identifier	1
reservation_id	BIGINT	NOT NULL, FOREIGN KEY (reservations.id)	Reservation ID	201
status	VARCHAR(20)	NOT NULL	New status	confirmed
changed_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	When status changed	2023-12-01 14:35:00 UTC
changed_by	VARCHAR(50)	NOT NULL	Who made the change	system
reason	TEXT	NULLABLE	Reason for change	Payment confirmed
metadata	JSONB	NULLABLE	Additional context	{"payment_id": 301}
Indexes:

idx_history_reservation_id on reservation_id

idx_history_changed_at on changed_at

idx_history_status on status

Reservation Notes
Stores notes and comments on reservations.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique identifier	1
reservation_id	BIGINT	NOT NULL, FOREIGN KEY (reservations.id)	Reservation ID	201
user_id	BIGINT	NOT NULL, FOREIGN KEY (users.id)	User who wrote note	5
note	TEXT	NOT NULL	Note content	Customer requested...
is_private	BOOLEAN	NOT NULL, DEFAULT: false	Whether note is private	false
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Creation timestamp	2023-12-01 14:35:00 UTC
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Update timestamp	2023-12-01 14:35:00 UTC
Indexes:

idx_notes_reservation_id on reservation_id

idx_notes_user_id on user_id

idx_notes_created_at on created_at

Reservation Addons
Stores additional services purchased with reservations.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique identifier	1
reservation_id	BIGINT	NOT NULL, FOREIGN KEY (reservations.id)	Reservation ID	209
addon_type	VARCHAR(50)	NOT NULL	Type of addon	valet
quantity	INTEGER	NOT NULL, DEFAULT: 1	Quantity purchased	1
unit_price	DECIMAL(10,2)	NOT NULL	Price per unit	15.00
total_price	DECIMAL(10,2)	NOT NULL	Total price	15.00
metadata	JSONB	NULLABLE	Addon-specific data	{"valet_id": "VAL-123"}
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Creation timestamp	2023-12-22 10:50:00 UTC
Indexes:

idx_addons_reservation_id on reservation_id

idx_addons_type on addon_type

Payments
Stores payment transaction data.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique identifier	301
reservation_id	BIGINT	NOT NULL, FOREIGN KEY (reservations.id)	Reservation ID	201
amount	DECIMAL(10,2)	NOT NULL	Payment amount	20.00
currency	VARCHAR(3)	NOT NULL, DEFAULT: 'USD'	Currency code	USD
status	VARCHAR(20)	NOT NULL	Payment status	completed
payment_method	VARCHAR(50)	NOT NULL	Payment method	credit_card
provider	VARCHAR(50)	NOT NULL	Payment provider	stripe
transaction_id	VARCHAR(255)	NULLABLE, UNIQUE	Provider transaction ID	ch_123456789
provider_response	JSONB	NULLABLE	Raw provider response	{"id": "ch_123"}
card_last4	VARCHAR(4)	NULLABLE	Last 4 digits of card	4242
card_brand	VARCHAR(20)	NULLABLE	Card brand	visa
refunded_amount	DECIMAL(10,2)	NULLABLE	Amount refunded	0.00
refund_reason	TEXT	NULLABLE	Reason for refund	Cancellation
refunded_at	TIMESTAMPTZ	NULLABLE	When refund was processed	2023-12-22 10:00:00 UTC
metadata	JSONB	NULLABLE	Additional metadata	{"receipt_url": "https://..."}
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Creation timestamp	2023-12-01 14:35:00 UTC
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Update timestamp	2023-12-01 14:35:00 UTC
Indexes:

idx_payments_reservation_id on reservation_id

idx_payments_transaction_id on transaction_id

idx_payments_status on status

idx_payments_created_at on created_at

Audit Tables
Audit Logs
Stores system audit trail.

Column	Data Type	Constraints	Description	Example
id	BIGINT	PRIMARY KEY, AUTO_INCREMENT	Unique identifier	1001
timestamp	TIMESTAMPTZ	NOT NULL, DEFAULT: NOW()	Event timestamp	2024-01-15 10:30:00 UTC
action	VARCHAR(50)	NOT NULL	Audit action type	reservation_created
entity_type	VARCHAR(50)	NOT NULL	Type of entity	reservation
entity_id	VARCHAR(50)	NOT NULL	Entity identifier	201
user_id	BIGINT	NULLABLE	User who performed action	5
user_email	VARCHAR(255)	NULLABLE	User email at time	john@example.com
ip_address	INET	NULLABLE	IP address	192.168.1.1
user_agent	TEXT	NULLABLE	User agent string	Mozilla/5.0...
old_values	JSONB	NULLABLE	Previous values	{"status": "pending"}
new_values	JSONB	NULLABLE	New values	{"status": "confirmed"}
metadata	JSONB	NULLABLE	Additional context	{"reason": "payment received"}
Indexes:

idx_audit_timestamp on timestamp

idx_audit_action on action

idx_audit_entity on entity_type, entity_id

idx_audit_user_id on user_id

Lookup Tables
Status Types
Status Type	Possible Values	Description
Reservation Status	pending, confirmed, checked_in, completed, cancelled, no_show, expired	Current state of a reservation
Payment Status	pending, authorized, paid, failed, refunded, partially_refunded, cancelled	State of payment processing
User Status	active, inactive, suspended, locked, pending_verification, deleted	State of user account
Parking Spot Status	available, occupied, reserved, maintenance, out_of_service	Current availability of spot
Waitlist Status	active, notified, expired, converted, cancelled	State of waitlist entry
Type Classifications
Type	Possible Values	Description
Reservation Type	standard, vip, ev_charging, oversize, disabled, monthly	Category of reservation
Parking Spot Type	standard, vip, ev_charging, oversize, disabled, motorcycle, compact	Category of parking spot
Vehicle Type	sedan, suv, truck, van, motorcycle, rv, bus, compact	Category of vehicle
User Role	customer, vip_customer, business_customer, attendant, manager, admin, super_admin	User permission level
Payment Method	credit_card, debit_card, paypal, apple_pay, google_pay, cash, bank_transfer, crypto, company_account	Method of payment
Data Types Reference
Data Type	Description	Range/Format
BIGINT	64-bit integer	-9,223,372,036,854,775,808 to 9,223,372,036,854,775,807
INTEGER	32-bit integer	-2,147,483,648 to 2,147,483,647
DECIMAL(10,2)	Fixed-point decimal	Up to 10 digits total, 2 decimal places
VARCHAR(n)	Variable-length string	Up to n characters
TEXT	Variable-length string	Unlimited length
BOOLEAN	Boolean value	true/false
DATE	Calendar date	YYYY-MM-DD
TIME	Time of day	HH:MM:SS
TIMESTAMPTZ	Timestamp with time zone	YYYY-MM-DD HH:MM:SS TZ
JSONB	Binary JSON data	Any valid JSON
INET	IP address	IPv4 or IPv6
INTEGER[]	Array of integers	[1, 2, 3]
Business Rules
Reservation Rules
Minimum reservation duration: 1 hour

Maximum reservation duration: 24 hours

Maximum advance booking: 30 days

Cancellation window: 2 hours before start time

Grace period for check-in: 30 minutes

No-show threshold: 30 minutes after start time

Payment Rules
Refund window: 30 days from payment date

Payment timeout: 300 seconds

Maximum retry attempts: 3

Waitlist Rules
Maximum waitlist position: 10

Notification expiry: 2 hours

Waitlist entry expiry: 2 days

Security Rules
Password minimum length: 8 characters

Password maximum length: 128 characters

Maximum login attempts: 5

Account lockout duration: 15 minutes

Indexes Summary
Index Name	Table	Columns	Type	Purpose
idx_users_email	users	email	UNIQUE	Fast user lookup by email
idx_reservations_user_id	reservations	user_id	BTREE	Find user's reservations
idx_reservations_spot_id	reservations	spot_id	BTREE	Find spot's reservations
idx_reservations_confirmation_code	reservations	confirmation_code	UNIQUE	Lookup by confirmation code
idx_reservations_date_range	reservations	start_time, end_time	BTREE	Find overlapping reservations
idx_waitlist_spot_date	waitlist	spot_id, date_from	BTREE	Find waitlist by spot and date
idx_payments_transaction_id	payments	transaction_id	UNIQUE	Lookup by provider transaction ID
Constraints Summary
Primary Keys
All tables have id as primary key with auto-increment

Foreign Keys
Constraint	Table	Foreign Table	On Delete
fk_reservations_user	reservations	users	RESTRICT
fk_reservations_spot	reservations	parking_spots	RESTRICT
fk_reservations_vehicle	reservations	vehicles	RESTRICT
fk_vehicles_user	vehicles	users	CASCADE
fk_payments_reservation	payments	reservations	RESTRICT
fk_waitlist_user	waitlist	users	CASCADE
fk_waitlist_spot	waitlist	parking_spots	CASCADE
Unique Constraints
Constraint	Table	Columns
uniq_users_email	users	email
uniq_spots_spot_number	parking_spots	spot_number
uniq_vehicles_license_plate	vehicles	license_plate
uniq_reservations_confirmation_code	reservations	confirmation_code
uniq_recurring_pattern_id	recurring_reservations	pattern_id
Check Constraints
Constraint	Table	Condition
chk_reservation_dates	reservations	end_time > start_time
chk_reservation_amount	reservations	total_amount >= 0
chk_payment_amount	payments	amount > 0
chk_waitlist_position	waitlist	position > 0
chk_user_age	users	birth_date <= current_date - interval '18 years' (if applicable)
Document Version History
Version	Date	Author	Changes
1.0.0	2024-01-15	Parking System Team	Initial version
Appendix: JSON Field Schemas
User Preferences Schema
json
{
  "notifications": {
    "email": true,
    "sms": false,
    "push": true
  },
  "language": "en",
  "timezone": "America/New_York",
  "preferred_payment_method": "credit_card"
}
Reservation Metadata Schema
json
{
  "source": "web|mobile_app|api|admin",
  "promo_code": "string",
  "customer_rating": 1-5,
  "created_by": "user_id|system",
  "modified_by": "user_id|system"
}
Parking Spot Features Schema
json
{
  "features": [
    "near_elevator",
    "covered",
    "security_camera",
    "ev_charging",
    "handicap_accessible"
  ]
}
Audit Metadata Schema
json
{
  "request_id": "uuid",
  "session_id": "string",
  "additional_context": {}
}
This document is maintained by the Parking Management System development team. For questions or updates, contact the system administrator.

text

This comprehensive `data_dictionary.md` provides:

1. **Document Information**: Version, date, and metadata
2. **Entity Relationship Diagram**: Visual representation of data relationships
3. **Core Tables**: Detailed documentation for Users, Parking Spots, Vehicles, Reservations
4. **Supporting Tables**: Recurring reservations, waitlist, history, notes, addons, payments
5. **Audit Tables**: Complete audit trail structure
6. **Lookup Tables**: All enum values and type classifications
7. **Data Types Reference**: PostgreSQL data types with ranges
8. **Business Rules**: Application logic constraints
9. **Indexes**: Complete index listing with purposes
10. **Constraints**: Primary keys, foreign keys, unique constraints, check constraints
11. **JSON Field Schemas**: Structure for JSONB fields
12. **Version History**: Document change tracking

The data dictionary is designed to be:
- **Comprehensive**: Covers all database objects
- **Standardized**: Consistent format for all tables
- **Useful**: Practical examples for each field
- **Maintainable**: Easy to update with version history
- **Reference-ready**: Complete documentation for developers and DBAs