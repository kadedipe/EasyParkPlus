# generate_class_diagram.py
import subprocess
import os

# Create directories
os.makedirs('parking-management-uml/diagrams/plantuml', exist_ok=True)
os.makedirs('parking-management-uml/diagrams/images', exist_ok=True)

# PlantUML code
plantuml_code = """@startuml

title Parking Management System - Class Diagram

class Location {
    +id: UUID
    +name: String
    +address: String
    +totalSlots: Integer
    +availableSlots: Integer
}

class ParkingSlot {
    +id: UUID
    +slotNumber: String
    +type: String
    +status: String
    +hourlyRate: Decimal
    +isAvailable(): Boolean
}

class Vehicle {
    +id: UUID
    +licensePlate: String
    +type: String
    +ownerId: UUID
}

class User {
    +id: UUID
    +email: String
    +name: String
    +role: String
}

class ParkingAssignment {
    +id: UUID
    +slotId: UUID
    +vehicleId: UUID
    +userId: UUID
    +checkInTime: DateTime
    +checkOutTime: DateTime
    +status: String
    +totalAmount: Decimal
}

class Payment {
    +id: UUID
    +assignmentId: UUID
    +amount: Decimal
    +status: String
    +method: String
}

' Relationships
Location "1" *-- "*" ParkingSlot
ParkingSlot "1" -- "*" ParkingAssignment
Vehicle "1" -- "*" ParkingAssignment
User "1" -- "*" ParkingAssignment
User "1" -- "*" Vehicle
ParkingAssignment "1" -- "1" Payment

@enduml"""

# Write PlantUML file
with open('parking-management-uml/diagrams/plantuml/class_diagram.puml', 'w') as f:
    f.write(plantuml_code)

print("PlantUML file created successfully!")

# Generate PNG (if PlantUML is installed)
try:
    result = subprocess.run(
        ['plantuml', 'parking-management-uml/diagrams/plantuml/class_diagram.puml', 
         '-o', '../images/'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("PNG generated successfully!")
    else:
        print("Error generating PNG. Make sure PlantUML is installed.")
        print("Error:", result.stderr)
except FileNotFoundError:
    print("PlantUML not found. Please install it or use online generator.")