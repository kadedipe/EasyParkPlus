
## 12. `architecture_diagrams.md`
```markdown
# Architecture Diagrams - Parking Management System

## System Architecture Overview

### 1. High-Level System Architecture
```plantuml
@startuml
!pragma layout smetana

title "Parking Management System - High Level Architecture"

package "Presentation Layer" {
  [Web Portal\nAngular/React] as Web
  [Mobile App\nReact Native/Flutter] as Mobile
  [Kiosk Interface\nTouchscreen] as Kiosk
  [Admin Dashboard\nVue.js] as Admin
}

package "API Gateway Layer" {
  [API Gateway\nKong/Spring Cloud Gateway] as Gateway
  [Load Balancer\nNGINX] as LB
  [Authentication Service] as Auth
  [Rate Limiter] as RateLimit
}

package "Application Layer" {
  [Parking Management Service] as ParkingService
  [Payment Processing Service] as PaymentService
  [Reservation Service] as ReservationService
  [Notification Service] as NotificationService
  [Reporting Service] as ReportingService
  [User Management Service] as UserService
}

package "Integration Layer" {
  [Payment Gateway Integration] as PaymentGateway
  [SMS Gateway Integration] as SMSGateway
  [Email Service Integration] as EmailService
  [Mapping Service Integration] as MappingService
  [Weather Service Integration] as WeatherService
}

package "Data Layer" {
  database "Primary Database\nPostgreSQL" as Postgres
  database "Cache\nRedis" as Redis
  database "Message Queue\nRabbitMQ/Kafka" as MQ
  database "File Storage\nS3/MinIO" as S3
  database "Time Series DB\nInfluxDB" as TSDB
}

package "Infrastructure Layer" {
  [Monitoring\nPrometheus/Grafana] as Monitoring
  [Logging\nELK Stack] as Logging
  [Container Orchestration\nKubernetes] as K8s
  [CI/CD Pipeline\nJenkins/GitLab CI] as CICD
}

' Connections
Web --> Gateway
Mobile --> Gateway
Kiosk --> Gateway
Admin --> Gateway

Gateway --> Auth
Gateway --> RateLimit
Gateway --> ParkingService
Gateway --> PaymentService
Gateway --> ReservationService
Gateway --> UserService

ParkingService --> Postgres
PaymentService --> Postgres
ReservationService --> Postgres
UserService --> Postgres

ParkingService --> Redis : Cache
ParkingService --> MQ : Events
PaymentService --> PaymentGateway : Process Payments
NotificationService --> SMSGateway : Send SMS
NotificationService --> EmailService : Send Emails

ReportingService --> Postgres : Read Data
ReportingService --> TSDB : Metrics

Monitoring --> All Services : Monitor
Logging --> All Services : Collect Logs
K8s --> All Services : Orchestrate
CICD --> All Services : Deploy

@enduml