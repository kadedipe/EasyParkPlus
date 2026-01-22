# Class Diagrams - Parking Management System

## Overview
This document contains class diagrams representing the static structure of the Parking Management System.

## Main Class Diagram

### PlantUML Version
```plantuml
@startuml
skinparam class {
    BackgroundColor White
    BorderColor Black
    ArrowColor #2E4053
    FontColor Black
}

package "Parking Management System" {
    class ParkingSystem {
        -systemId: String
        -name: String
        -totalSpots: Integer
        -availableSpots: Integer
        +checkAvailability(): Boolean
        +reserveSpot(): Boolean
        +calculateFee(): Double
        +generateTicket(): Ticket
    }

    class ParkingSpot {
        -spotId: String
        -type: SpotType
        -status: SpotStatus
        -location: String
        -ratePerHour: Double
        +isAvailable(): Boolean
        +reserve(): Boolean
        +release(): void
    }

    enum SpotType {
        COMPACT
        REGULAR
        HANDICAPPED
        ELECTRIC
        VIP
    }

    enum SpotStatus {
        AVAILABLE
        OCCUPIED
        RESERVED
        MAINTENANCE
    }

    class Vehicle {
        -vehicleId: String
        -licensePlate: String
        -type: VehicleType
        -owner: Customer
        +enterParking(): void
        +exitParking(): void
    }

    enum VehicleType {
        CAR
        MOTORCYCLE
        TRUCK
        ELECTRIC
        COMPACT
    }

    class Customer {
        -customerId: String
        -name: String
        -email: String
        -phone: String
        -paymentMethods: List<PaymentMethod>
        +register(): void
        +login(): Boolean
        +makePayment(): Boolean
    }

    class Ticket {
        -ticketId: String
        -entryTime: DateTime
        -exitTime: DateTime
        -spot: ParkingSpot
        -vehicle: Vehicle
        -totalAmount: Double
        +calculateDuration(): Integer
        +calculateTotal(): Double
        +validate(): Boolean
    }

    class Payment {
        -paymentId: String
        -amount: Double
        -method: PaymentMethod
        -status: PaymentStatus
        -timestamp: DateTime
        +processPayment(): Boolean
        +refund(): Boolean
        +generateReceipt(): Receipt
    }

    enum PaymentMethod {
        CASH
        CREDIT_CARD
        DEBIT_CARD
        MOBILE_WALLET
        SUBSCRIPTION
    }

    enum PaymentStatus {
        PENDING
        COMPLETED
        FAILED
        REFUNDED
    }

    class Receipt {
        -receiptId: String
        -payment: Payment
        -customer: Customer
        -details: String
        +generatePDF(): Blob
        +sendEmail(): Boolean
    }

    class Admin {
        -adminId: String
        -username: String
        -permissions: List<String>
        +addSpot(): void
        +removeSpot(): void
        +modifyRates(): void
        +generateReport(): Report
    }

    class Report {
        -reportId: String
        -type: ReportType
        -data: JSON
        -generatedAt: DateTime
        +generate(): void
        +exportToCSV(): Blob
        +sendToEmail(): Boolean
    }

    enum ReportType {
        DAILY
        WEEKLY
        MONTHLY
        FINANCIAL
        UTILIZATION
    }

    ' Relationships
    ParkingSystem "1" *-- "many" ParkingSpot : contains
    ParkingSystem "1" -- "many" Ticket : generates
    Vehicle "1" -- "1" Customer : owned by
    Ticket "1" -- "1" Vehicle : for
    Ticket "1" -- "1" ParkingSpot : assigned to
    Payment "1" -- "1" Ticket : pays for
    Customer "1" -- "many" Payment : makes
    Admin "1" -- "many" Report : generates
    ParkingSystem "1" -- "1" Admin : managed by
}

@enduml