
## 15. `generate_diagrams.py`
```python
#!/usr/bin/env python3
"""
Parking Management System Diagram Generator

This script generates UML diagrams for the Parking Management System
using PlantUML and Mermaid.js formats.
"""

import os
import subprocess
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class DiagramGenerator:
    """Main diagram generator class"""
    
    def __init__(self, output_dir: str = "diagrams"):
        self.output_dir = Path(output_dir)
        self.plantuml_dir = self.output_dir / "plantuml"
        self.mermaid_dir = self.output_dir / "mermaid"
        self.images_dir = self.output_dir / "images"
        
        # Create directories
        self.plantuml_dir.mkdir(parents=True, exist_ok=True)
        self.mermaid_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Diagram configurations
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load diagram configuration"""
        return {
            "colors": {
                "primary": "#3498db",
                "success": "#2ecc71",
                "warning": "#f39c12",
                "danger": "#e74c3c",
                "info": "#9b59b6",
                "light": "#ecf0f1",
                "dark": "#2c3e50"
            },
            "styles": {
                "class": {
                    "BackgroundColor": "White",
                    "BorderColor": "Black",
                    "ArrowColor": "#2E4053"
                },
                "component": {
                    "BackgroundColor": "White",
                    "BorderColor": "#2C3E50"
                }
            },
            "sizes": {
                "width": 1200,
                "height": 800
            }
        }
    
    def generate_all_diagrams(self):
        """Generate all diagrams"""
        print("Generating Parking Management System Diagrams...")
        print("=" * 50)
        
        diagrams = [
            ("class_diagram", self.generate_class_diagram),
            ("sequence_diagram", self.generate_sequence_diagram),
            ("use_case_diagram", self.generate_use_case_diagram),
            ("activity_diagram", self.generate_activity_diagram),
            ("component_diagram", self.generate_component_diagram),
            ("deployment_diagram", self.generate_deployment_diagram),
            ("state_diagram", self.generate_state_diagram),
            ("er_diagram", self.generate_er_diagram)
        ]
        
        for name, generator in diagrams:
            print(f"Generating {name.replace('_', ' ')}...")
            try:
                generator()
                print(f"  ✓ {name.replace('_', ' ')} generated successfully")
            except Exception as e:
                print(f"  ✗ Error generating {name}: {e}")
        
        print("\n" + "=" * 50)
        print("Diagram generation complete!")
        print(f"Output directory: {self.output_dir}")
    
    def generate_class_diagram(self):
        """Generate class diagram"""
        content = """@startuml
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
    
    class Admin {
        -adminId: String
        -username: String
        -permissions: List<String>
        +addSpot(): void
        +removeSpot(): void
        +modifyRates(): void
        +generateReport(): Report
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

@enduml"""
        
        self._save_plantuml("class_diagram.puml", content)
        self._generate_image("class_diagram.puml")
    
    def generate_sequence_diagram(self):
        """Generate sequence diagram"""
        content = """@startuml
title Vehicle Entry Process

participant "Customer" as Customer
participant "Entry Gate\nSystem" as EntryGate
participant "License Plate\nReader" as LPR
participant "Parking\nController" as ParkingCtrl
participant "Spot\nManager" as SpotManager
participant "Ticket\nPrinter" as TicketPrinter
participant "Payment\nService" as PaymentService
participant "Database" as DB

Customer -> EntryGate : Approach entry gate
EntryGate -> LPR : Capture license plate
LPR -> ParkingCtrl : Send plate number

alt Regular Entry
    ParkingCtrl -> DB : Check for reservation
    DB --> ParkingCtrl : Return reservation details
    
    ParkingCtrl -> SpotManager : Assign available spot
    SpotManager -> DB : Find optimal spot
    DB --> SpotManager : Return spot details
    SpotManager --> ParkingCtrl : Spot assigned
    
    ParkingCtrl -> TicketPrinter : Generate ticket
    TicketPrinter --> Customer : Issue ticket
    
    ParkingCtrl -> EntryGate : Open barrier
    EntryGate --> Customer : Barrier opens
    
else Pre-paid/Subscription Entry
    ParkingCtrl -> PaymentService : Validate subscription
    PaymentService -> DB : Check active subscription
    DB --> PaymentService : Subscription status
    PaymentService --> ParkingCtrl : Valid subscription
    
    ParkingCtrl -> SpotManager : Assign reserved spot
    SpotManager --> ParkingCtrl : Spot confirmed
    
    ParkingCtrl -> EntryGate : Open barrier
    EntryGate --> Customer : Barrier opens
end

ParkingCtrl -> DB : Log entry transaction
Customer -> EntryGate : Drive through
EntryGate -> ParkingCtrl : Vehicle entered
ParkingCtrl -> DB : Update spot status to OCCUPIED
@enduml"""
        
        self._save_plantuml("sequence_diagram.puml", content)
        self._generate_image("sequence_diagram.puml")
    
    def generate_use_case_diagram(self):
        """Generate use case diagram"""
        content = """@startuml
left to right direction

actor Customer as Customer
actor "Parking Attendant" as Attendant
actor "System Administrator" as Admin
actor "Maintenance Staff" as Maintenance

rectangle "Parking Management System" {
  (Enter Parking Lot) as UC1
  (Exit Parking Lot) as UC2
  (Find Available Parking Spot) as UC3
  (Reserve Parking Spot) as UC4
  (Make Payment) as UC5
  (View Parking History) as UC6
  (Generate Parking Ticket) as UC7
  (Validate Ticket) as UC8
  (Manage Parking Rates) as UC9
  (Monitor Parking Occupancy) as UC10
  (Generate Reports) as UC11
  (Manage User Accounts) as UC12
  (Handle Maintenance Requests) as UC13
}

Customer --> UC1
Customer --> UC2
Customer --> UC3
Customer --> UC4
Customer --> UC5
Customer --> UC6

Attendant --> UC7
Attendant --> UC8
Attendant --> UC5

Admin --> UC9
Admin --> UC10
Admin --> UC11
Admin --> UC12

Maintenance --> UC13

UC1 ..> UC7 : includes
UC2 ..> UC5 : includes
UC2 ..> UC8 : includes
UC4 ..> UC5 : includes

@enduml"""
        
        self._save_plantuml("use_case_diagram.puml", content)
        self._generate_image("use_case_diagram.puml")
    
    def generate_activity_diagram(self):
        """Generate activity diagram"""
        content = """@startuml
title Complete Parking Process Flow

start
:Customer arrives at parking lot;

if (Has reservation?) then (yes)
  :Scan reservation QR code;
  :Validate reservation;
else (no)
  :Walk-in customer;
endif

:Check spot availability;
if (Spots available?) then (yes)
  :Assign parking spot;
  :Generate parking ticket;
  :Open entry barrier;
  :Customer parks vehicle;
  
  :Customer prepares to exit;
  :Scan ticket at exit;
  :Calculate parking charges;
  :Display amount due;
  :Process payment;
  
  if (Payment successful?) then (yes)
    :Generate receipt;
    :Open exit barrier;
    :Update spot status;
    :Log transaction;
    stop
  else (no)
    :Show payment error;
    :Retry payment;
  endif
else (no)
  :Display "LOT FULL" message;
  stop
endif
@enduml"""
        
        self._save_plantuml("activity_diagram.puml", content)
        self._generate_image("activity_diagram.puml")
    
    def generate_component_diagram(self):
        """Generate component diagram"""
        content = """@startuml
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
    [Database] as DB
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

PMS --> DB : CRUD Operations
Payment --> DB : Store Transactions
Auth --> DB : User Data

Payment --> PG : Process Payment
Notification --> SMS : Send SMS
Notification --> Email : Send Email

note right of UI
    Web Portal
    Mobile App
    Kiosk Interface
end note

@enduml"""
        
        self._save_plantuml("component_diagram.puml", content)
        self._generate_image("component_diagram.puml")
    
    def generate_deployment_diagram(self):
        """Generate deployment diagram"""
        content = """@startuml
skinparam node {
    backgroundColor White
    borderColor #34495E
    fontColor Black
}

cloud "AWS Cloud" {
    node "Public Subnet" {
        [Load Balancer\nAWS ELB] as LB
        [API Gateway\nAWS API Gateway] as APIGW
        
        folder "Security Group" {
            node "Private Subnet" {
                [Auth Service\nDocker Container] as AUTH
                [Parking Service\nDocker Container] as PARK
                [Payment Service\nDocker Container] as PAY
            }
        }
        
        node "Data Layer" {
            database "Main Database\nAmazon RDS" as RDS {
                [PostgreSQL] as PG
            }
            
            database "Cache\nAmazon ElastiCache" as CACHE {
                [Redis Cluster] as REDIS
            }
            
            storage "File Storage\nAmazon S3" as S3
        }
    }
    
    node "Monitoring" {
        [CloudWatch] as CW
    }
}

' Internet connections
[Internet] --> LB : HTTPS (443)
LB --> APIGW : HTTP

' Internal connections
APIGW --> AUTH : gRPC
APIGW --> PARK : REST
APIGW --> PAY : REST

' Service to data layer
AUTH --> PG : SQL
PARK --> PG : SQL
PAY --> PG : SQL

PARK --> REDIS : Cache
PAY --> REDIS : Session

' Monitoring
CW --> PG : Metrics
CW --> REDIS : Cache Metrics

' External services
PAY --> [Payment Gateway\nStripe/PayPal] : HTTPS
@enduml"""
        
        self._save_plantuml("deployment_diagram.puml", content)
        self._generate_image("deployment_diagram.puml")
    
    def generate_state_diagram(self):
        """Generate state machine diagram"""
        content = """@startuml
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

@enduml"""
        
        self._save_plantuml("state_diagram.puml", content)
        self._generate_image("state_diagram.puml")
    
    def generate_er_diagram(self):
        """Generate entity-relationship diagram"""
        content = """@startuml
!pragma layout smetana

title "Parking Management System - ER Diagram"

entity "Customer" as customer {
  * customer_id : UUID <<PK>>
  --
  first_name : VARCHAR(50)
  last_name : VARCHAR(50)
  email : VARCHAR(100) <<UNIQUE>>
  phone : VARCHAR(20)
  registration_date : TIMESTAMP
  status : VARCHAR(20)
}

entity "Vehicle" as vehicle {
  * vehicle_id : UUID <<PK>>
  * customer_id : UUID <<FK>>
  --
  license_plate : VARCHAR(20) <<UNIQUE>>
  make : VARCHAR(50)
  model : VARCHAR(50)
  vehicle_type : VARCHAR(20)
}

entity "ParkingSpot" as spot {
  * spot_id : UUID <<PK>>
  * lot_id : UUID <<FK>>
  --
  spot_number : VARCHAR(10)
  spot_type : VARCHAR(20)
  rate_per_hour : DECIMAL(8,2)
  status : VARCHAR(20)
}

entity "Reservation" as reservation {
  * reservation_id : UUID <<PK>>
  * customer_id : UUID <<FK>>
  * spot_id : UUID <<FK>>
  * vehicle_id : UUID <<FK>>
  --
  start_time : TIMESTAMP
  end_time : TIMESTAMP
  status : VARCHAR(20)
  amount : DECIMAL(10,2)
}

entity "ParkingTicket" as ticket {
  * ticket_id : UUID <<PK>>
  * customer_id : UUID <<FK>>
  * vehicle_id : UUID <<FK>>
  * spot_id : UUID <<FK>>
  --
  entry_time : TIMESTAMP
  exit_time : TIMESTAMP
  total_amount : DECIMAL(10,2)
  status : VARCHAR(20)
}

entity "Payment" as payment {
  * payment_id : UUID <<PK>>
  * customer_id : UUID <<FK>>
  * ticket_id : UUID <<FK>>
  --
  amount : DECIMAL(10,2)
  payment_method : VARCHAR(30)
  status : VARCHAR(20)
  payment_date : TIMESTAMP
}

' Relationships
customer ||--o{ vehicle : "owns"
customer ||--o{ reservation : "makes"
customer ||--o{ ticket : "receives"
customer ||--o{ payment : "makes"

spot ||--o{ reservation : "reserved for"
spot ||--o{ ticket : "used for"

vehicle ||--o{ reservation : "used for"
vehicle ||--o{ ticket : "parked with"

ticket ||--o{ payment : "paid by"

@enduml"""
        
        self._save_plantuml("er_diagram.puml", content)
        self._generate_image("er_diagram.puml")
    
    def generate_mermaid_diagrams(self):
        """Generate Mermaid.js diagrams"""
        mermaid_diagrams = {
            "class_diagram.md": """```mermaid
