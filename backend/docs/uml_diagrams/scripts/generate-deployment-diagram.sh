#!/bin/bash
# generate-deployment-diagram.sh

set -e

echo "🚗 Generating Parking Management System Deployment Diagram..."

# Create directories
mkdir -p parking-management-uml/diagrams/{plantuml,images}

# Create simplified PlantUML file
cat > parking-management-uml/diagrams/plantuml/deployment_diagram.puml << 'EOF'
@startuml

title Parking Management System - Deployment Architecture

skinparam component {
    BackgroundColor<<Frontend>> #E3F2FD
    BackgroundColor<<Backend>> #F3E5F5
    BackgroundColor<<Database>> #C8E6C9
    BackgroundColor<<Cache>> #FFCCBC
    BackgroundColor<<Storage>> #FFF3E0
    BorderColor #263238
}

' User Access
cloud "Users" {
    rectangle "Mobile App\n(iOS/Android)"
    rectangle "Web Portal\n(React)"
    rectangle "Admin Dashboard\n(Vue.js)"
}

' Load Balancer & API Gateway
component "API Gateway + Load Balancer" as gateway {
    rectangle "NGINX/ALB" as alb
    rectangle "Rate Limiting" as rate_limit
    rectangle "SSL Termination" as ssl
}

' Application Layer
node "Application Servers" as app_servers {
    component "Parking API Service" as parking_api <<Backend>>
    component "Payment Service" as payment_service <<Backend>>
    component "User Service" as user_service <<Backend>>
    component "Notification Service" as notification_service <<Backend>>
}

' Data Layer
node "Data Storage" as data_storage {
    database "PostgreSQL Cluster" as postgresql <<Database>> {
        rectangle "Primary\n(us-east-1a)"
        rectangle "Replica\n(us-east-1b)"
        rectangle "Replica\n(us-east-1c)"
    }
    
    component "Redis Cluster" as redis <<Cache>> {
        rectangle "Cache Layer"
        rectangle "Session Store"
        rectangle "Message Queue"
    }
    
    component "Object Storage" as s3 <<Storage>> {
        rectangle "User Uploads"
        rectangle "Backups"
        rectangle "Static Assets"
    }
}

' External Services
cloud "External Systems" {
    rectangle "Payment Processors\n(Stripe, PayPal)"
    rectangle "SMS/Email Services\n(Twilio, SendGrid)"
    rectangle "IoT Devices\n(Sensors, Cameras)"
}

' Monitoring
component "Monitoring Stack" as monitoring {
    rectangle "Prometheus\n(Metrics)"
    rectangle "Grafana\n(Dashboards)"
    rectangle "ELK Stack\n(Logging)"
}

' Connections
Users --> gateway : "HTTPS/WebSocket"
gateway --> app_servers : "Load Balanced"
parking_api --> postgresql : "SQL"
payment_service --> postgresql : "SQL"
user_service --> postgresql : "SQL"
app_servers --> redis : "Cache Access"
app_servers --> s3 : "Object Storage"
payment_service --> "Payment Processors" : "API Calls"
notification_service --> "SMS/Email Services" : "API Calls"
parking_api --> "IoT Devices" : "MQTT/WebSocket"
app_servers --> monitoring : "Metrics & Logs"

' Notes
note right of gateway
    <b>Security Features:</b>
    • JWT Authentication
    • Rate Limiting
    • DDoS Protection
    • WAF Rules
end note

note left of postgresql
    <b>Database:</b>
    • Multi-AZ Deployment
    • Automated Backups
    • Read Replicas
    • Point-in-Time Recovery
end note

legend bottom
    | Architecture Overview |
    Users : End-user access points |
    API Gateway : Security & routing layer |
    Application Servers : Business logic services |
    Data Storage : Persistent data layer |
    External Systems : Third-party integrations |
    Monitoring : Observability stack |
end legend

@enduml
EOF

echo "✓ PlantUML file created"

# Check if PlantUML is installed
if command -v plantuml &> /dev/null; then
    # Generate SVG
    plantuml -tsvg parking-management-uml/diagrams/plantuml/deployment_diagram.puml -o ../images/
    
    if [ $? -eq 0 ]; then
        echo "✓ SVG generated successfully!"
        echo ""
        echo "📁 Files created:"
        echo "  • parking-management-uml/diagrams/plantuml/deployment_diagram.puml"
        echo "  • parking-management-uml/diagrams/images/deployment_diagram.svg"
        echo ""
        echo "🔧 To view the diagram:"
        echo "  • Open the SVG file in any modern browser"
        echo "  • Or use: xdg-open parking-management-uml/diagrams/images/deployment_diagram.svg"
    else
        echo "✗ Failed to generate SVG"
        exit 1
    fi
else
    echo "⚠️ PlantUML not found. Generating instructions instead..."
    echo ""
    echo "📝 To generate the SVG, you need PlantUML installed:"
    echo ""
    echo "1. Install PlantUML:"
    echo "   macOS: brew install plantuml"
    echo "   Ubuntu: sudo apt-get install plantuml"
    echo "   Or download from: https://plantuml.com/download"
    echo ""
    echo "2. Then run:"
    echo "   plantuml -tsvg parking-management-uml/diagrams/plantuml/deployment_diagram.puml -o ../images/"
    echo ""
    echo "3. Or use the online version:"
    echo "   • Go to https://www.plantuml.com/plantuml/uml/"
    echo "   • Copy the content of deployment_diagram.puml"
    echo "   • Paste and generate, then save as SVG"
fi