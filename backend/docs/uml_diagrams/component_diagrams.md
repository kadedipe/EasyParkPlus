# Component Diagrams - Parking Management System

## System Architecture Overview

```plantuml
@startuml
skinparam component {
    BackgroundColor White
    BorderColor #2C3E50
    FontColor Black
}

package "Parking Management System" {
    [User Interface] as UI
    [API Gateway] as Gateway
    [Authentication Service] as Auth
    [Parking Management Service] as PMS
    [Payment Service] as Payment
    [Notification Service] as Notification
    [Reporting Service] as Reporting
    [Database] as DB
    [Cache] as Cache
    [Message Queue] as MQ
}

package "External Systems" {
    [Payment Gateway] as PG
    [SMS Gateway] as SMS
    [Email Service] as Email
}

' Connections
UI --> Gateway : HTTP/HTTPS
Gateway --> Auth : Authenticate
Gateway --> PMS : Process Requests
Gateway --> Payment : Handle Payments
Gateway --> Notification : Send Alerts
Gateway --> Reporting : Generate Reports

PMS --> DB : CRUD Operations
Payment --> DB : Store Transactions
Auth --> DB : User Data
Reporting --> DB : Read Data

PMS --> Cache : Session Data
Payment --> Cache : Transaction Cache

PMS --> MQ : Events
Notification --> MQ : Consume Events

Payment --> PG : Process Payment
Notification --> SMS : Send SMS
Notification --> Email : Send Email

' Notes
note right of UI
    Web Portal
    Mobile App
    Kiosk Interface
end note

note right of DB
    PostgreSQL
    MongoDB
    Redis
end note

@enduml