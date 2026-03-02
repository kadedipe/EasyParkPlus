
## 10. `communication_diagrams.md`
```markdown
# Communication Diagrams - Parking Management System

## System Interaction Overview

### 1. Parking Reservation Communication
```plantuml
@startuml
!pragma layout smetana

title "Parking Reservation Communication Flow"

object "Customer" as Customer
object "Mobile App" as App
object "API Gateway" as Gateway
object "Reservation Service" as Reservation
object "Payment Service" as Payment
object "Spot Manager" as SpotManager
object "Notification Service" as Notification
object "Database" as DB

' Sequence of communications
Customer -> App : 1: Search parking spots
App -> Gateway : 2: GET /api/spots/available
Gateway -> Reservation : 3: Forward request
Reservation -> SpotManager : 4: Get available spots
SpotManager -> DB : 5: Query available spots
DB --> SpotManager : 6: Return spot data
SpotManager --> Reservation : 7: Available spots
Reservation --> Gateway : 8: Spot list
Gateway --> App : 9: Display spots

Customer -> App : 10: Select spot & time
App -> Gateway : 11: POST /api/reservations
Gateway -> Reservation : 12: Create reservation
Reservation -> SpotManager : 13: Lock spot
SpotManager -> DB : 14: Update spot status
DB --> SpotManager : 15: Status updated
SpotManager --> Reservation : 16: Spot locked
Reservation -> Payment : 17: Calculate price
Payment -> DB : 18: Get rate data
DB --> Payment : 19: Rate information
Payment --> Reservation : 20: Calculated amount
Reservation --> Gateway : 21: Reservation quote
Gateway --> App : 22: Show payment page

Customer -> App : 23: Confirm payment
App -> Gateway : 24: POST /api/payments
Gateway -> Payment : 25: Process payment
Payment -> "Payment Gateway" : 26: Authorize payment
"Payment Gateway" --> Payment : 27: Authorization code
Payment -> DB : 28: Record transaction
DB --> Payment : 29: Transaction saved
Payment --> Reservation : 30: Payment confirmed
Reservation -> SpotManager : 31: Confirm reservation
SpotManager -> DB : 32: Finalize reservation
DB --> SpotManager : 33: Reservation saved
SpotManager --> Reservation : 34: Reservation confirmed
Reservation -> Notification : 35: Send confirmation
Notification -> App : 36: Push notification
Notification -> "Email Service" : 37: Send email
Notification -> "SMS Service" : 38: Send SMS
Reservation --> Gateway : 39: Success response
Gateway --> App : 40: Show confirmation
App --> Customer : 41: Reservation complete
@enduml