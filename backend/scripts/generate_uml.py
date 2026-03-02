#!/usr/bin/env python3
"""
UML Diagram Generator for Parking Management System

This script generates various UML diagrams for the system:
1. Class Diagrams
2. Sequence Diagrams
3. Use Case Diagrams
4. Component Diagrams
5. Deployment Diagrams

Requirements:
    pip install pylint
    pip install graphviz
    pip install plantuml
"""

import ast
import os
import sys
import inspect
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import importlib.util
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


# ============================================================================
# AST PARSER AND VISITOR
# ============================================================================

class ClassVisitor(ast.NodeVisitor):
    """AST visitor to extract class information"""
    
    def __init__(self):
        self.classes = []
        self.current_class = None
        
    def visit_ClassDef(self, node):
        """Visit class definition"""
        class_info = {
            'name': node.name,
            'bases': [ast.unparse(base) for base in node.bases],
            'methods': [],
            'attributes': [],
            'decorators': [ast.unparse(dec) for dec in node.decorator_list] if node.decorator_list else [],
            'docstring': ast.get_docstring(node)
        }
        
        self.current_class = class_info
        
        # Visit class body
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = {
                    'name': item.name,
                    'args': [arg.arg for arg in item.args.args],
                    'decorators': [ast.unparse(dec) for dec in item.decorator_list] if item.decorator_list else [],
                    'docstring': ast.get_docstring(item),
                    'is_async': isinstance(item, ast.AsyncFunctionDef)
                }
                class_info['methods'].append(method_info)
            elif isinstance(item, ast.AnnAssign):
                if hasattr(item.target, 'id'):
                    attr_info = {
                        'name': item.target.id,
                        'type': ast.unparse(item.annotation) if item.annotation else None
                    }
                    class_info['attributes'].append(attr_info)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if hasattr(target, 'id'):
                        attr_info = {
                            'name': target.id,
                            'type': 'Any',
                            'value': ast.unparse(item.value) if item.value else None
                        }
                        class_info['attributes'].append(attr_info)
        
        self.classes.append(class_info)
        self.generic_visit(node)