classDiagram
    class ParkingSystem {
        -String systemId
        -String name
        -Integer totalSpots
        -Integer availableSpots
        +Boolean checkAvailability()
        +Boolean reserveSpot()
        +Double calculateFee()
        +Ticket generateTicket()
    }

    class ParkingSpot {
        -String spotId
        -SpotType type
        -SpotStatus status
        -String location
        -Double ratePerHour
        +Boolean isAvailable()
        +Boolean reserve()
        +void release()
    }

    class Vehicle {
        -String vehicleId
        -String licensePlate
        -VehicleType type
        -Customer owner
        +void enterParking()
        +void exitParking()
    }

    class Customer {
        -String customerId
        -String name
        -String email
        -String phone
        -List~PaymentMethod~ paymentMethods
        +void register()
        +Boolean login()
        +Boolean makePayment()
    }

    ParkingSystem "1" *-- "many" ParkingSpot : contains
    ParkingSystem "1" --> "many" Ticket : generates
    Vehicle "1" --> "1" Customer : owned by
    Ticket "1" --> "1" Vehicle : for
    Ticket "1" --> "1" ParkingSpot : assigned to
```""",
            
            "sequence_diagram.md": """```mermaid
sequenceDiagram
    participant C as Customer
    participant MA as Mobile App
    participant PS as Parking Service
    participant SM as Spot Manager
    participant PM as Pricing Module
    participant PP as Payment Processor
    participant DB as Database

    C->>MA: Open parking app
    MA->>PS: Request available spots
    PS->>SM: Get availability
    SM->>DB: Query available spots
    DB-->>SM: Return spot data
    SM-->>PS: Return spot list
    PS-->>MA: Display available spots
    
    C->>MA: Select spot and time
    MA->>PS: Make reservation request
    PS->>PM: Calculate price
    PM->>DB: Get current rates
    DB-->>PM: Return rate data
    PM-->>PS: Return calculated price
    
    PS->>PP: Process payment
    PP->>DB: Verify payment method
    DB-->>PP: Payment method valid
    PP->>External: Process transaction
    External-->>PP: Transaction successful
    PP-->>PS: Payment confirmed
    
    PS->>SM: Reserve selected spot
    SM->>DB: Update spot status
    DB-->>SM: Status updated
    SM-->>PS: Reservation confirmed
    
    PS-->>MA: Reservation successful
    MA-->>C: Show confirmation details
