
## 7. `sequence_diagrams.md`
```markdown
# Sequence Diagrams - Parking Management System

## Core System Interactions

### 1. Vehicle Entry Sequence
```plantuml
@startuml
title Vehicle Entry Process
participant "Customer" as Customer
participant "Entry Gate\nSystem" as EntryGate
participant "License Plate\nReader" as LPR
participant "Parking\nController" as ParkingCtrl
participant "Spot\nManager" as SpotManager
participant "Ticket\nPrinter" as TicketPrinter
participant "Payment\nService" as PaymentService
participant "Database" as DB

Customer -> EntryGate : Approach entry gate
EntryGate -> LPR : Capture license plate
LPR -> ParkingCtrl : Send plate number

alt Regular Entry
    ParkingCtrl -> DB : Check for reservation
    DB --> ParkingCtrl : Return reservation details
    
    ParkingCtrl -> SpotManager : Assign available spot
    SpotManager -> DB : Find optimal spot
    DB --> SpotManager : Return spot details
    SpotManager --> ParkingCtrl : Spot assigned
    
    ParkingCtrl -> TicketPrinter : Generate ticket
    TicketPrinter --> Customer : Issue ticket
    
    ParkingCtrl -> EntryGate : Open barrier
    EntryGate --> Customer : Barrier opens
    
else Pre-paid/Subscription Entry
    ParkingCtrl -> PaymentService : Validate subscription
    PaymentService -> DB : Check active subscription
    DB --> PaymentService : Subscription status
    PaymentService --> ParkingCtrl : Valid subscription
    
    ParkingCtrl -> SpotManager : Assign reserved spot
    SpotManager --> ParkingCtrl : Spot confirmed
    
    ParkingCtrl -> EntryGate : Open barrier
    EntryGate --> Customer : Barrier opens
end

ParkingCtrl -> DB : Log entry transaction
Customer -> EntryGate : Drive through
EntryGate -> ParkingCtrl : Vehicle entered
ParkingCtrl -> DB : Update spot status to OCCUPIED
@enduml