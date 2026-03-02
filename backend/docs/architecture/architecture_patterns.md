
## 4. **architecture_patterns.md** - Architecture Patterns

```markdown
# Architecture Patterns

## Overview

This document outlines the architectural patterns and design decisions used in the Parking Management System. These patterns ensure scalability, maintainability, and reliability while addressing the specific challenges of parking management.

## Architectural Style

### Hexagonal Architecture (Ports and Adapters)

The system follows Hexagonal Architecture principles to maintain separation between domain logic and infrastructure concerns.

```mermaid
graph TB
    subgraph "External World"
        WEB[Web Clients]
        MOB[Mobile Apps]
        IOT[IoT Devices]
        API[Third-party APIs]
        DB[(Databases)]
    end

    subgraph "Adapters (Infrastructure)"
        WEB_AD[Web Adapter]
        MOB_AD[Mobile Adapter]
        IOT_AD[IoT Adapter]
        API_AD[API Adapter]
        DB_AD[Database Adapter]
    end

    subgraph "Ports (Interfaces)"
        HTTP_P[HTTP Port]
        MQTT_P[MQTT Port]
        DB_P[Database Port]
        MSG_P[Message Port]
    end

    subgraph "Application Core"
        subgraph "Application Layer"
            APP_SVC[Application Services]
            CMD[Command Handlers]
            QRY[Query Handlers]
        end
        
        subgraph "Domain Layer"
            ENT[Entities]
            VO[Value Objects]
            DOM_SVC[Domain Services]
            REPO[Repositories]
        end
    end

    WEB --> WEB_AD
    MOB --> WEB_AD
    IOT --> IOT_AD
    API --> API_AD
    
    WEB_AD --> HTTP_P
    IOT_AD --> MQTT_P
    API_AD --> HTTP_P
    
    HTTP_P --> APP_SVC
    MQTT_P --> APP_SVC
    MSG_P --> APP_SVC
    
    APP_SVC --> DOM_SVC
    APP_SVC --> ENT
    APP_SVC --> REPO
    
    REPO --> DB_P
    DB_P --> DB_AD
    DB_AD --> DB