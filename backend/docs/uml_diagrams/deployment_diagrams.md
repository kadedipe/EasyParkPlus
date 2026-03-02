
## 3. `deployment_diagrams.md`
```markdown
# Deployment Diagrams - Parking Management System

## Cloud Deployment Architecture

```plantuml
@startuml
skinparam node {
    backgroundColor White
    borderColor #34495E
    fontColor Black
}

cloud "AWS Cloud" {
    node "Public Subnet" {
        [Load Balancer\nAWS ELB] as LB
        [API Gateway\nAWS API Gateway] as APIGW
        [Web Server\nEC2 Instance] as WEB
        
        folder "Security Group" {
            node "Private Subnet" {
                [Auth Service\nDocker Container] as AUTH
                [Parking Service\nDocker Container] as PARK
                [Payment Service\nDocker Container] as PAY
                [Notification Service\nDocker Container] as NOTIFY
            }
        }
        
        node "Data Layer" {
            database "Main Database\nAmazon RDS" as RDS {
                [PostgreSQL] as PG
                [Read Replicas] as RR
            }
            
            database "Cache\nAmazon ElastiCache" as CACHE {
                [Redis Cluster] as REDIS
            }
            
            queue "Message Queue\nAmazon SQS/SNS" as MQ {
                [SQS Queue] as SQS
                [SNS Topic] as SNS
            }
            
            storage "File Storage\nAmazon S3" as S3 {
                [Reports Bucket] as REPORTS
                [Logs Bucket] as LOGS
            }
        }
    }
    
    node "Monitoring" {
        [CloudWatch] as CW
        [X-Ray] as XRAY
        [CloudTrail] as CT
    }
}

' Internet connections
[Internet] --> LB : HTTPS (443)
LB --> APIGW : HTTP
APIGW --> WEB : HTTP

' Internal connections
WEB --> AUTH : gRPC
WEB --> PARK : REST
WEB --> PAY : REST
WEB --> NOTIFY : REST

' Service to data layer
AUTH --> PG : SQL
PARK --> PG : SQL
PAY --> PG : SQL

PARK --> REDIS : Cache
PAY --> REDIS : Session

NOTIFY --> SQS : Messages
PARK --> SNS : Events

' Monitoring
CW --> PG : Metrics
CW --> REDIS : Cache Metrics
XRAY --> WEB : Tracing
CT --> ALL : Logging

' External services
PAY --> [Payment Gateway\nStripe/PayPal] : HTTPS
NOTIFY --> [Email Service\nAmazon SES] : SMTP
NOTIFY --> [SMS Service\nAmazon SNS] : SMS

@enduml