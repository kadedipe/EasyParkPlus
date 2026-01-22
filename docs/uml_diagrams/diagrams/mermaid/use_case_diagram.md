# Parking System Use Cases

## Overall System
```mermaid

[graph TD
    subgraph "Parking Management System"
        direction LR
        
        %% Actors
        Customer["🚗 Customer"]
        Attendant["👷 Parking Attendant"]
        Admin["👔 System Administrator"]
        Manager["📊 Parking Manager"]
        System["🤖 System"]
        PaymentGateway["💳 Payment Gateway"]
        Vehicle["🚘 Vehicle System"]
        
        %% Customer Use Cases
        subgraph "Customer Actions"
            UC1["📱 Register/Login"]
            UC2["🔍 Search Parking"]
            UC3["📅 Book Parking Slot"]
            UC4["📲 Check-in/Check-out"]
            UC5["💳 Make Payment"]
            UC6["📝 View History"]
            UC7["🔄 Extend Parking"]
            UC8["🚫 Cancel Booking"]
            UC9["📊 View Receipt"]
            UC10["⚙️ Manage Profile"]
        end
        
        %% Attendant Use Cases
        subgraph "Parking Attendant Actions"
            UC11["👀 Monitor Slots"]
            UC12["🤝 Assist Customers"]
            UC13["📋 Manual Check-in"]
            UC14["📄 Manual Check-out"]
            UC15["⚠️ Handle Issues"]
            UC16["🔧 Report Maintenance"]
        end
        
        %% Administrator Use Cases
        subgraph "Administrator Actions"
            UC17["👥 Manage Users"]
            UC18["⚙️ Configure System"]
            UC19["📊 View Reports"]
            UC20["🔐 Manage Permissions"]
            UC21["💾 Backup/Restore"]
            UC22["📈 Monitor Performance"]
        end
        
        %% Manager Use Cases
        subgraph "Parking Manager Actions"
            UC23["💰 Set Pricing"]
            UC24["📅 Manage Schedules"]
            UC25["🚧 Manage Maintenance"]
            UC26["📊 Analyze Revenue"]
            UC27["🎯 Set Targets"]
            UC28["📋 Manage Staff"]
        end
        
        %% System Use Cases
        subgraph "System Actions"
            UC29["🤖 Automatic Billing"]
            UC30["📢 Send Notifications"]
            UC31["📝 Generate Reports"]
            UC32["🔒 Security Monitoring"]
            UC33["🔄 Data Sync"]
            UC34["⚙️ System Maintenance"]
        end
        
        %% External System Interactions
        subgraph "External Interactions"
            UC35["💳 Process Payment"]
            UC36["📱 Send SMS"]
            UC37["📧 Send Email"]
            UC38["🚗 Vehicle Recognition"]
            UC39["📡 Sensor Integration"]
        end
        
        %% Relationships
        Customer --> UC1
        Customer --> UC2
        Customer --> UC3
        Customer --> UC4
        Customer --> UC5
        Customer --> UC6
        Customer --> UC7
        Customer --> UC8
        Customer --> UC9
        Customer --> UC10
        
        Attendant --> UC11
        Attendant --> UC12
        Attendant --> UC13
        Attendant --> UC14
        Attendant --> UC15
        Attendant --> UC16
        
        Admin --> UC17
        Admin --> UC18
        Admin --> UC19
        Admin --> UC20
        Admin --> UC21
        Admin --> UC22
        
        Manager --> UC23
        Manager --> UC24
        Manager --> UC25
        Manager --> UC26
        Manager --> UC27
        Manager --> UC28
        
        System --> UC29
        System --> UC30
        System --> UC31
        System --> UC32
        System --> UC33
        System --> UC34
        
        UC5 --> UC35
        UC30 --> UC36
        UC30 --> UC37
        UC4 --> UC38
        UC11 --> UC39
    end
    
    style Customer fill:#4CAF50,color:#fff
    style Attendant fill:#2196F3,color:#fff
    style Admin fill:#FF9800,color:#fff
    style Manager fill:#9C27B0,color:#fff
    style System fill:#607D8B,color:#fff
    style PaymentGateway fill:#FF5722,color:#fff
    style Vehicle fill:#795548,color:#fff
    
    style UC1 fill:#E8F5E9
    style UC2 fill:#E8F5E9
    style UC3 fill:#E8F5E9
    style UC4 fill:#E8F5E9
    style UC5 fill:#E8F5E9
    style UC6 fill:#E8F5E9
    style UC7 fill:#E8F5E9
    style UC8 fill:#E8F5E9
    style UC9 fill:#E8F5E9
    style UC10 fill:#E8F5E9
    
    style UC11 fill:#E3F2FD
    style UC12 fill:#E3F2FD
    style UC13 fill:#E3F2FD
    style UC14 fill:#E3F2FD
    style UC15 fill:#E3F2FD
    style UC16 fill:#E3F2FD
    
    style UC17 fill:#FFF3E0
    style UC18 fill:#FFF3E0
    style UC19 fill:#FFF3E0
    style UC20 fill:#FFF3E0
    style UC21 fill:#FFF3E0
    style UC22 fill:#FFF3E0
    
    style UC23 fill:#F3E5F5
    style UC24 fill:#F3E5F5
    style UC25 fill:#F3E5F5
    style UC26 fill:#F3E5F5
    style UC27 fill:#F3E5F5
    style UC28 fill:#F3E5F5
    
    style UC29 fill:#E0F7FA
    style UC30 fill:#E0F7FA
    style UC31 fill:#E0F7FA
    style UC32 fill:#E0F7FA
    style UC33 fill:#E0F7FA
    style UC34 fill:#E0F7FA
    
    style UC35 fill:#FFEBEE
    style UC36 fill:#FFEBEE
    style UC37 fill:#FFEBEE
    style UC38 fill:#FFEBEE
    style UC39 fill:#FFEBEE]

## Customer Use Case Diagram

[graph TD
    subgraph "Customer Use Cases"
        direction TB
        
        Customer["🚗 Customer"]
        
        subgraph "Registration & Authentication"
            UC1["Register New Account"]
            UC2["Login to System"]
            UC3["Reset Password"]
            UC4["Verify Email"]
            UC5["Update Profile"]
        end
        
        subgraph "Parking Operations"
            UC6["Search Available Slots"]
            UC7["View Slot Details"]
            UC8["Book Parking Slot"]
            UC9["Check-in to Parking"]
            UC10["Check-out from Parking"]
            UC11["Extend Parking Duration"]
            UC12["Cancel Booking"]
        end
        
        subgraph "Payment & Billing"
            UC13["View Pricing"]
            UC14["Make Payment"]
            UC15["View Payment History"]
            UC16["Download Receipt"]
            UC17["Add Payment Method"]
            UC18["Apply Discount Code"]
        end
        
        subgraph "Notifications & Support"
            UC19["Receive Notifications"]
            UC20["View Booking History"]
            UC21["Contact Support"]
            UC22["Submit Feedback"]
            UC23["Report Issues"]
        end
        
        subgraph "Vehicle Management"
            UC24["Add Vehicle"]
            UC25["Update Vehicle Details"]
            UC26["Remove Vehicle"]
            UC27["Set Default Vehicle"]
        end
        
        %% Extends relationships
        UC8 -.->|extends| UC6
        UC9 -.->|extends| UC8
        UC10 -.->|extends| UC9
        UC11 -.->|extends| UC9
        UC14 -.->|requires| UC8
        UC16 -.->|extends| UC14
        
        %% Includes relationships
        UC6 -->|includes| UC7
        UC8 -->|includes| UC14
        UC9 -->|includes| UC19
        UC10 -->|includes| UC19
        UC14 -->|includes| UC16
        
        %% Customer to Use Cases
        Customer --> UC1
        Customer --> UC2
        Customer --> UC6
        Customer --> UC8
        Customer --> UC9
        Customer --> UC10
        Customer --> UC11
        Customer --> UC12
        Customer --> UC13
        Customer --> UC14
        Customer --> UC19
        Customer --> UC20
        Customer --> UC21
        Customer --> UC24
    end
    
    %% Style definitions
    style Customer fill:#4CAF50,color:#fff,stroke:#388E3C,stroke-width:2px
    
    style UC1 fill:#E8F5E9,stroke:#81C784
    style UC2 fill:#E8F5E9,stroke:#81C784
    style UC3 fill:#E8F5E9,stroke:#81C784
    style UC4 fill:#E8F5E9,stroke:#81C784
    style UC5 fill:#E8F5E9,stroke:#81C784
    
    style UC6 fill:#C8E6C9,stroke:#4CAF50
    style UC7 fill:#C8E6C9,stroke:#4CAF50
    style UC8 fill:#C8E6C9,stroke:#4CAF50
    style UC9 fill:#C8E6C9,stroke:#4CAF50
    style UC10 fill:#C8E6C9,stroke:#4CAF50
    style UC11 fill:#C8E6C9,stroke:#4CAF50
    style UC12 fill:#C8E6C9,stroke:#4CAF50
    
    style UC13 fill:#DCEDC8,stroke:#8BC34A
    style UC14 fill:#DCEDC8,stroke:#8BC34A
    style UC15 fill:#DCEDC8,stroke:#8BC34A
    style UC16 fill:#DCEDC8,stroke:#8BC34A
    style UC17 fill:#DCEDC8,stroke:#8BC34A
    style UC18 fill:#DCEDC8,stroke:#8BC34A
    
    style UC19 fill:#F1F8E9,stroke:#CDDC39
    style UC20 fill:#F1F8E9,stroke:#CDDC39
    style UC21 fill:#F1F8E9,stroke:#CDDC39
    style UC22 fill:#F1F8E9,stroke:#CDDC39
    style UC23 fill:#F1F8E9,stroke:#CDDC39
    
    style UC24 fill:#E8F5E9,stroke:#81C784
    style UC25 fill:#E8F5E9,stroke:#81C784
    style UC26 fill:#E8F5E9,stroke:#81C784
    style UC27 fill:#E8F5E9,stroke:#81C784
    
    %% Legend
    subgraph "Legend"
        L1["Include Relationship<br/>Use case A includes use case B"]
        L2["Extend Relationship<br/>Use case A extends use case B"]
        L3["Requires Relationship<br/>Use case A requires use case B"]
    end
    
    style L1 fill:#f9f9f9,stroke:#ddd
    style L2 fill:#f9f9f9,stroke:#ddd
    style L3 fill:#f9f9f9,stroke:#ddd]

## Parking Slot Management Use Case Diagram

[graph TD
    subgraph "Parking Slot Management"
        direction LR
        
        %% Actors
        Admin["👔 System Administrator"]
        Manager["📊 Parking Manager"]
        System["🤖 System"]
        Sensor["📡 IoT Sensors"]
        
        subgraph "Slot Configuration"
            UC1["Define Slot Types"]
            UC2["Configure Slot Rates"]
            UC3["Set Slot Restrictions"]
            UC4["Assign Slot Numbers"]
            UC5["Configure Zone Mapping"]
            UC6["Set Capacity Limits"]
        end
        
        subgraph "Slot Monitoring"
            UC7["Monitor Real-time Status"]
            UC8["View Occupancy Rates"]
            UC9["Track Slot Utilization"]
            UC10["Generate Slot Reports"]
            UC11["Set Status Alerts"]
            UC12["View Historical Data"]
        end
        
        subgraph "Maintenance Management"
            UC13["Schedule Maintenance"]
            UC14["Record Maintenance Issues"]
            UC15["Update Maintenance Status"]
            UC16["Track Maintenance History"]
            UC17["Assign Maintenance Tasks"]
            UC18["Verify Maintenance Completion"]
        end
        
        subgraph "Reservation Management"
            UC19["Manage Reservations"]
            UC20["Handle Walk-ins"]
            UC21["Process Early Check-outs"]
            UC22["Handle Overstays"]
            UC23["Manage Waitlist"]
            UC24["Process Cancellations"]
        end
        
        subgraph "Automated Operations"
            UC25["Auto-detect Availability"]
            UC26["Auto-assign Best Slot"]
            UC27["Auto-calculate Fees"]
            UC28["Auto-update Status"]
            UC29["Auto-generate Alerts"]
            UC30["Auto-sync with Sensors"]
        end
        
        %% Relationships
        Admin --> UC1
        Admin --> UC2
        Admin --> UC3
        Admin --> UC4
        Admin --> UC5
        Admin --> UC6
        
        Manager --> UC7
        Manager --> UC8
        Manager --> UC9
        Manager --> UC10
        Manager --> UC11
        Manager --> UC12
        
        Manager --> UC13
        Manager --> UC14
        Manager --> UC15
        Manager --> UC16
        
        Manager --> UC19
        Manager --> UC20
        Manager --> UC21
        Manager --> UC22
        Manager --> UC23
        Manager --> UC24
        
        System --> UC25
        System --> UC26
        System --> UC27
        System --> UC28
        System --> UC29
        System --> UC30
        
        Sensor -.-> UC25
        Sensor -.-> UC28
        Sensor -.-> UC30
        
        %% Relationships between use cases
        UC7 -.->|extends| UC8
        UC8 -.->|extends| UC9
        UC9 -.->|extends| UC10
        UC13 -.->|extends| UC14
        UC14 -.->|extends| UC15
        UC15 -.->|extends| UC16
        UC25 -.->|includes| UC26
        UC26 -.->|includes| UC27
        UC28 -.->|triggers| UC29
    end
    
    %% Styles
    style Admin fill:#FF9800,color:#fff,stroke:#F57C00
    style Manager fill:#9C27B0,color:#fff,stroke:#7B1FA2
    style System fill:#607D8B,color:#fff,stroke:#455A64
    style Sensor fill:#795548,color:#fff,stroke:#5D4037
    
    style UC1 fill:#FFF3E0,stroke:#FFB74D
    style UC2 fill:#FFF3E0,stroke:#FFB74D
    style UC3 fill:#FFF3E0,stroke:#FFB74D
    style UC4 fill:#FFF3E0,stroke:#FFB74D
    style UC5 fill:#FFF3E0,stroke:#FFB74D
    style UC6 fill:#FFF3E0,stroke:#FFB74D
    
    style UC7 fill:#F3E5F5,stroke:#BA68C8
    style UC8 fill:#F3E5F5,stroke:#BA68C8
    style UC9 fill:#F3E5F5,stroke:#BA68C8
    style UC10 fill:#F3E5F5,stroke:#BA68C8
    style UC11 fill:#F3E5F5,stroke:#BA68C8
    style UC12 fill:#F3E5F5,stroke:#BA68C8
    
    style UC13 fill:#E1BEE7,stroke:#AB47BC
    style UC14 fill:#E1BEE7,stroke:#AB47BC
    style UC15 fill:#E1BEE7,stroke:#AB47BC
    style UC16 fill:#E1BEE7,stroke:#AB47BC
    style UC17 fill:#E1BEE7,stroke:#AB47BC
    style UC18 fill:#E1BEE7,stroke:#AB47BC
    
    style UC19 fill:#D1C4E9,stroke:#9575CD
    style UC20 fill:#D1C4E9,stroke:#9575CD
    style UC21 fill:#D1C4E9,stroke:#9575CD
    style UC22 fill:#D1C4E9,stroke:#9575CD
    style UC23 fill:#D1C4E9,stroke:#9575CD
    style UC24 fill:#D1C4E9,stroke:#9575CD
    
    style UC25 fill:#BBDEFB,stroke:#64B5F6
    style UC26 fill:#BBDEFB,stroke:#64B5F6
    style UC27 fill:#BBDEFB,stroke:#64B5F6
    style UC28 fill:#BBDEFB,stroke:#64B5F6
    style UC29 fill:#BBDEFB,stroke:#64B5F6
    style UC30 fill:#BBDEFB,stroke:#64B5F6]

## Payment & Billing Use Case Diagram

[graph TD
    subgraph "Payment & Billing Management"
        direction TB
        
        Customer["🚗 Customer"]
        Admin["👔 Administrator"]
        Manager["📊 Finance Manager"]
        System["🤖 System"]
        PaymentGateway["💳 Payment Gateway"]
        
        subgraph "Payment Processing"
            UC1["Process Credit Card Payment"]
            UC2["Process Digital Wallet Payment"]
            UC3["Process Cash Payment"]
            UC4["Validate Payment"]
            UC5["Authorize Payment"]
            UC6["Capture Payment"]
            UC7["Handle Payment Failure"]
            UC8["Process Refund"]
        end
        
        subgraph "Invoice Management"
            UC9["Generate Invoice"]
            UC10["Send Invoice"]
            UC11["View Invoice History"]
            UC12["Download Invoice"]
            UC13["Apply Discount to Invoice"]
            UC14["Handle Invoice Disputes"]
            UC15["Update Invoice Status"]
        end
        
        subgraph "Billing Configuration"
            UC16["Configure Pricing Rules"]
            UC17["Set Tax Rates"]
            UC18["Configure Billing Cycles"]
            UC19["Set Late Fees"]
            UC20["Configure Payment Methods"]
            UC21["Set Currency Settings"]
        end
        
        subgraph "Reporting & Analytics"
            UC22["Generate Revenue Reports"]
            UC23["View Payment Analytics"]
            UC24["Monitor Transaction Volume"]
            UC25["Identify Payment Trends"]
            UC26["Generate Tax Reports"]
            UC27["Export Financial Data"]
        end
        
        subgraph "Automated Billing"
            UC28["Auto-generate Invoices"]
            UC29["Auto-send Payment Reminders"]
            UC30["Auto-process Recurring Payments"]
            UC31["Auto-apply Late Fees"]
            UC32["Auto-reconcile Payments"]
            UC33["Auto-generate Receipts"]
        end
        
        %% Actor to Use Case relationships
        Customer --> UC1
        Customer --> UC2
        Customer --> UC11
        Customer --> UC12
        
        Admin --> UC16
        Admin --> UC17
        Admin --> UC18
        Admin --> UC19
        Admin --> UC20
        Admin --> UC21
        
        Manager --> UC22
        Manager --> UC23
        Manager --> UC24
        Manager --> UC25
        Manager --> UC26
        Manager --> UC27
        
        System --> UC28
        System --> UC29
        System --> UC30
        System --> UC31
        System --> UC32
        System --> UC33
        
        PaymentGateway --> UC4
        PaymentGateway --> UC5
        PaymentGateway --> UC6
        PaymentGateway --> UC7
        PaymentGateway --> UC8
        
        %% Use Case relationships
        UC1 -->|includes| UC4
        UC1 -->|includes| UC5
        UC1 -->|includes| UC6
        UC9 -->|extends| UC10
        UC10 -->|extends| UC11
        UC22 -->|includes| UC23
        UC22 -->|includes| UC24
        UC28 -->|triggers| UC29
        UC29 -->|triggers| UC30
        UC9 -.->|precedes| UC33
        
        %% Cross-boundary relationships
        UC1 -.->|uses| PaymentGateway
        UC2 -.->|uses| PaymentGateway
        UC8 -.->|uses| PaymentGateway
        UC28 -.->|triggers| UC1
        UC30 -.->|triggers| UC1
    end
    
    %% Styles
    style Customer fill:#4CAF50,color:#fff
    style Admin fill:#FF9800,color:#fff
    style Manager fill:#9C27B0,color:#fff
    style System fill:#607D8B,color:#fff
    style PaymentGateway fill:#FF5722,color:#fff
    
    style UC1 fill:#FFEBEE,stroke:#EF5350
    style UC2 fill:#FFEBEE,stroke:#EF5350
    style UC3 fill:#FFEBEE,stroke:#EF5350
    style UC4 fill:#FFEBEE,stroke:#EF5350
    style UC5 fill:#FFEBEE,stroke:#EF5350
    style UC6 fill:#FFEBEE,stroke:#EF5350
    style UC7 fill:#FFEBEE,stroke:#EF5350
    style UC8 fill:#FFEBEE,stroke:#EF5350
    
    style UC9 fill:#FCE4EC,stroke:#EC407A
    style UC10 fill:#FCE4EC,stroke:#EC407A
    style UC11 fill:#FCE4EC,stroke:#EC407A
    style UC12 fill:#FCE4EC,stroke:#EC407A
    style UC13 fill:#FCE4EC,stroke:#EC407A
    style UC14 fill:#FCE4EC,stroke:#EC407A
    style UC15 fill:#FCE4EC,stroke:#EC407A
    
    style UC16 fill:#F3E5F5,stroke:#AB47BC
    style UC17 fill:#F3E5F5,stroke:#AB47BC
    style UC18 fill:#F3E5F5,stroke:#AB47BC
    style UC19 fill:#F3E5F5,stroke:#AB47BC
    style UC20 fill:#F3E5F5,stroke:#AB47BC
    style UC21 fill:#F3E5F5,stroke:#AB47BC
    
    style UC22 fill:#E8EAF6,stroke:#5C6BC0
    style UC23 fill:#E8EAF6,stroke:#5C6BC0
    style UC24 fill:#E8EAF6,stroke:#5C6BC0
    style UC25 fill:#E8EAF6,stroke:#5C6BC0
    style UC26 fill:#E8EAF6,stroke:#5C6BC0
    style UC27 fill:#E8EAF6,stroke:#5C6BC0
    
    style UC28 fill:#E3F2FD,stroke:#42A5F5
    style UC29 fill:#E3F2FD,stroke:#42A5F5
    style UC30 fill:#E3F2FD,stroke:#42A5F5
    style UC31 fill:#E3F2FD,stroke:#42A5F5
    style UC32 fill:#E3F2FD,stroke:#42A5F5
    style UC33 fill:#E3F2FD,stroke:#42A5F5]

## Reporting & Analytics Use Case Diagram

[graph TD
    subgraph "Reporting & Analytics System"
        direction LR
        
        %% Actors
        Manager["📊 Parking Manager"]
        Admin["👔 System Administrator"]
        Finance["💰 Finance Team"]
        Operations["🏢 Operations Team"]
        System["🤖 System"]
        
        subgraph "Real-time Monitoring"
            UC1["View Live Occupancy"]
            UC2["Monitor Revenue Stream"]
            UC3["Track Active Bookings"]
            UC4["View Peak Hours"]
            UC5["Monitor System Health"]
            UC6["Receive Live Alerts"]
        end
        
        subgraph "Operational Reports"
            UC7["Generate Daily Report"]
            UC8["Generate Weekly Report"]
            UC9["Generate Monthly Report"]
            UC10["View Slot Utilization"]
            UC11["View Customer Trends"]
            UC12["View Revenue Analysis"]
        end
        
        subgraph "Financial Reports"
            UC13["Generate Income Statement"]
            UC14["View Revenue by Slot Type"]
            UC15["Analyze Payment Methods"]
            UC16["View Tax Reports"]
            UC17["Track Outstanding Payments"]
            UC18["View Profit Margins"]
        end
        
        subgraph "Analytics & Insights"
            UC19["Predict Future Demand"]
            UC20["Analyze Customer Behavior"]
            UC21["Identify Peak Periods"]
            UC22["Optimize Pricing Strategy"]
            UC23["Forecast Revenue"]
            UC24["Generate Business Insights"]
        end
        
        subgraph "Export & Distribution"
            UC25["Export to PDF"]
            UC26["Export to Excel"]
            UC27["Export to CSV"]
            UC28["Schedule Report Delivery"]
            UC29["Share Reports"]
            UC30["Archive Reports"]
        end
        
        subgraph "Automated Reporting"
            UC31["Auto-generate Reports"]
            UC32["Auto-send Reports"]
            UC33["Auto-archive Reports"]
            UC34["Auto-analyze Trends"]
            UC35["Auto-generate Alerts"]
            UC36["Auto-optimize Recommendations"]
        end
        
        %% Actor to Use Case relationships
        Manager --> UC1
        Manager --> UC2
        Manager --> UC7
        Manager --> UC8
        Manager --> UC9
        Manager --> UC19
        Manager --> UC20
        Manager --> UC21
        
        Admin --> UC5
        Admin --> UC6
        Admin --> UC30
        Admin --> UC33
        
        Finance --> UC13
        Finance --> UC14
        Finance --> UC15
        Finance --> UC16
        Finance --> UC17
        Finance --> UC18
        
        Operations --> UC3
        Operations --> UC4
        Operations --> UC10
        Operations --> UC11
        Operations --> UC12
        
        System --> UC31
        System --> UC32
        System --> UC33
        System --> UC34
        System --> UC35
        System --> UC36
        
        %% Use Case relationships
        UC7 -->|extends| UC8
        UC8 -->|extends| UC9
        UC13 -->|includes| UC14
        UC14 -->|includes| UC15
        UC19 -->|uses| UC20
        UC20 -->|uses| UC21
        UC25 -->|extends| UC26
        UC26 -->|extends| UC27
        UC31 -->|triggers| UC32
        UC32 -->|triggers| UC33
        UC34 -->|generates| UC35
        UC35 -->|generates| UC36
    end
    
    %% Styles
    style Manager fill:#9C27B0,color:#fff
    style Admin fill:#FF9800,color:#fff
    style Finance fill:#F44336,color:#fff
    style Operations fill:#2196F3,color:#fff
    style System fill:#607D8B,color:#fff
    
    style UC1 fill:#F3E5F5,stroke:#BA68C8
    style UC2 fill:#F3E5F5,stroke:#BA68C8
    style UC3 fill:#F3E5F5,stroke:#BA68C8
    style UC4 fill:#F3E5F5,stroke:#BA68C8
    style UC5 fill:#F3E5F5,stroke:#BA68C8
    style UC6 fill:#F3E5F5,stroke:#BA68C8
    
    style UC7 fill:#E1BEE7,stroke:#AB47BC
    style UC8 fill:#E1BEE7,stroke:#AB47BC
    style UC9 fill:#E1BEE7,stroke:#AB47BC
    style UC10 fill:#E1BEE7,stroke:#AB47BC
    style UC11 fill:#E1BEE7,stroke:#AB47BC
    style UC12 fill:#E1BEE7,stroke:#AB47BC
    
    style UC13 fill:#D1C4E9,stroke:#9575CD
    style UC14 fill:#D1C4E9,stroke:#9575CD
    style UC15 fill:#D1C4E9,stroke:#9575CD
    style UC16 fill:#D1C4E9,stroke:#9575CD
    style UC17 fill:#D1C4E9,stroke:#9575CD
    style UC18 fill:#D1C4E9,stroke:#9575CD
    
    style UC19 fill:#C5CAE9,stroke:#7986CB
    style UC20 fill:#C5CAE9,stroke:#7986CB
    style UC21 fill:#C5CAE9,stroke:#7986CB
    style UC22 fill:#C5CAE9,stroke:#7986CB
    style UC23 fill:#C5CAE9,stroke:#7986CB
    style UC24 fill:#C5CAE9,stroke:#7986CB
    
    style UC25 fill:#BBDEFB,stroke:#64B5F6
    style UC26 fill:#BBDEFB,stroke:#64B5F6
    style UC27 fill:#BBDEFB,stroke:#64B5F6
    style UC28 fill:#BBDEFB,stroke:#64B5F6
    style UC29 fill:#BBDEFB,stroke:#64B5F6
    style UC30 fill:#BBDEFB,stroke:#64B5F6
    
    style UC31 fill:#B3E5FC,stroke:#29B6F6
    style UC32 fill:#B3E5FC,stroke:#29B6F6
    style UC33 fill:#B3E5FC,stroke:#29B6F6
    style UC34 fill:#B3E5FC,stroke:#29B6F6
    style UC35 fill:#B3E5FC,stroke:#29B6F6
    style UC36 fill:#B3E5FC,stroke:#29B6F6]

## Maintenance & Support Use Case Diagram

[graph TD
    subgraph "Maintenance & Support System"
        direction TB
        
        %% Actors
        Technician["🔧 Maintenance Technician"]
        Attendant["👷 Parking Attendant"]
        Admin["👔 System Administrator"]
        Manager["📊 Facility Manager"]
        System["🤖 System"]
        
        subgraph "Maintenance Scheduling"
            UC1["Schedule Preventive Maintenance"]
            UC2["Create Maintenance Work Order"]
            UC3["Assign Maintenance Tasks"]
            UC4["Set Maintenance Priority"]
            UC5["Schedule Downtime"]
            UC6["Track Maintenance Schedule"]
        end
        
        subgraph "Issue Reporting & Tracking"
            UC7["Report Maintenance Issue"]
            UC8["Log Repair Request"]
            UC9["Track Issue Status"]
            UC10["Update Issue Resolution"]
            UC11["Close Maintenance Ticket"]
            UC12["Escalate Critical Issues"]
        end
        
        subgraph "Maintenance Execution"
            UC13["Perform Maintenance"]
            UC14["Record Maintenance Details"]
            UC15["Update Equipment Status"]
            UC16["Verify Maintenance Completion"]
            UC17["Document Maintenance Steps"]
            UC18["Test After Maintenance"]
        end
        
        subgraph "Inventory Management"
            UC19["Track Spare Parts"]
            UC20["Manage Inventory Levels"]
            UC21["Order Replacement Parts"]
            UC22["Track Part Usage"]
            UC23["Manage Supplier Information"]
            UC24["Audit Inventory"]
        end
        
        subgraph "Support & Communication"
            UC25["Provide Customer Support"]
            UC26["Handle Customer Complaints"]
            UC27["Communicate Downtime"]
            UC28["Send Maintenance Notifications"]
            UC29["Update Status Board"]
            UC30["Coordinate with Teams"]
        end
        
        subgraph "Analytics & Improvement"
            UC31["Analyze Maintenance History"]
            UC32["Identify Recurring Issues"]
            UC33["Optimize Maintenance Schedule"]
            UC34["Calculate Maintenance Costs"]
            UC35["Generate Maintenance Reports"]
            UC36["Plan Equipment Upgrades"]
        end
        
        %% Actor to Use Case relationships
        Technician --> UC13
        Technician --> UC14
        Technician --> UC15
        Technician --> UC16
        Technician --> UC17
        Technician --> UC18
        
        Attendant --> UC7
        Attendant --> UC8
        Attendant --> UC25
        Attendant --> UC26
        Attendant --> UC29
        
        Admin --> UC1
        Admin --> UC2
        Admin --> UC3
        Admin --> UC4
        Admin --> UC5
        Admin --> UC6
        
        Manager --> UC19
        Manager --> UC20
        Manager --> UC21
        Manager --> UC22
        Manager --> UC23
        Manager --> UC24
        
        System --> UC28
        System --> UC30
        System --> UC31
        System --> UC32
        System --> UC33
        System --> UC34
        System --> UC35
        System --> UC36
        
        %% Use Case relationships
        UC1 -->|includes| UC2
        UC2 -->|includes| UC3
        UC7 -->|triggers| UC8
        UC8 -->|triggers| UC9
        UC13 -->|includes| UC14
        UC14 -->|includes| UC15
        UC19 -->|extends| UC20
        UC20 -->|extends| UC21
        UC25 -->|includes| UC26
        UC31 -->|generates| UC32
        UC32 -->|generates| UC33
        UC34 -->|feeds into| UC35
        UC35 -->|feeds into| UC36
        
        %% Cross-relationships
        UC7 -.->|requires| UC28
        UC13 -.->|updates| UC15
        UC16 -.->|triggers| UC11
        UC28 -.->|notifies| UC27
    end
    
    %% Styles
    style Technician fill:#FF9800,color:#fff
    style Attendant fill:#2196F3,color:#fff
    style Admin fill:#FF5722,color:#fff
    style Manager fill:#9C27B0,color:#fff
    style System fill:#607D8B,color:#fff
    
    style UC1 fill:#FFF3E0,stroke:#FFB74D
    style UC2 fill:#FFF3E0,stroke:#FFB74D
    style UC3 fill:#FFF3E0,stroke:#FFB74D
    style UC4 fill:#FFF3E0,stroke:#FFB74D
    style UC5 fill:#FFF3E0,stroke:#FFB74D
    style UC6 fill:#FFF3E0,stroke:#FFB74D
    
    style UC7 fill:#E3F2FD,stroke:#90CAF9
    style UC8 fill:#E3F2FD,stroke:#90CAF9
    style UC9 fill:#E3F2FD,stroke:#90CAF9
    style UC10 fill:#E3F2FD,stroke:#90CAF9
    style UC11 fill:#E3F2FD,stroke:#90CAF9
    style UC12 fill:#E3F2FD,stroke:#90CAF9
    
    style UC13 fill:#C8E6C9,stroke:#81C784
    style UC14 fill:#C8E6C9,stroke:#81C784
    style UC15 fill:#C8E6C9,stroke:#81C784
    style UC16 fill:#C8E6C9,stroke:#81C784
    style UC17 fill:#C8E6C9,stroke:#81C784
    style UC18 fill:#C8E6C9,stroke:#81C784
    
    style UC19 fill:#F3E5F5,stroke:#CE93D8
    style UC20 fill:#F3E5F5,stroke:#CE93D8
    style UC21 fill:#F3E5F5,stroke:#CE93D8
    style UC22 fill:#F3E5F5,stroke:#CE93D8
    style UC23 fill:#F3E5F5,stroke:#CE93D8
    style UC24 fill:#F3E5F5,stroke:#CE93D8
    
    style UC25 fill:#E1F5FE,stroke:#4FC3F7
    style UC26 fill:#E1F5FE,stroke:#4FC3F7
    style UC27 fill:#E1F5FE,stroke:#4FC3F7
    style UC28 fill:#E1F5FE,stroke:#4FC3F7
    style UC29 fill:#E1F5FE,stroke:#4FC3F7
    style UC30 fill:#E1F5FE,stroke:#4FC3F7
    
    style UC31 fill:#F1F8E9,stroke:#AED581
    style UC32 fill:#F1F8E9,stroke:#AED581
    style UC33 fill:#F1F8E9,stroke:#AED581
    style UC34 fill:#F1F8E9,stroke:#AED581
    style UC35 fill:#F1F8E9,stroke:#AED581
    style UC36 fill:#F1F8E9,stroke:#AED581]

## System Integration Use Case Diagram

[graph TD
    subgraph "System Integration & External Services"
        direction LR
        
        %% External Systems
        PaymentGateway["💳 Payment Gateway"]
        SMSService["📱 SMS Service"]
        EmailService["📧 Email Service"]
        MapService["🗺️ Map Service"]
        VehicleRecognition["🚗 Vehicle Recognition"]
        SensorNetwork["📡 IoT Sensor Network"]
        AccountingSystem["📊 Accounting System"]
        CRM["👥 CRM System"]
        
        %% Internal Systems
        ParkingSystem["🏢 Parking Management System"]
        BillingSystem["💰 Billing System"]
        UserManagement["👤 User Management"]
        SlotManagement["🅿️ Slot Management"]
        NotificationSystem["🔔 Notification System"]
        ReportingSystem["📈 Reporting System"]
        
        subgraph "Payment Gateway Integration"
            UC1["Process Payment Transactions"]
            UC2["Handle Payment Refunds"]
            UC3["Validate Payment Cards"]
            UC4["Process Recurring Payments"]
            UC5["Handle Payment Webhooks"]
            UC6["Synchronize Payment Status"]
        end
        
        subgraph "Communication Services"
            UC7["Send SMS Notifications"]
            UC8["Send Email Notifications"]
            UC9["Send Push Notifications"]
            UC10["Handle Delivery Status"]
            UC11["Manage Templates"]
            UC12["Track Communication History"]
        end
        
        subgraph "Mapping & Navigation"
            UC13["Provide Location Services"]
            UC14["Generate Navigation Routes"]
            UC15["Display Real-time Traffic"]
            UC16["Find Nearest Parking"]
            UC17["Provide Street View"]
            UC18["Calculate ETA"]
        end
        
        subgraph "Vehicle Recognition"
            UC19["Capture License Plate"]
            UC20["Recognize Vehicle Type"]
            UC21["Validate Vehicle Entry"]
            UC22["Detect Vehicle Exit"]
            UC23["Identify Violations"]
            UC24["Update Vehicle Database"]
        end
        
        subgraph "IoT & Sensor Integration"
            UC25["Monitor Slot Occupancy"]
            UC26["Detect Vehicle Presence"]
            UC27["Control Barrier Gates"]
            UC28["Monitor Environmental Sensors"]
            UC29["Track Equipment Health"]
            UC30["Send Sensor Alerts"]
        end
        
        subgraph "Business System Integration"
            UC31["Sync with Accounting System"]
            UC32["Integrate with CRM"]
            UC33["Export to ERP System"]
            UC34["Connect to HR System"]
            UC35["Integrate with POS Systems"]
            UC36["Sync with Inventory System"]
        end
        
        %% System to Use Case relationships
        ParkingSystem --> UC1
        ParkingSystem --> UC2
        ParkingSystem --> UC7
        ParkingSystem --> UC8
        ParkingSystem --> UC13
        ParkingSystem --> UC14
        
        BillingSystem --> UC3
        BillingSystem --> UC4
        BillingSystem --> UC31
        
        UserManagement --> UC11
        UserManagement --> UC12
        UserManagement --> UC32
        
        SlotManagement --> UC19
        SlotManagement --> UC20
        SlotManagement --> UC25
        SlotManagement --> UC26
        
        NotificationSystem --> UC9
        NotificationSystem --> UC10
        
        ReportingSystem --> UC33
        ReportingSystem --> UC34
        
        %% External System to Use Case relationships
        PaymentGateway --> UC5
        PaymentGateway --> UC6
        
        SMSService --> UC7
        EmailService --> UC8
        
        MapService --> UC15
        MapService --> UC16
        MapService --> UC17
        MapService --> UC18
        
        VehicleRecognition --> UC21
        VehicleRecognition --> UC22
        VehicleRecognition --> UC23
        
        SensorNetwork --> UC27
        SensorNetwork --> UC28
        SensorNetwork --> UC29
        SensorNetwork --> UC30
        
        AccountingSystem --> UC31
        CRM --> UC32
    end
    
    %% Styles
    style PaymentGateway fill:#FF5722,color:#fff,stroke:#D84315
    style SMSService fill:#2196F3,color:#fff,stroke:#1565C0
    style EmailService fill:#4CAF50,color:#fff,stroke:#388E3C
    style MapService fill:#FF9800,color:#fff,stroke:#EF6C00
    style VehicleRecognition fill:#795548,color:#fff,stroke:#5D4037
    style SensorNetwork fill:#607D8B,color:#fff,stroke:#455A64
    style AccountingSystem fill:#9C27B0,color:#fff,stroke:#7B1FA2
    style CRM fill:#00BCD4,color:#fff,stroke:#0097A7
    
    style ParkingSystem fill:#3F51B5,color:#fff,stroke:#303F9F
    style BillingSystem fill:#E91E63,color:#fff,stroke:#C2185B
    style UserManagement fill:#009688,color:#fff,stroke:#00796B
    style SlotManagement fill:#FFC107,color:#000,stroke:#FFA000
    style NotificationSystem fill:#8BC34A,color:#fff,stroke:#689F38
    style ReportingSystem fill:#FF9800,color:#fff,stroke:#F57C00
    
    style UC1 fill:#FFEBEE,stroke:#EF5350
    style UC2 fill:#FFEBEE,stroke:#EF5350
    style UC3 fill:#FFEBEE,stroke:#EF5350
    style UC4 fill:#FFEBEE,stroke:#EF5350
    style UC5 fill:#FFEBEE,stroke:#EF5350
    style UC6 fill:#FFEBEE,stroke:#EF5350
    
    style UC7 fill:#E3F2FD,stroke:#90CAF9
    style UC8 fill:#E3F2FD,stroke:#90CAF9
    style UC9 fill:#E3F2FD,stroke:#90CAF9
    style UC10 fill:#E3F2FD,stroke:#90CAF9
    style UC11 fill:#E3F2FD,stroke:#90CAF9
    style UC12 fill:#E3F2FD,stroke:#90CAF9
    
    style UC13 fill:#FFF3E0,stroke:#FFCC80
    style UC14 fill:#FFF3E0,stroke:#FFCC80
    style UC15 fill:#FFF3E0,stroke:#FFCC80
    style UC16 fill:#FFF3E0,stroke:#FFCC80
    style UC17 fill:#FFF3E0,stroke:#FFCC80
    style UC18 fill:#FFF3E0,stroke:#FFCC80
    
    style UC19 fill:#E8F5E9,stroke:#A5D6A7
    style UC20 fill:#E8F5E9,stroke:#A5D6A7
    style UC21 fill:#E8F5E9,stroke:#A5D6A7
    style UC22 fill:#E8F5E9,stroke:#A5D6A7
    style UC23 fill:#E8F5E9,stroke:#A5D6A7
    style UC24 fill:#E8F5E9,stroke:#A5D6A7
    
    style UC25 fill:#F3E5F5,stroke:#CE93D8
    style UC26 fill:#F3E5F5,stroke:#CE93D8
    style UC27 fill:#F3E5F5,stroke:#CE93D8
    style UC28 fill:#F3E5F5,stroke:#CE93D8
    style UC29 fill:#F3E5F5,stroke:#CE93D8
    style UC30 fill:#F3E5F5,stroke:#CE93D8
    
    style UC31 fill:#E0F7FA,stroke:#80DEEA
    style UC32 fill:#E0F7FA,stroke:#80DEEA
    style UC33 fill:#E0F7FA,stroke:#80DEEA
    style UC34 fill:#E0F7FA,stroke:#80DEEA
    style UC35 fill:#E0F7FA,stroke:#80DEEA
    style UC36 fill:#E0F7FA,stroke:#80DEEA]