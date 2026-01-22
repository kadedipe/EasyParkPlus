
## 5. `package_diagrams.md`
```markdown
# Package Diagrams - Parking Management System

## System Package Structure

```plantuml
@startuml
skinparam package {
    BackgroundColor White
    BorderColor #2C3E50
    FontColor Black
}

package "com.parkingsystem" {
    package "domain" {
        package "entities" {
            [Vehicle]
            [ParkingSpot]
            [Customer]
            [Ticket]
            [Payment]
            [Reservation]
        }
        
        package "valueobjects" {
            [Money]
            [TimeRange]
            [Location]
            [LicensePlate]
        }
        
        package "enums" {
            [SpotType]
            [VehicleType]
            [PaymentStatus]
            [TicketStatus]
        }
        
        package "exceptions" {
            [ParkingException]
            [PaymentException]
            [ValidationException]
        }
    }
    
    package "application" {
        package "services" {
            [ParkingService]
            [PaymentService]
            [ReservationService]
            [NotificationService]
        }
        
        package "commands" {
            [EnterParkingCommand]
            [ExitParkingCommand]
            [MakePaymentCommand]
            [CreateReservationCommand]
        }
        
        package "queries" {
            [FindAvailableSpotsQuery]
            [GetCustomerTicketsQuery]
            [GenerateReportQuery]
        }
        
        package "dtos" {
            [ParkingSpotDTO]
            [TicketDTO]
            [CustomerDTO]
            [PaymentDTO]
        }
    }
    
    package "infrastructure" {
        package "persistence" {
            package "repositories" {
                [ParkingSpotRepository]
                [CustomerRepository]
                [TicketRepository]
                [PaymentRepository]
            }
            
            package "entities" {
                [ParkingSpotEntity]
                [CustomerEntity]
                [TicketEntity]
                [PaymentEntity]
            }
            
            package "mappers" {
                [ParkingSpotMapper]
                [CustomerMapper]
                [TicketMapper]
                [PaymentMapper]
            }
        }
        
        package "external" {
            [PaymentGatewayAdapter]
            [SMSGatewayAdapter]
            [EmailServiceAdapter]
            [GISServiceAdapter]
        }
        
        package "messaging" {
            [EventPublisher]
            [EventSubscriber]
            [MessageQueue]
            [DeadLetterQueue]
        }
        
        package "cache" {
            [SpotAvailabilityCache]
            [CustomerSessionCache]
            [RateCache]
        }
    }
    
    package "presentation" {
        package "controllers" {
            [ParkingController]
            [PaymentController]
            [ReservationController]
            [AdminController]
        }
        
        package "views" {
            [ParkingLotView]
            [PaymentView]
            [ReservationView]
            [AdminDashboardView]
        }
        
        package "models" {
            [ParkingRequest]
            [PaymentRequest]
            [ReservationRequest]
            [AdminRequest]
        }
    }
    
    package "common" {
        package "utils" {
            [DateUtils]
            [MoneyUtils]
            [ValidationUtils]
            [SecurityUtils]
        }
        
        package "logging" {
            [AuditLogger]
            [ErrorLogger]
            [PerformanceLogger]
        }
        
        package "config" {
            [ApplicationConfig]
            [DatabaseConfig]
            [SecurityConfig]
            [CacheConfig]
        }
    }
}

' Dependencies
[presentation.controllers] --> [application.services]
[application.services] --> [domain.entities]
[application.services] --> [infrastructure.persistence.repositories]
[infrastructure.persistence.repositories] --> [infrastructure.persistence.entities]
[infrastructure.external] --> [application.services]
[common.utils] --> [application.services]
[common.logging] --> [application.services]

@enduml