def parse_python_file(file_path: Path) -> List[Dict]:
    """Parse Python file and extract class information"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        visitor = ClassVisitor()
        visitor.visit(tree)
        
        # Add file information
        for class_info in visitor.classes:
            class_info['file'] = file_path.name
            class_info['module'] = file_path.stem
        
        return visitor.classes
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


# ============================================================================
# PLANTUML GENERATOR
# ============================================================================

class PlantUMLGenerator:
    """Generate PlantUML diagrams"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_class_diagram(self, classes: List[Dict], title: str = "Class Diagram") -> str:
        """Generate PlantUML class diagram"""
        puml = f"""@startuml {title.replace(' ', '_')}
skinparam class {{
    BackgroundColor White
    BorderColor Black
    ArrowColor #007acc
    AttributeFontSize 10
    MethodFontSize 10
}}
title {title}
"""
        
        # Add classes
        for class_info in classes:
            puml += f"class {class_info['name']} {{\n"
            
            # Add attributes
            for attr in class_info.get('attributes', []):
                if attr.get('type'):
                    puml += f"  {attr['type']} {attr['name']}\n"
                else:
                    puml += f"  {attr['name']}\n"
            
            if class_info.get('attributes') and class_info.get('methods'):
                puml += "  --\n"
            
            # Add methods
            for method in class_info.get('methods', []):
                params = ', '.join(method['args'][1:] if method['args'] and method['args'][0] == 'self' else method['args'])
                async_prefix = "{abstract} " if method.get('is_async') else ""
                puml += f"  {async_prefix}{method['name']}({params})\n"
            
            puml += "}\n"
            
            # Add inheritance relationships
            for base in class_info.get('bases', []):
                if base != 'object' and not base.startswith('typing.'):
                    puml += f"{base} <|-- {class_info['name']}\n"
            
            # Add composition/aggregation based on attribute types
            for attr in class_info.get('attributes', []):
                attr_type = attr.get('type', '')
                if attr_type and any(cls['name'] in attr_type for cls in classes):
                    # Simple heuristic: if attribute type is another class, it's composition
                    for cls in classes:
                        if cls['name'] in attr_type:
                            puml += f"{class_info['name']} *-- {cls['name']} : {attr['name']}\n"
                            break
        
        puml += "@enduml"
        
        # Save file
        output_file = self.output_dir / f"{title.replace(' ', '_').lower()}.puml"
        output_file.write_text(puml)
        
        return str(output_file)
    
    def generate_package_diagram(self, packages: Dict[str, List[str]], title: str = "Package Diagram") -> str:
        """Generate PlantUML package diagram"""
        puml = f"""@startuml {title.replace(' ', '_')}
skinparam package {{
    BackgroundColor White
    BorderColor Black
    FontColor Black
}}
title {title}
"""
        
        # Add packages and their classes
        for package, classes in packages.items():
            puml += f"package {package} {{\n"
            for cls in classes:
                puml += f"  class {cls}\n"
            puml += "}\n"
        
        # Add dependencies between packages (simplified)
        if "presentation" in packages and "application" in packages:
            puml += "[presentation] --> [application] : uses\n"
        if "application" in packages and "domain" in packages:
            puml += "[application] --> [domain] : uses\n"
        if "application" in packages and "infrastructure" in packages:
            puml += "[application] --> [infrastructure] : uses\n"
        
        puml += "@enduml"
        
        output_file = self.output_dir / f"{title.replace(' ', '_').lower()}.puml"
        output_file.write_text(puml)
        
        return str(output_file)
    
    def generate_sequence_diagram(self, scenario: str, title: str = "Sequence Diagram") -> str:
        """Generate PlantUML sequence diagram for a specific scenario"""
        
        scenarios = {
            "park_vehicle": """@startuml park_vehicle_sequence
title Vehicle Parking Sequence Diagram

actor User
participant "Parking GUI" as GUI
participant "ParkingAppController" as Controller
participant "CommandProcessor" as Processor
participant "ParkingService" as Service
participant "ParkingLot" as Lot
participant "ParkingSlot" as Slot

User -> GUI: Park Vehicle
GUI -> Controller: park_vehicle(vehicle_data)
Controller -> Processor: process(ParkVehicleCommand)
Processor -> Service: park_vehicle(request)
Service -> Lot: find_available_slot()
Lot -> Slot: check_availability()
Slot --> Lot: available
Lot --> Service: slot_found
Service -> Slot: occupy(vehicle_id)
Slot --> Service: occupied
Service --> Processor: success
Processor --> Controller: result
Controller --> GUI: success_message
GUI --> User: Vehicle Parked Successfully

@enduml""",
            
            "exit_vehicle": """@startuml exit_vehicle_sequence
title Vehicle Exit Sequence Diagram

actor User
participant "Parking GUI" as GUI
participant "ParkingAppController" as Controller
participant "CommandProcessor" as Processor
participant "ParkingService" as Service
participant "ParkingLot" as Lot
participant "ParkingSlot" as Slot
participant "BillingService" as Billing

User -> GUI: Exit Vehicle
GUI -> Controller: exit_vehicle(license_plate)
Controller -> Processor: process(ExitVehicleCommand)
Processor -> Service: exit_vehicle(request)
Service -> Lot: find_vehicle_slot(license_plate)
Lot -> Slot: get_vehicle_info()
Slot --> Lot: vehicle_info
Lot --> Service: slot_info
Service -> Billing: calculate_charge(duration)
Billing --> Service: amount
Service -> Slot: vacate()
Slot --> Service: vacated
Service --> Processor: billing_info
Processor --> Controller: result
Controller --> GUI: billing_details
GUI --> User: Payment Required

@enduml""",
            
            "add_parking_lot": """@startuml add_parking_lot_sequence
title Add Parking Lot Sequence Diagram

actor Admin
participant "Parking GUI" as GUI
participant "ParkingAppController" as Controller
participant "ParkingService" as Service
participant "ParkingLotFactory" as Factory
participant "Repository" as Repo

Admin -> GUI: Add New Parking Lot
GUI -> Controller: add_parking_lot(lot_data)
Controller -> Service: create_parking_lot(lot_data)
Service -> Factory: create(lot_data)
Factory --> Service: parking_lot
Service -> Repo: save(parking_lot)
Repo --> Service: saved
Service --> Controller: success
Controller --> GUI: success_message
GUI --> Admin: Parking Lot Added

@enduml"""
        }
        
        if scenario in scenarios:
            puml = scenarios[scenario]
            output_file = self.output_dir / f"{scenario}_sequence.puml"
            output_file.write_text(puml)
            return str(output_file)
        else:
            # Generate generic sequence diagram
            puml = f"""@startuml {scenario}_sequence
title {title}

actor User
participant "GUI Layer" as GUI
participant "Controller" as Controller
participant "Service Layer" as Service
participant "Domain Layer" as Domain
participant "Infrastructure" as Infrastructure

User -> GUI: User Action
GUI -> Controller: handle_action(data)
Controller -> Service: process_request(data)
Service -> Domain: execute_business_logic()
Domain -> Infrastructure: persist_data()
Infrastructure --> Domain: result
Domain --> Service: business_result
Service --> Controller: service_result
Controller --> GUI: response
GUI --> User: Display Result

@enduml"""
            
            output_file = self.output_dir / f"{scenario}_sequence.puml"
            output_file.write_text(puml)
            return str(output_file)
    
    def generate_use_case_diagram(self, title: str = "Use Case Diagram") -> str:
        """Generate PlantUML use case diagram"""
        puml = f"""@startuml {title.replace(' ', '_')}
skinparam usecase {{
    BackgroundColor White
    BorderColor Black
    FontColor Black
}}
title {title}

actor "Parking Attendant" as Attendant
actor "System Administrator" as Admin
actor "Vehicle Owner" as Owner
actor "EV Owner" as EVOwner

rectangle "Parking Management System" {{
  usecase "Park Vehicle" as UC1
  usecase "Exit Vehicle" as UC2
  usecase "Process Payment" as UC3
  usecase "Manage Parking Lots" as UC4
  usecase "Generate Reports" as UC5
  usecase "Monitor EV Charging" as UC6
  usecase "Make Reservation" as UC7
  usecase "View Real-time Availability" as UC8
}}

Attendant --> UC1
Attendant --> UC2
Attendant --> UC3
Attendant --> UC8

Admin --> UC4
Admin --> UC5

Owner --> UC1
Owner --> UC2
Owner --> UC3
Owner --> UC7
Owner --> UC8

EVOwner --> UC6
EVOwner --> UC1
EVOwner --> UC2
EVOwner --> UC3

UC1 ..> UC8 : includes
UC2 ..> UC3 : extends
UC6 ..> UC1 : extends

@enduml"""
        
        output_file = self.output_dir / "use_case_diagram.puml"
        output_file.write_text(puml)
        
        return str(output_file)
    
    def generate_component_diagram(self, title: str = "Component Diagram") -> str:
        """Generate PlantUML component diagram"""
        puml = f"""@startuml {title.replace(' ', '_')}
skinparam component {{
    BackgroundColor White
    BorderColor Black
    FontColor Black
}}
title {title}

package "Presentation Layer" {{
  [Parking GUI] as GUI
  [Controllers] as Controllers
  [Views] as Views
  [Dialogs] as Dialogs
  
  GUI --> Controllers
  Controllers --> Views
  Views --> Dialogs
}}

package "Application Layer" {{
  [Parking Service] as Service
  [Command Processor] as Command
  [Event Bus] as EventBus
  [DTOs] as DTOs
  
  Service --> Command
  Service --> EventBus
  Command --> DTOs
}}

package "Domain Layer" {{
  [Entities] as Entities
  [Value Objects] as VOs
  [Domain Events] as Events
  [Business Rules] as Rules
  
  Entities --> VOs
  Entities --> Events
  Events --> Rules
}}

package "Infrastructure Layer" {{
  [Repositories] as Repos
  [Factories] as Factories
  [External Services] as External
  [Database] as DB
  
  Repos --> DB
  Factories --> Repos
}}

[Controllers] --> [Service] : uses
[Service] --> [Entities] : manipulates
[Service] --> [Repos] : persists data
[Repos] --> [Entities] : manages
[EventBus] --> [Events] : publishes

note top of GUI : Tkinter-based desktop application
note right of DB : PostgreSQL / SQLite
note left of External : Payment Gateway, SMS Service

@enduml"""
        
        output_file = self.output_dir / "component_diagram.puml"
        output_file.write_text(puml)
        
        return str(output_file)
    
    def generate_deployment_diagram(self, title: str = "Deployment Diagram") -> str:
        """Generate PlantUML deployment diagram"""
        puml = f"""@startuml {title.replace(' ', '_')}
skinparam node {{
    BackgroundColor White
    BorderColor Black
    FontColor Black
}}
title {title}

node "Client Workstation" {{
  artifact "Parking Management GUI" as GUI
  database "Local Cache" as Cache
  GUI --> Cache
}}

node "Application Server" {{
  [API Gateway] as API
  [Business Logic] as Business
  [Authentication] as Auth
  [Billing Engine] as Billing
  
  API --> Business
  Business --> Auth
  Business --> Billing
}}

node "Database Server" {{
  database "PostgreSQL" as PG {
    folder "Parking Data" {
      file "parking_lots"
      file "vehicles"
      file "transactions"
    }
  }
}}

node "External Services" {{
  cloud "Payment Gateway" as Payment
  cloud "SMS Service" as SMS
  cloud "Email Service" as Email
}}

GUI --> API : HTTP/REST
Business --> PG : SQL
Business --> Payment : API Call
Business --> SMS : SMS API
Business --> Email : SMTP

@enduml"""
        
        output_file = self.output_dir / "deployment_diagram.puml"
        output_file.write_text(puml)
        
        return str(output_file)
    
    def generate_activity_diagram(self, process: str, title: str = "Activity Diagram") -> str:
        """Generate PlantUML activity diagram"""
        
        processes = {
            "vehicle_parking": """@startuml vehicle_parking_activity
title Vehicle Parking Process

start
:Driver arrives at parking lot;
:Enter license plate/details;
if (Vehicle registered?) then (yes)
else (no)
  :Register new vehicle;
endif

:Check available slots;
if (Slot available?) then (yes)
  :Allocate parking slot;
  :Generate ticket;
  :Open gate;
  :Vehicle enters;
  :Update occupancy;
  stop
else (no)
  :Display "Lot Full" message;
  stop
endif

@enduml""",
            
            "vehicle_exit": """@startuml vehicle_exit_activity
title Vehicle Exit Process

start
:Driver requests exit;
:Enter ticket/plate number;
:Calculate parking duration;
:Calculate charges;
:Display amount due;

if (Payment method?) then (cash)
  :Accept cash payment;
  :Provide receipt;
else (card)
  :Process card payment;
  :Provide receipt;
else (digital)
  :Process digital wallet;
  :Provide e-receipt;
endif

:Release parking slot;
:Open exit gate;
:Update system records;
stop

@enduml""",
            
            "ev_charging": """@startuml ev_charging_activity
title EV Charging Process

start
:EV arrives at charging station;
:Check charging compatibility;
if (Compatible?) then (yes)
  :Connect charging cable;
  :Authenticate user;
  :Start charging session;
  
  repeat
    :Monitor charging progress;
    :Update display;
  repeat while (Charging complete?) is (no)
  
  :Stop charging;
  :Calculate energy used;
  :Generate charging bill;
  :Process payment;
  :Disconnect cable;
  stop
else (no)
  :Display incompatibility message;
  stop
endif

@enduml"""
        }
        
        if process in processes:
            puml = processes[process]
            output_file = self.output_dir / f"{process}_activity.puml"
            output_file.write_text(puml)
            return str(output_file)
        else:
            puml = f"""@startuml {process}_activity
title {title}

start
:Start Process;
:Perform Step 1;
:Perform Step 2;
if (Decision?) then (Yes)
  :Perform Action A;
else (No)
  :Perform Action B;
endif
:Complete Process;
stop

@enduml"""
            
            output_file = self.output_dir / f"{process}_activity.puml"
            output_file.write_text(puml)
            return str(output_file)
    
    def generate_state_diagram(self, entity: str, title: str = "State Diagram") -> str:
        """Generate PlantUML state diagram"""
        
        entities = {
            "parking_slot": """@startuml parking_slot_state
title Parking Slot State Diagram

state "Available" as Available
state "Reserved" as Reserved
state "Occupied" as Occupied
state "Maintenance" as Maintenance
state "Disabled" as Disabled

[*] --> Available

Available --> Reserved : reserve()
Reserved --> Available : cancel_reservation()
Reserved --> Occupied : occupy()
Available --> Occupied : occupy()
Occupied --> Available : vacate()

Available --> Maintenance : start_maintenance()
Maintenance --> Available : complete_maintenance()

Available --> Disabled : disable()
Disabled --> Available : enable()

Occupied --> Maintenance : emergency_maintenance()
Maintenance --> Available : repair_complete()

@enduml""",
            
            "parking_ticket": """@startuml parking_ticket_state
title Parking Ticket State Diagram

state "Issued" as Issued
state "Valid" as Valid
state "Expired" as Expired
state "Paid" as Paid
state "Cancelled" as Cancelled

[*] --> Issued
Issued --> Valid : activate()
Valid --> Expired : time_expired()
Valid --> Paid : process_payment()
Expired --> Paid : process_payment(with_penalty)
Valid --> Cancelled : cancel()
Expired --> Cancelled : cancel()
Paid --> [*] : exit()
Cancelled --> [*]

@enduml""",
            
            "ev_charging_session": """@startuml ev_charging_session_state
title EV Charging Session State Diagram

state "Idle" as Idle
state "Connected" as Connected
state "Authenticating" as Authenticating
state "Charging" as Charging
state "Paused" as Paused
state "Completed" as Completed
state "Fault" as Fault

[*] --> Idle
Idle --> Connected : connect_cable()
Connected --> Authenticating : start_authentication()
Authenticating --> Charging : authentication_successful()
Authenticating --> Connected : authentication_failed()

Charging --> Paused : pause_charging()
Paused --> Charging : resume_charging()
Charging --> Completed : target_reached()
Charging --> Fault : error_detected()
Fault --> Idle : reset()
Completed --> Idle : disconnect_cable()

@enduml"""
        }
        
        if entity in entities:
            puml = entities[entity]
            output_file = self.output_dir / f"{entity}_state.puml"
            output_file.write_text(puml)
            return str(output_file)
        else:
            puml = f"""@startuml {entity}_state
title {title}

state "State1" as S1
state "State2" as S2
state "State3" as S3

[*] --> S1
S1 --> S2 : event1()
S2 --> S3 : event2()
S3 --> S1 : event3()
S2 --> [*] : final_event()

@enduml"""
            
            output_file = self.output_dir / f"{entity}_state.puml"
            output_file.write_text(puml)
            return str(output_file)


