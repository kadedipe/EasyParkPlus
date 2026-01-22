
## 11. `entity_relationship_diagrams.md`
```markdown
# Entity-Relationship Diagrams - Parking Management System

## Complete Database Schema

### 1. Core Entity-Relationship Diagram
```plantuml
@startuml
!pragma layout smetana

title "Parking Management System - ER Diagram"

entity "Customer" as customer {
  * customer_id : UUID <<PK>>
  --
  first_name : VARCHAR(50)
  last_name : VARCHAR(50)
  email : VARCHAR(100) <<UNIQUE>>
  phone : VARCHAR(20)
  password_hash : VARCHAR(255)
  registration_date : TIMESTAMP
  last_login : TIMESTAMP
  status : VARCHAR(20)
  loyalty_points : INTEGER
}

entity "Vehicle" as vehicle {
  * vehicle_id : UUID <<PK>>
  * customer_id : UUID <<FK>>
  --
  license_plate : VARCHAR(20) <<UNIQUE>>
  make : VARCHAR(50)
  model : VARCHAR(50)
  year : INTEGER
  color : VARCHAR(30)
  vehicle_type : VARCHAR(20)
  is_electric : BOOLEAN
  registration_date : DATE
}

entity "ParkingLot" as lot {
  * lot_id : UUID <<PK>>
  --
  name : VARCHAR(100)
  address : TEXT
  total_capacity : INTEGER
  latitude : DECIMAL(10,8)
  longitude : DECIMAL(11,8)
  opening_time : TIME
  closing_time : TIME
  is_24_hours : BOOLEAN
  status : VARCHAR(20)
}

entity "ParkingSpot" as spot {
  * spot_id : UUID <<PK>>
  * lot_id : UUID <<FK>>
  --
  spot_number : VARCHAR(10)
  floor_level : INTEGER
  zone : VARCHAR(10)
  spot_type : VARCHAR(20)
  rate_per_hour : DECIMAL(8,2)
  is_covered : BOOLEAN
  has_charger : BOOLEAN
  width : DECIMAL(5,2)
  length : DECIMAL(5,2)
  status : VARCHAR(20)
}

entity "Reservation" as reservation {
  * reservation_id : UUID <<PK>>
  * customer_id : UUID <<FK>>
  * spot_id : UUID <<FK>>
  * vehicle_id : UUID <<FK>>
  --
  start_time : TIMESTAMP
  end_time : TIMESTAMP
  reservation_date : DATE
  status : VARCHAR(20)
  amount : DECIMAL(10,2)
  payment_status : VARCHAR(20)
  created_at : TIMESTAMP
  cancelled_at : TIMESTAMP
}

entity "ParkingTicket" as ticket {
  * ticket_id : UUID <<PK>>
  * customer_id : UUID <<FK>>
  * vehicle_id : UUID <<FK>>
  * spot_id : UUID <<FK>>
  --
  entry_time : TIMESTAMP
  exit_time : TIMESTAMP
  ticket_number : VARCHAR(20) <<UNIQUE>>
  ticket_type : VARCHAR(20)
  duration_minutes : INTEGER
  base_amount : DECIMAL(10,2)
  total_amount : DECIMAL(10,2)
  status : VARCHAR(20)
  issued_by : VARCHAR(50)
}

entity "Payment" as payment {
  * payment_id : UUID <<PK>>
  * customer_id : UUID <<FK>>
  * ticket_id : UUID <<FK>>
  --
  amount : DECIMAL(10,2)
  payment_method : VARCHAR(30)
  transaction_id : VARCHAR(100) <<UNIQUE>>
  status : VARCHAR(20)
  currency : CHAR(3)
  payment_date : TIMESTAMP
  gateway_response : TEXT
  refund_amount : DECIMAL(10,2)
}

entity "Invoice" as invoice {
  * invoice_id : UUID <<PK>>
  * payment_id : UUID <<FK>>
  --
  invoice_number : VARCHAR(50) <<UNIQUE>>
  invoice_date : DATE
  due_date : DATE
  tax_amount : DECIMAL(10,2)
  discount_amount : DECIMAL(10,2)
  total_amount : DECIMAL(10,2)
  status : VARCHAR(20)
  pdf_path : VARCHAR(255)
}

entity "Maintenance" as maintenance {
  * maintenance_id : UUID <<PK>>
  * spot_id : UUID <<FK>>
  * technician_id : UUID <<FK>>
  --
  issue_type : VARCHAR(50)
  description : TEXT
  priority : VARCHAR(20)
  scheduled_date : DATE
  completed_date : DATE
  status : VARCHAR(20)
  cost : DECIMAL(10,2)
  notes : TEXT
}

entity "Technician" as technician {
  * technician_id : UUID <<PK>>
  --
  name : VARCHAR(100)
  specialization : VARCHAR(50)
  phone : VARCHAR(20)
  email : VARCHAR(100)
  status : VARCHAR(20)
  hourly_rate : DECIMAL(8,2)
}

' Relationships
customer ||--o{ vehicle : "owns"
customer ||--o{ reservation : "makes"
customer ||--o{ ticket : "receives"
customer ||--o{ payment : "makes"

lot ||--o{ spot : "contains"

spot ||--o{ reservation : "reserved for"
spot ||--o{ ticket : "used for"
spot ||--o{ maintenance : "requires"

vehicle ||--o{ reservation : "used for"
vehicle ||--o{ ticket : "parked with"

reservation }o--|| ticket : "converted to"

ticket ||--o{ payment : "paid by"
payment }o--|| invoice : "generates"

technician ||--o{ maintenance : "performs"

@enduml