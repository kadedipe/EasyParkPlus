markdown
# Parking Management System - Entity Relationship Diagram

## Document Information
| | |
|---|---|
| **Document Version** | 1.0.0 |
| **Last Updated** | 2024-01-15 |
| **Database** | PostgreSQL 14+ |
| **Author** | Parking Management System Team |

## Document Purpose
This document provides a comprehensive entity relationship diagram (ERD) for the Parking Management System database. It includes visual representations of all tables, their relationships, cardinalities, and key attributes.

---

## Table of Contents
1. [Complete ER Diagram](#complete-er-diagram)
2. [Core Entities](#core-entities)
   - [Users Entity](#users-entity)
   - [Parking Spots Entity](#parking-spots-entity)
   - [Vehicles Entity](#vehicles-entity)
   - [Reservations Entity](#reservations-entity)
3. [Supporting Entities](#supporting-entities)
   - [Recurring Reservations](#recurring-reservations-entity)
   - [Waitlist](#waitlist-entity)
   - [Reservation History](#reservation-history-entity)
   - [Reservation Notes](#reservation-notes-entity)
   - [Reservation Addons](#reservation-addons-entity)
   - [Payments](#payments-entity)
4. [Audit Entities](#audit-entities)
   - [Audit Logs](#audit-logs-entity)
5. [Relationship Summary](#relationship-summary)
6. [Cardinality Guide](#cardinality-guide)
7. [Cascade Rules](#cascade-rules)
8. [Denormalized Relationships](#denormalized-relationships)
9. [Index Relationships](#index-relationships)

---

## Complete ER Diagram

```mermaid
erDiagram
    %% Core Entities
    USERS {
        bigint id PK
        varchar email UK
        varchar full_name
        varchar phone
        varchar password_hash
        varchar role
        varchar status
        varchar verification_status
        jsonb preferences
        jsonb metadata
        timestamptz last_login_at
        timestamptz created_at
        timestamptz updated_at
    }
    
    PARKING_SPOTS {
        bigint id PK
        varchar spot_number UK
        varchar spot_type
        decimal hourly_rate
        decimal charging_fee
        varchar charger_type
        varchar charger_power
        boolean is_active
        boolean is_covered
        boolean is_handicap
        boolean is_near_elevator
        integer level
        varchar section
        varchar row
        jsonb coordinates
        jsonb features
        date last_maintenance
        date next_maintenance
        timestamptz created_at
        timestamptz updated_at
    }
    
    VEHICLES {
        bigint id PK
        bigint user_id FK
        varchar license_plate UK
        varchar vehicle_type
        varchar make
        varchar model
        varchar color
        integer year
        boolean is_ev
        integer battery_capacity
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }
    
    RESERVATIONS {
        bigint id PK
        bigint user_id FK
        bigint spot_id FK
        bigint vehicle_id FK
        varchar confirmation_code UK
        varchar reservation_type
        varchar status
        timestamptz start_time
        timestamptz end_time
        decimal total_amount
        decimal charging_fee
        decimal energy_used_kwh
        varchar payment_status
        bigint payment_id FK
        text special_requests
        text cancellation_reason
        jsonb metadata
        timestamptz created_at
        timestamptz confirmed_at
        timestamptz checked_in_at
        timestamptz checked_out_at
        timestamptz completed_at
        timestamptz cancelled_at
        timestamptz updated_at
    }

    %% Supporting Entities
    RECURRING_RESERVATIONS {
        bigint id PK
        bigint user_id FK
        bigint spot_id FK
        bigint vehicle_id FK
        varchar pattern_id UK
        varchar frequency
        date start_date
        date end_date
        time start_time
        time end_time
        integer[] days_of_week
        integer day_of_month
        varchar monthly_option
        decimal total_amount_per_occurrence
        boolean is_active
        jsonb paused_periods
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }
    
    WAITLIST {
        bigint id PK
        bigint user_id FK
        bigint spot_id FK
        timestamptz date_from
        timestamptz date_to
        varchar status
        integer position
        timestamptz notified_at
        timestamptz expires_at
        timestamptz created_at
        timestamptz updated_at
    }
    
    RESERVATION_HISTORY {
        bigint id PK
        bigint reservation_id FK
        varchar status
        timestamptz changed_at
        varchar changed_by
        text reason
        jsonb metadata
    }
    
    RESERVATION_NOTES {
        bigint id PK
        bigint reservation_id FK
        bigint user_id FK
        text note
        boolean is_private
        timestamptz created_at
        timestamptz updated_at
    }
    
    RESERVATION_ADDONS {
        bigint id PK
        bigint reservation_id FK
        varchar addon_type
        integer quantity
        decimal unit_price
        decimal total_price
        jsonb metadata
        timestamptz created_at
    }
    
    PAYMENTS {
        bigint id PK
        bigint reservation_id FK
        decimal amount
        varchar currency
        varchar status
        varchar payment_method
        varchar provider
        varchar transaction_id UK
        jsonb provider_response
        varchar card_last4
        varchar card_brand
        decimal refunded_amount
        text refund_reason
        timestamptz refunded_at
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }
    
    %% Audit Entities
    AUDIT_LOGS {
        bigint id PK
        timestamptz timestamp
        varchar action
        varchar entity_type
        varchar entity_id
        bigint user_id
        varchar user_email
        inet ip_address
        text user_agent
        jsonb old_values
        jsonb new_values
        jsonb metadata
    }

    %% Relationships
    USERS ||--o{ VEHICLES : owns
    USERS ||--o{ RESERVATIONS : makes
    USERS ||--o{ WAITLIST : joins
    USERS ||--o{ RECURRING_RESERVATIONS : sets_up
    USERS ||--o{ RESERVATION_NOTES : writes
    USERS ||--o{ AUDIT_LOGS : performs
    
    PARKING_SPOTS ||--o{ RESERVATIONS : booked_for
    PARKING_SPOTS ||--o{ WAITLIST : requested_for
    PARKING_SPOTS ||--o{ RECURRING_RESERVATIONS : scheduled_for
    
    VEHICLES ||--o{ RESERVATIONS : used_in
    VEHICLES ||--o{ RECURRING_RESERVATIONS : used_in
    
    RESERVATIONS ||--o{ RESERVATION_HISTORY : has
    RESERVATIONS ||--o{ RESERVATION_NOTES : has
    RESERVATIONS ||--o{ RESERVATION_ADDONS : includes
    RESERVATIONS |o--o{ PAYMENTS : has
    
    RECURRING_RESERVATIONS ||--o{ RESERVATIONS : generates
Core Entities
Users Entity









































Primary Key: id
Unique Constraints: email
Foreign Keys: None (parent table)

Description: Central entity storing all user information including customers, staff, and administrators.

Parking Spots Entity

















































Primary Key: id
Unique Constraints: spot_number
Foreign Keys: None (parent table)

Description: Physical parking spots with their attributes, location, and availability status.

Vehicles Entity




































Primary Key: id
Unique Constraints: license_plate
Foreign Keys: user_id references USERS(id)

Description: Vehicles registered by users for parking reservations.

Reservations Entity





































































Primary Key: id
Unique Constraints: confirmation_code
Foreign Keys:

user_id references USERS(id)

spot_id references PARKING_SPOTS(id)

vehicle_id references VEHICLES(id)

payment_id references PAYMENTS(id)

Description: Core transactional entity storing all parking reservations.

Supporting Entities
Recurring Reservations Entity




















































Primary Key: id
Unique Constraints: pattern_id
Foreign Keys:

user_id references USERS(id)

spot_id references PARKING_SPOTS(id)

vehicle_id references VEHICLES(id)

Description: Defines patterns for recurring reservations that generate individual reservations.

Waitlist Entity






























Primary Key: id
Foreign Keys:

user_id references USERS(id)

spot_id references PARKING_SPOTS(id)

Description: Queue of users waiting for specific parking spots when they become available.

Reservation History Entity



















Primary Key: id
Foreign Keys: reservation_id references RESERVATIONS(id)

Description: Audit trail of status changes for each reservation.

Reservation Notes Entity






















Primary Key: id
Foreign Keys:

reservation_id references RESERVATIONS(id)

user_id references USERS(id)

Description: Notes and comments attached to reservations, with privacy controls.

Reservation Addons Entity





















Primary Key: id
Foreign Keys: reservation_id references RESERVATIONS(id)

Description: Additional services purchased with reservations (valet, car wash, etc.).

Payments Entity








































Primary Key: id
Unique Constraints: transaction_id
Foreign Keys: reservation_id references RESERVATIONS(id)

Description: Payment transactions associated with reservations.

Audit Entities
Audit Logs Entity




























Primary Key: id
Foreign Keys: user_id references USERS(id) (optional)

Description: Comprehensive audit trail for all system actions and data changes.

Relationship Summary
Relationship	From	To	Cardinality	Description
Owns	USERS	VEHICLES	1 : N	One user can own multiple vehicles
Makes	USERS	RESERVATIONS	1 : N	One user can make multiple reservations
Joins	USERS	WAITLIST	1 : N	One user can join multiple waitlists
Sets Up	USERS	RECURRING_RESERVATIONS	1 : N	One user can set up multiple recurring patterns
Writes	USERS	RESERVATION_NOTES	1 : N	One user can write multiple notes
Performs	USERS	AUDIT_LOGS	1 : N	One user can generate multiple audit logs
Books	PARKING_SPOTS	RESERVATIONS	1 : N	One spot can have multiple reservations
Requests	PARKING_SPOTS	WAITLIST	1 : N	One spot can have multiple waitlist entries
Schedules	PARKING_SPOTS	RECURRING_RESERVATIONS	1 : N	One spot can have multiple recurring patterns
Uses	VEHICLES	RESERVATIONS	1 : N	One vehicle can be used in multiple reservations
Includes	VEHICLES	RECURRING_RESERVATIONS	1 : N	One vehicle can be used in multiple recurring patterns
Has History	RESERVATIONS	RESERVATION_HISTORY	1 : N	One reservation can have multiple history entries
Has Notes	RESERVATIONS	RESERVATION_NOTES	1 : N	One reservation can have multiple notes
Has Addons	RESERVATIONS	RESERVATION_ADDONS	1 : N	One reservation can have multiple addons
Has Payment	RESERVATIONS	PAYMENTS	1 : 0..N	One reservation can have zero or multiple payments
Generates	RECURRING_RESERVATIONS	RESERVATIONS	1 : N	One recurring pattern can generate multiple reservations
Cardinality Guide













Cardinality Symbols in Diagrams
Symbol	Meaning	Example
||--o{	One to many (optional)	One user to many reservations
||--||	One to one (mandatory)	One reservation to one payment (if paid)
}o--||	Many to one (optional)	Many reservations to one user
}|--o{	Many to many (optional)	Not used in this schema
|o--o|	One to zero or one	One reservation to zero or one payment
Relationship Types
Mandatory Relationships
User → Vehicle: A vehicle must belong to a user

Reservation → User: A reservation must have a user

Reservation → Spot: A reservation must have a parking spot

Reservation → Vehicle: A reservation must have a vehicle

Optional Relationships
Reservation → Payment: A reservation may not have a payment (pending)

User → Audit Log: An audit log may not have a user (system action)

Reservation → Notes: A reservation may not have notes

Cascade Relationships
User → Vehicles: When user is deleted, their vehicles are also deleted (CASCADE)

User → Waitlist: When user is deleted, their waitlist entries are deleted (CASCADE)

Reservation → History: When reservation is deleted, its history is deleted (CASCADE)

Cascade Rules
Parent Table	Child Table	Delete Rule	Update Rule
USERS	VEHICLES	CASCADE	CASCADE
USERS	RESERVATIONS	RESTRICT	CASCADE
USERS	WAITLIST	CASCADE	CASCADE
USERS	RECURRING_RESERVATIONS	CASCADE	CASCADE
USERS	RESERVATION_NOTES	SET NULL	CASCADE
USERS	AUDIT_LOGS	SET NULL	CASCADE
PARKING_SPOTS	RESERVATIONS	RESTRICT	CASCADE
PARKING_SPOTS	WAITLIST	CASCADE	CASCADE
PARKING_SPOTS	RECURRING_RESERVATIONS	RESTRICT	CASCADE
VEHICLES	RESERVATIONS	RESTRICT	CASCADE
VEHICLES	RECURRING_RESERVATIONS	RESTRICT	CASCADE
RESERVATIONS	RESERVATION_HISTORY	CASCADE	CASCADE
RESERVATIONS	RESERVATION_NOTES	CASCADE	CASCADE
RESERVATIONS	RESERVATION_ADDONS	CASCADE	CASCADE
RESERVATIONS	PAYMENTS	RESTRICT	CASCADE
Cascade Rules Explanation:

CASCADE: When parent is deleted/updated, child is also deleted/updated

RESTRICT: Prevents deletion/update if child records exist

SET NULL: Sets foreign key to NULL when parent is deleted

NO ACTION: Similar to RESTRICT but checked at end of transaction

Denormalized Relationships
Reservation Denormalization
Reservations contain denormalized data for performance:









These fields are denormalized from:

users.email → reservations.user_email

users.full_name → reservations.user_name

parking_spots.spot_number → reservations.spot_number

parking_spots.spot_type → reservations.spot_type

vehicles.license_plate → reservations.license_plate

vehicles.vehicle_type → reservations.vehicle_type

Purpose: Improve query performance and provide historical snapshot of data at reservation time.

Index Relationships


























Index Relationships Summary
Index	Table	Related To	Purpose
idx_reservations_user_id	RESERVATIONS	USERS	Fast lookup of user's reservations
idx_reservations_spot_id	RESERVATIONS	PARKING_SPOTS	Fast lookup of spot's reservations
idx_reservations_vehicle_id	RESERVATIONS	VEHICLES	Fast lookup of vehicle's reservations
idx_vehicles_user_id	VEHICLES	USERS	Fast lookup of user's vehicles
idx_waitlist_user_id	WAITLIST	USERS	Fast lookup of user's waitlist entries
idx_waitlist_spot_id	WAITLIST	PARKING_SPOTS	Fast lookup of spot's waitlist
idx_recurring_user_id	RECURRING	USERS	Fast lookup of user's recurring patterns
idx_recurring_spot_id	RECURRING	PARKING_SPOTS	Fast lookup of spot's recurring patterns
idx_notes_reservation_id	NOTES	RESERVATIONS	Fast lookup of reservation's notes
idx_history_reservation_id	HISTORY	RESERVATIONS	Fast lookup of reservation's history
idx_addons_reservation_id	ADDONS	RESERVATIONS	Fast lookup of reservation's addons
idx_payments_reservation_id	PAYMENTS	RESERVATIONS	Fast lookup of reservation's payments
Document Version History
Version	Date	Author	Changes
1.0.0	2024-01-15	Parking System Team	Initial version
Appendix: Quick Reference
Entity Count Summary
Entity Type	Entity Name	Record Count (Sample)
Core	USERS	~100
Core	PARKING_SPOTS	~50
Core	VEHICLES	~100
Core	RESERVATIONS	~1000
Supporting	RECURRING_RESERVATIONS	~10
Supporting	WAITLIST	~20
Supporting	RESERVATION_HISTORY	~4000
Supporting	RESERVATION_NOTES	~50
Supporting	RESERVATION_ADDONS	~50
Supporting	PAYMENTS	~1000
Audit	AUDIT_LOGS	~5000
Most Common Query Patterns
Find reservations by user: RESERVATIONS ← user_id

Find spot availability: RESERVATIONS ← spot_id, time range

Find user vehicles: VEHICLES ← user_id

Find reservation history: RESERVATION_HISTORY ← reservation_id

Find waitlist position: WAITLIST ← spot_id, date

This document is maintained by the Parking Management System development team. For questions or updates, contact the system administrator.

text

This comprehensive `er_diagram.md` provides:

1. **Complete ER Diagram**: Full Mermaid ER diagram showing all tables and relationships
2. **Entity Details**: Each entity with its complete attribute list
3. **Relationship Visualizations**: Entity-specific relationship diagrams
4. **Relationship Summary**: Comprehensive table of all relationships with cardinalities
5. **Cardinality Guide**: Explanation of symbols used in diagrams
6. **Cascade Rules**: Complete delete/update behavior for all foreign keys
7. **Denormalized Relationships**: Explanation of denormalized fields for performance
8. **Index Relationships**: Visual representation of index dependencies
9. **Quick Reference**: Entity counts and common query patterns

The ER diagram is designed to be:
- **Comprehensive**: Covers all database objects and their relationships
- **Visual**: Easy-to-understand Mermaid diagrams
- **Practical**: Includes cardinalities and business rules
- **Maintainable**: Version controlled with change history
- **Reference-ready**: Complete documentation for developers and DBAs