# ============================================================================
# GRAPHVIZ GENERATOR
# ============================================================================

class GraphvizGenerator:
    """Generate Graphviz diagrams"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_dependency_graph(self, dependencies: Dict[str, List[str]], title: str = "Dependency Graph") -> str:
        """Generate Graphviz dependency graph"""
        dot = f"""digraph G {{
    rankdir=LR;
    node [shape=box, style=filled, fillcolor=lightblue];
    edge [color=gray50];
    label="{title}";
    fontsize=20;
    
"""
        
        # Add nodes
        for module in dependencies.keys():
            dot += f'    "{module}" [shape=box];\n'
        
        # Add edges
        for source, targets in dependencies.items():
            for target in targets:
                dot += f'    "{source}" -> "{target}";\n'
        
        dot += "}"
        
        output_file = self.output_dir / f"{title.replace(' ', '_').lower()}.dot"
        output_file.write_text(dot)
        
        return str(output_file)
    
    def generate_call_graph(self, calls: List[Tuple[str, str]], title: str = "Call Graph") -> str:
        """Generate Graphviz call graph"""
        dot = f"""digraph G {{
    rankdir=TB;
    node [shape=ellipse, style=filled, fillcolor=lightyellow];
    edge [color=blue];
    label="{title}";
    fontsize=20;
    
"""
        
        # Get unique functions
        functions = set()
        for caller, callee in calls:
            functions.add(caller)
            functions.add(callee)
        
        # Add nodes
        for func in functions:
            dot += f'    "{func}";\n'
        
        # Add edges
        for caller, callee in calls:
            dot += f'    "{caller}" -> "{callee}";\n'
        
        dot += "}"
        
        output_file = self.output_dir / f"{title.replace(' ', '_').lower()}.dot"
        output_file.write_text(dot)
        
        return str(output_file)
    
    def generate_module_hierarchy(self, hierarchy: Dict[str, List[str]], title: str = "Module Hierarchy") -> str:
        """Generate Graphviz module hierarchy"""
        dot = f"""digraph G {{
    rankdir=TB;
    node [shape=folder, style=filled, fillcolor=lightgreen];
    edge [color=darkgreen];
    label="{title}";
    fontsize=20;
    
"""
        
        def add_node(parent, children, depth=0):
            indent = "    " * depth
            dot = ""
            
            if parent:
                dot += f'{indent}"{parent}";\n'
            
            for child in children:
                if isinstance(child, dict):
                    for key, subchildren in child.items():
                        dot += f'{indent}"{parent}" -> "{key}";\n'
                        dot += add_node(key, subchildren, depth + 1)
                else:
                    dot += f'{indent}"{parent}" -> "{child}";\n'
            
            return dot
        
        # Build hierarchy
        dot += add_node("", hierarchy)
        
        dot += "}"
        
        output_file = self.output_dir / f"{title.replace(' ', '_').lower()}.dot"
        output_file.write_text(dot)
        
        return str(output_file)


# ============================================================================
# CODE ANALYSIS
# ============================================================================

class CodeAnalyzer:
    """Analyze code structure and dependencies"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.all_classes = []
        self.modules = {}
        
    def analyze_project(self):
        """Analyze entire project structure"""
        print(f"Analyzing project at: {self.project_root}")
        
        # Walk through all Python files
        for file_path in self.project_root.rglob("*.py"):
            # Skip test files and __pycache__
            if "test" in str(file_path) or "__pycache__" in str(file_path):
                continue
            
            rel_path = file_path.relative_to(self.project_root)
            print(f"  Analyzing: {rel_path}")
            
            classes = parse_python_file(file_path)
            if classes:
                self.all_classes.extend(classes)
                
                # Group by module
                module_name = str(rel_path.parent).replace('/', '.').replace('\\', '.')
                if module_name not in self.modules:
                    self.modules[module_name] = []
                self.modules[module_name].extend([cls['name'] for cls in classes])
    
    def get_package_structure(self) -> Dict:
        """Get package structure"""
        packages = {}
        for module, classes in self.modules.items():
            # Extract package name (first part before dot)
            package = module.split('.')[0] if '.' in module else module
            if package not in packages:
                packages[package] = []
            packages[package].extend(classes)
        
        return packages
    
    def get_class_hierarchy(self) -> Dict:
        """Get class inheritance hierarchy"""
        hierarchy = {}
        
        for class_info in self.all_classes:
            class_name = class_info['name']
            bases = class_info['bases']
            
            for base in bases:
                if base not in hierarchy:
                    hierarchy[base] = []
                hierarchy[base].append(class_name)
        
        return hierarchy
    
    def get_dependencies(self) -> Dict[str, List[str]]:
        """Extract dependencies between modules"""
        dependencies = {}
        
        # Simple heuristic: import statements analysis would be better
        # For now, use package structure
        packages = self.get_package_structure()
        
        # Define expected dependencies based on architecture
        if 'presentation' in packages:
            dependencies['presentation'] = ['application']
        if 'application' in packages:
            dependencies['application'] = ['domain', 'infrastructure']
        if 'domain' in packages:
            dependencies['domain'] = []
        if 'infrastructure' in packages:
            dependencies['infrastructure'] = ['domain']
        
        return dependencies


# ============================================================================
# DIAGRAM RENDERER
# ============================================================================

class DiagramRenderer:
    """Render diagrams to various formats"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def render_plantuml(self, puml_file: Path, format: str = "png") -> Optional[Path]:
        """Render PlantUML file to image"""
        try:
            # Check if PlantUML is available
            result = subprocess.run(['plantuml', '-version'], capture_output=True, text=True)
            if result.returncode != 0:
                print("PlantUML not found. Please install it from: https://plantuml.com/")
                print("Or use the online version.")
                return None
            
            # Render diagram
            output_file = puml_file.with_suffix(f'.{format}')
            cmd = ['plantuml', f'-t{format}', str(puml_file), '-o', str(self.output_dir)]
            
            print(f"Rendering {puml_file.name} to {format}...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                output_path = self.output_dir / output_file.name
                print(f"  Generated: {output_path}")
                return output_path
            else:
                print(f"  Error: {result.stderr}")
                return None
                
        except FileNotFoundError:
            print("PlantUML not found in PATH. Please install it.")
            print("You can also view the .puml files online at: http://www.plantuml.com/plantuml/uml/")
            return None
    
    def render_graphviz(self, dot_file: Path, format: str = "png") -> Optional[Path]:
        """Render Graphviz file to image"""
        try:
            # Check if Graphviz is available
            result = subprocess.run(['dot', '-V'], capture_output=True, text=True)
            if result.returncode != 0:
                print("Graphviz not found. Please install it from: https://graphviz.org/")
                return None
            
            # Render diagram
            output_file = dot_file.with_suffix(f'.{format}')
            cmd = ['dot', f'-T{format}', str(dot_file), '-o', str(output_file)]
            
            print(f"Rendering {dot_file.name} to {format}...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  Generated: {output_file}")
                return output_file
            else:
                print(f"  Error: {result.stderr}")
                return None
                
        except FileNotFoundError:
            print("Graphviz not found in PATH. Please install it.")
            return None
    
    def generate_html_report(self, diagrams: List[Dict], output_file: Path):
        """Generate HTML report with all diagrams"""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Parking Management System - UML Diagrams</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .diagram-section {
            background-color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .diagram-title {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .diagram-container {
            text-align: center;
            margin: 20px 0;
        }
        img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        .download-links {
            margin-top: 10px;
            font-size: 14px;
        }
        a {
            color: #3498db;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .no-diagram {
            color: #7f8c8d;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Parking Management System</h1>
        <h2>UML Diagrams and Documentation</h2>
        <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    </div>
"""
        
        # Add diagram sections
        for diagram in diagrams:
            html += f"""
    <div class="diagram-section">
        <h3 class="diagram-title">{diagram['title']}</h3>
        <p>{diagram.get('description', '')}</p>
"""
            
            if diagram.get('image_path'):
                html += f"""
        <div class="diagram-container">
            <img src="{diagram['image_path'].name}" alt="{diagram['title']}">
        </div>
"""
            
            html += f"""
        <div class="download-links">
"""
            
            if diagram.get('source_path'):
                html += f'            <a href="{diagram["source_path"].name}">Source File</a> | '
            
            if diagram.get('image_path'):
                html += f'            <a href="{diagram["image_path"].name}">Download Image</a>'
            
            html += """
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        output_file.write_text(html)
        print(f"\nHTML report generated: {output_file}")
        return output_file


# ============================================================================
# MAIN SCRIPT
# ============================================================================

import argparse
from datetime import datetime

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate UML diagrams for Parking Management System')
    parser.add_argument('--project-root', type=Path, default=Path.cwd().parent,
                       help='Project root directory (default: parent of scripts directory)')
    parser.add_argument('--output-dir', type=Path, default=Path('docs/uml'),
                       help='Output directory for diagrams (default: docs/uml)')
    parser.add_argument('--format', choices=['png', 'svg', 'pdf', 'all'], default='png',
                       help='Output format for diagrams (default: png)')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze code, do not generate diagrams')
    parser.add_argument('--generate-report', action='store_true',
                       help='Generate HTML report with all diagrams')
    parser.add_argument('--diagram-type', choices=['all', 'class', 'sequence', 'usecase', 'component',
                                                  'deployment', 'activity', 'state', 'package'],
                       default='all', help='Type of diagram to generate (default: all)')
    
    args = parser.parse_args()
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("Parking Management System - UML Diagram Generator")
    print("=" * 70)
    
    # Analyze code
    analyzer = CodeAnalyzer(args.project_root)
    analyzer.analyze_project()
    
    if args.analyze_only:
        print("\nCode Analysis Complete:")
        print(f"  Total Classes: {len(analyzer.all_classes)}")
        print(f"  Modules: {len(analyzer.modules)}")
        return
    
    # Initialize generators
    plantuml_gen = PlantUMLGenerator(args.output_dir)
    graphviz_gen = GraphvizGenerator(args.output_dir)
    renderer = DiagramRenderer(args.output_dir)
    
    diagrams = []
    
    # Generate selected diagrams
    if args.diagram_type in ['all', 'class']:
        print("\nGenerating Class Diagram...")
        class_file = plantuml_gen.generate_class_diagram(
            analyzer.all_classes[:20],  # Limit to first 20 classes for clarity
            "Parking System Class Diagram"
        )
        if class_file:
            img_file = renderer.render_plantuml(Path(class_file), args.format)
            diagrams.append({
                'title': 'Class Diagram',
                'description': 'Shows the main classes and their relationships',
                'source_path': Path(class_file),
                'image_path': img_file
            })
    
    if args.diagram_type in ['all', 'package']:
        print("\nGenerating Package Diagram...")
        packages = analyzer.get_package_structure()
        package_file = plantuml_gen.generate_package_diagram(
            packages, "Parking System Package Diagram"
        )
        if package_file:
            img_file = renderer.render_plantuml(Path(package_file), args.format)
            diagrams.append({
                'title': 'Package Diagram',
                'description': 'Shows package structure and dependencies',
                'source_path': Path(package_file),
                'image_path': img_file
            })
    
    if args.diagram_type in ['all', 'usecase']:
        print("\nGenerating Use Case Diagram...")
        usecase_file = plantuml_gen.generate_use_case_diagram()
        if usecase_file:
            img_file = renderer.render_plantuml(Path(usecase_file), args.format)
            diagrams.append({
                'title': 'Use Case Diagram',
                'description': 'Shows system functionalities and actors',
                'source_path': Path(usecase_file),
                'image_path': img_file
            })
    
    if args.diagram_type in ['all', 'component']:
        print("\nGenerating Component Diagram...")
        component_file = plantuml_gen.generate_component_diagram()
        if component_file:
            img_file = renderer.render_plantuml(Path(component_file), args.format)
            diagrams.append({
                'title': 'Component Diagram',
                'description': 'Shows system components and their relationships',
                'source_path': Path(component_file),
                'image_path': img_file
            })
    
    if args.diagram_type in ['all', 'deployment']:
        print("\nGenerating Deployment Diagram...")
        deployment_file = plantuml_gen.generate_deployment_diagram()
        if deployment_file:
            img_file = renderer.render_plantuml(Path(deployment_file), args.format)
            diagrams.append({
                'title': 'Deployment Diagram',
                'description': 'Shows system deployment architecture',
                'source_path': Path(deployment_file),
                'image_path': img_file
            })
    
    if args.diagram_type in ['all', 'sequence']:
        print("\nGenerating Sequence Diagrams...")
        for scenario in ['park_vehicle', 'exit_vehicle', 'add_parking_lot']:
            seq_file = plantuml_gen.generate_sequence_diagram(
                scenario, f"{scenario.replace('_', ' ').title()} Sequence"
            )
            if seq_file:
                img_file = renderer.render_plantuml(Path(seq_file), args.format)
                diagrams.append({
                    'title': f'{scenario.replace("_", " ").title()} Sequence Diagram',
                    'description': f'Shows sequence of operations for {scenario.replace("_", " ")}',
                    'source_path': Path(seq_file),
                    'image_path': img_file
                })
    
    if args.diagram_type in ['all', 'activity']:
        print("\nGenerating Activity Diagrams...")
        for process in ['vehicle_parking', 'vehicle_exit', 'ev_charging']:
            act_file = plantuml_gen.generate_activity_diagram(
                process, f"{process.replace('_', ' ').title()} Activity"
            )
            if act_file:
                img_file = renderer.render_plantuml(Path(act_file), args.format)
                diagrams.append({
                    'title': f'{process.replace("_", " ").title()} Activity Diagram',
                    'description': f'Shows activity flow for {process.replace("_", " ")}',
                    'source_path': Path(act_file),
                    'image_path': img_file
                })
    
    if args.diagram_type in ['all', 'state']:
        print("\nGenerating State Diagrams...")
        for entity in ['parking_slot', 'parking_ticket', 'ev_charging_session']:
            state_file = plantuml_gen.generate_state_diagram(
                entity, f"{entity.replace('_', ' ').title()} State"
            )
            if state_file:
                img_file = renderer.render_plantuml(Path(state_file), args.format)
                diagrams.append({
                    'title': f'{entity.replace("_", " ").title()} State Diagram',
                    'description': f'Shows state transitions for {entity.replace("_", " ")}',
                    'source_path': Path(state_file),
                    'image_path': img_file
                })
    
    # Generate dependency graph
    print("\nGenerating Dependency Graph...")
    dependencies = analyzer.get_dependencies()
    if dependencies:
        dep_file = graphviz_gen.generate_dependency_graph(
            dependencies, "System Dependencies"
        )
        if dep_file:
            img_file = renderer.render_graphviz(Path(dep_file), args.format)
            diagrams.append({
                'title': 'Dependency Graph',
                'description': 'Shows dependencies between system modules',
                'source_path': Path(dep_file),
                'image_path': img_file
            })
    
    # Generate HTML report if requested
    if args.generate_report and diagrams:
        print("\nGenerating HTML Report...")
        report_file = args.output_dir / 'uml_report.html'
        renderer.generate_html_report(diagrams, report_file)
    
    print("\n" + "=" * 70)
    print("Diagram Generation Complete!")
    print("=" * 70)
    
    # Print summary
    print(f"\nGenerated {len(diagrams)} diagrams in: {args.output_dir.absolute()}")
    
    if diagrams:
        print("\nAvailable diagrams:")
        for i, diagram in enumerate(diagrams, 1):
            print(f"  {i}. {diagram['title']}")
            if diagram.get('image_path'):
                print(f"     Image: {diagram['image_path'].name}")
            if diagram.get('source_path'):
                print(f"     Source: {diagram['source_path'].name}")
            print()
    
    print("\nNote: If PlantUML/Graphviz is not installed, you can:")
    print("  1. Install them to generate images locally")
    print("  2. View .puml files online at: http://www.plantuml.com/plantuml/uml/")
    print("  3. View .dot files with any Graphviz viewer")


if __name__ == "__main__":
    main()