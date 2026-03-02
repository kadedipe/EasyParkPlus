
## 4. `object_diagrams.md`
```markdown
# Object Diagrams - Parking Management System

## Runtime Object Instances

### 1. Parking Lot Instance at Peak Hours
```plantuml
@startuml
object "ParkingLot:pl001" as pl001 {
  name = "Downtown Mall Parking"
  totalSpots = 500
  availableSpots = 120
  hourlyRate = 2.50
  dailyMax = 25.00
}

object "ParkingSpot:ps001" as ps001 {
  spotId = "A-101"
  type = "REGULAR"
  status = "OCCUPIED"
  rate = 2.50
}

object "ParkingSpot:ps002" as ps002 {
  spotId = "A-102"
  type = "COMPACT"
  status = "AVAILABLE"
  rate = 2.00
}

object "ParkingSpot:ps003" as ps003 {
  spotId = "B-201"
  type = "HANDICAPPED"
  status = "RESERVED"
  rate = 1.50
}

object "ParkingSpot:ps004" as ps004 {
  spotId = "C-301"
  type = "ELECTRIC"
  status = "OCCUPIED"
  rate = 3.00
}

object "ParkingSpot:ps005" as ps005 {
  spotId = "D-401"
  type = "VIP"
  status = "MAINTENANCE"
  rate = 5.00
}

pl001 --> ps001 : contains
pl001 --> ps002 : contains
pl001 --> ps003 : contains
pl001 --> ps004 : contains
pl001 --> ps005 : contains

object "Vehicle:v001" as v001 {
  licensePlate = "ABC123"
  type = "CAR"
  make = "Toyota"
  model = "Camry"
}

object "Customer:c001" as c001 {
  customerId = "CUST001"
  name = "John Doe"
  email = "john@example.com"
  phone = "+1234567890"
}

object "Ticket:t001" as t001 {
  ticketId = "TKT001"
  entryTime = "2024-01-15 09:30:00"
  expectedExit = "2024-01-15 17:00:00"
  amountDue = 18.75
}

object "Payment:p001" as p001 {
  paymentId = "PAY001"
  amount = 18.75
  method = "CREDIT_CARD"
  status = "COMPLETED"
  timestamp = "2024-01-15 17:05:00"
}

c001 --> v001 : owns
v001 --> t001 : has
t001 --> ps001 : assigned to
t001 --> p001 : paid by

note right of pl001
  Active parking lot instance
  during business hours
  120 spots available
  380 spots occupied
end note

@enduml