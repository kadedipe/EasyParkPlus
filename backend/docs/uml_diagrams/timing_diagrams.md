
## 14. `timing_diagrams.md`
```markdown
# Timing Diagrams - Parking Management System

## System Timing and Sequence Constraints

### 1. Vehicle Entry Timing Diagram
```plantuml
@startuml
title "Vehicle Entry Timing Sequence"

robust "Driver" as Driver
robust "License Plate Reader" as LPR
robust "Entry Barrier" as Barrier
robust "Parking System" as System
robust "Payment System" as Payment

Driver -> LPR : Vehicle approaches\n(0ms)
LPR -> System : Send plate image\n(100ms)
System -> System : Process plate recognition\n(200ms)
System -> System : Check reservation\n(50ms)
System -> Payment : Validate pre-payment\n(100ms)
Payment -> System : Payment status\n(50ms)

alt Has valid reservation/pre-payment
    System -> Barrier : Open barrier\n(50ms)
    Barrier -> Driver : Barrier opens\n(100ms)
    Driver -> Barrier : Drive through\n(500ms)
    Barrier -> System : Vehicle entered\n(50ms)
    System -> System : Update spot status\n(100ms)
else No reservation
    System -> System : Assign available spot\n(100ms)
    System -> Driver : Display instructions\n(200ms)
    Driver -> System : Accept terms\n(varies)
    System -> Barrier : Open barrier\n(50ms)
    Barrier -> Driver : Barrier opens\n(100ms)
end

@enduml