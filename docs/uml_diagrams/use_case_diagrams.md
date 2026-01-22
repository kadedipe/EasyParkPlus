
## 6. `use_case_diagrams.md`
```markdown
# Use Case Diagrams - Parking Management System

## System Actors

```plantuml
@startuml
left to right direction

actor Customer as Customer
actor "Parking Attendant" as Attendant
actor "System Administrator" as Admin
actor "Maintenance Staff" as Maintenance
actor "Security Officer" as Security
actor "Payment Gateway" as PaymentGateway
actor "Mobile App" as MobileApp
actor "Kiosk" as Kiosk

rectangle "Parking Management System" {
  (Enter Parking Lot) as UC1
  (Exit Parking Lot) as UC2
  (Find Available Parking Spot) as UC3
  (Reserve Parking Spot) as UC4
  (Make Payment) as UC5
  (View Parking History) as UC6
  (Generate Parking Ticket) as UC7
  (Validate Ticket) as UC8
  (Manage Parking Rates) as UC9
  (Monitor Parking Occupancy) as UC10
  (Generate Reports) as UC11
  (Manage User Accounts) as UC12
  (Handle Maintenance Requests) as UC13
  (Process Refunds) as UC14
  (Send Notifications) as UC15
}

Customer --> UC1
Customer --> UC2
Customer --> UC3
Customer --> UC4
Customer --> UC5
Customer --> UC6

Attendant --> UC7
Attendant --> UC8
Attendant --> UC5

Admin --> UC9
Admin --> UC10
Admin --> UC11
Admin --> UC12

Maintenance --> UC13

Security --> UC10

PaymentGateway --> UC5

MobileApp --> UC3
MobileApp --> UC4
MobileApp --> UC5
MobileApp --> UC6

Kiosk --> UC5
Kiosk --> UC7
Kiosk --> UC8

UC1 ..> UC7 : includes
UC2 ..> UC5 : includes
UC2 ..> UC8 : includes
UC4 ..> UC15 : includes
UC5 ..> PaymentGateway : uses
UC11 ..> UC10 : extends
UC13 ..> UC15 : includes

@enduml