```""",
            
            "flowchart_diagram.md": """```mermaid
flowchart TD
    Start([Customer arrives]) --> A[Check for reservation]
    
    A --> B{Has reservation?}
    B -->|Yes| C[Validate reservation]
    B -->|No| D[Find available spot]
    
    C --> E{Valid?}
    E -->|Yes| F[Assign reserved spot]
    E -->|No| D
    
    D --> G{Spot available?}
    G -->|Yes| H[Assign spot]
    G -->|No| I[Display LOT FULL]
    
    H --> J[Generate ticket]
    J --> K[Open barrier]
    K --> L[Vehicle enters]
    
    L --> M[Monitor duration]
    M --> N{Time to exit?}
    N -->|Yes| O[Process exit]
    N -->|No| M
    
    O --> P[Calculate charges]
    P --> Q[Process payment]
    Q --> R{Payment successful?}
    R -->|Yes| S[Open exit barrier]
    R -->|No| T[Retry payment]
    
    S --> U[Vehicle exits]
    U --> V[Update spot status]
    V --> End([Process complete])
```"""
        }
        
        for filename, content in mermaid_diagrams.items():
            filepath = self.mermaid_dir / filename
            filepath.write_text(content)
            print(f"  ✓ Generated {filename}")
    
    def _save_plantuml(self, filename: str, content: str):
        """Save PlantUML content to file"""
        filepath = self.plantuml_dir / filename
        filepath.write_text(content)
    
    def _generate_image(self, puml_file: str):
        """Generate image from PlantUML file"""
        input_file = self.plantuml_dir / puml_file
        output_file = self.images_dir / f"{Path(puml_file).stem}.png"
        
        # Check if PlantUML is installed
        try:
            subprocess.run(["plantuml", "-version"], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"  ⚠ PlantUML not installed. Install with: sudo apt install plantuml")
            return
        
        # Generate image
        try:
            subprocess.run([
                "plantuml", 
                "-tpng", 
                f"-o{self.images_dir.absolute()}",
                str(input_file.absolute())
            ], check=True)
            print(f"  ✓ Generated image: {output_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Error generating image: {e}")
    
    def generate_report(self):
        """Generate diagram generation report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "diagrams": {
                "plantuml": list(self.plantuml_dir.glob("*.puml")),
                "mermaid": list(self.mermaid_dir.glob("*.md")),
                "images": list(self.images_dir.glob("*.png"))
            },
            "statistics": {
                "total_diagrams": len(list(self.plantuml_dir.glob("*.puml"))) +
                                 len(list(self.mermaid_dir.glob("*.md")))
            }
        }
        
        report_file = self.output_dir / "generation_report.json"
        report_file.write_text(json.dumps(report, indent=2))
        
        # Print summary
        print("\n" + "=" * 50)
        print("DIAGRAM GENERATION SUMMARY")
        print("=" * 50)
        print(f"PlantUML diagrams: {len(report['diagrams']['plantuml'])}")
        print(f"Mermaid diagrams: {len(report['diagrams']['mermaid'])}")
        print(f"Generated images: {len(report['diagrams']['images'])}")
        print(f"Total diagrams: {report['statistics']['total_diagrams']}")
        print(f"Report saved to: {report_file}")

def main():
    """Main function"""
    generator = DiagramGenerator()
    
    # Generate all diagrams
    generator.generate_all_diagrams()
    
    # Generate Mermaid diagrams
    print("\nGenerating Mermaid diagrams...")
    generator.generate_mermaid_diagrams()
    
    # Generate report
    generator.generate_report()

if __name__ == "__main__":
    main()