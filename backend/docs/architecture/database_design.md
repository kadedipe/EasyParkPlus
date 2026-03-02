
## 6. **database_design.md** - Database Design

```markdown
# Database Design

## Overview

This document details the database architecture, schema design, optimization strategies, and data management practices for the Parking Management System. The system uses PostgreSQL as the primary database with specialized extensions for time-series data, geospatial queries, and full-text search.

## Database Architecture

### Multi-Database Strategy

```mermaid
graph TB
    subgraph "Primary Database"
        PG[(PostgreSQL 14+)]
        TS[(TimescaleDB)]
        GIS[(PostGIS)]
    end
    
    subgraph "Specialized Databases"
        ES[(Elasticsearch)]
        REDIS[(Redis)]
        S3[(AWS S3)]
    end
    
    subgraph "Message Queue"
        KAFKA[(Apache Kafka)]
    end
    
    subgraph "Microservices"
        PS[Parking Service]
        PAY[Payment Service]
        CUST[Customer Service]
        NOTIF[Notification Service]
        ANALYTICS[Analytics Service]
    end
    
    PS --> PG
    PS --> REDIS
    PAY --> PG
    CUST --> PG
    NOTIF --> REDIS
    ANALYTICS --> TS
    ANALYTICS --> ES
    
    PS --> KAFKA
    PAY --> KAFKA
    CUST --> KAFKA
    
    KAFKA --> TS
    KAFKA --> ES
    
    PG --> S3