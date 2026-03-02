
## 9. `state_machine_diagrams.md`
```markdown
# State Machine Diagrams - Parking Management System

## Core Object States

### 1. Parking Spot State Machine
```plantuml
@startuml
title Parking Spot State Machine
state "AVAILABLE" as Available {
  state "Idle" as Idle
  state "Reserved" as Reserved
}

state "OCCUPIED" as Occupied {
  state "Active Parking" as Active
  state "Grace Period" as Grace
}

state "MAINTENANCE" as Maintenance {
  state "Scheduled" as Scheduled
  state "In Progress" as InProgress
  state "Testing" as Testing
}

state "BLOCKED" as Blocked

[*] --> Available : Spot created
Available --> Reserved : Reservation made
Reserved --> Available : Reservation cancelled\nor expired
Reserved --> Occupied : Vehicle arrives
Available --> Occupied : Vehicle parks
Occupied --> Available : Vehicle exits
Occupied --> Grace : Parking time expired
Grace --> Available : Vehicle exits\n(within grace period)
Grace --> Blocked : Vehicle overstays
Available --> Maintenance : Maintenance scheduled
Maintenance --> Available : Maintenance completed
Occupied --> Maintenance : Emergency maintenance
Blocked --> Available : Fine paid\n& vehicle removed

@enduml