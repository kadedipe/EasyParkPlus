
## 13. `data_flow_diagrams.md`
```markdown
# Data Flow Diagrams - Parking Management System

## System-Wide Data Flow

### 1. Level 0 - Context Diagram
```plantuml
@startuml
title "Parking Management System - Context Diagram"

rectangle "Parking Management System" as System {
  (Process Parking\nTransactions) as P1
  (Manage Customer\nAccounts) as P2
  (Handle Reservations) as P3
  (Generate Reports) as P4
  (Monitor Parking\nSpots) as P5
}

entity "Customer" as Customer
entity "Parking Attendant" as Attendant
entity "System Administrator" as Admin
entity "Maintenance Staff" as Maintenance

entity "Payment Gateway" as PaymentGateway
entity "SMS Gateway" as SMSGateway
entity "Email Service" as EmailService
entity "Mapping Service" as MapService

' Data flows from external entities
Customer --> P1 : Parking request\nVehicle details
Customer --> P2 : Registration data\nLogin credentials
Customer --> P3 : Reservation request\nPreferences

Attendant --> P1 : Manual ticket entry\nPayment processing
Admin --> P4 : Report criteria\nConfiguration data
Maintenance --> P5 : Status updates\nRepair reports

' Data flows to external entities
P1 --> PaymentGateway : Payment authorization\nTransaction data
P1 --> Customer : Parking ticket\nPayment receipt

P2 --> SMSGateway : Verification codes\nAccount alerts
P2 --> EmailService : Welcome emails\nPassword reset

P3 --> Customer : Reservation confirmation\nReminders
P3 --> MapService : Location data\nDirections

P4 --> Admin : Financial reports\nUsage statistics
P5 --> Maintenance : Maintenance alerts\nWork orders

' Internal data flows
P1 --> P2 : Update customer history
P1 --> P5 : Update spot status
P3 --> P1 : Pre-paid parking data
P5 --> P4 : Occupancy statistics

@enduml