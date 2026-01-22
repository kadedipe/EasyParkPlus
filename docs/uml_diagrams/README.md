## UML Diagrams for Parking Management System

## Overview

This directory contains complete UML (Unified Modeling Language) diagrams for the Parking Management System. These diagrams provide visual representations of the system's structure, behavior, and interactions, serving as essential documentation for developers, architects, and stakeholders.

## Diagram Types

### Structural Diagrams
1. **[Class Diagrams](./class_diagrams.md)** - System structure and relationships
2. **[Component Diagrams](./component_diagrams.md)** - System components and dependencies
3. **[Deployment Diagrams](./deployment_diagrams.md)** - Physical deployment architecture
4. **[Object Diagrams](./object_diagrams.md)** - Object instances at runtime
5. **[Package Diagrams](./package_diagrams.md)** - Logical grouping of elements

### Behavioral Diagrams
6. **[Use Case Diagrams](./use_case_diagrams.md)** - System functionality and actors
7. **[Sequence Diagrams](./sequence_diagrams.md)** - Message flow between objects
8. **[Activity Diagrams](./activity_diagrams.md)** - Business process workflows
9. **[State Machine Diagrams](./state_machine_diagrams.md)** - Object state transitions
10. **[Communication Diagrams](./communication_diagrams.md)** - Object interactions

### Specialized Diagrams
11. **[Entity-Relationship Diagrams](./entity_relationship_diagrams.md)** - Database schema
12. **[Architecture Diagrams](./architecture_diagrams.md)** - High-level system architecture
13. **[Data Flow Diagrams](./data_flow_diagrams.md)** - Data movement through system
14. **[Timing Diagrams](./timing_diagrams.md)** - Timing constraints and behaviors

## Tools and Standards

### Diagram Tools
- **PlantUML**: Text-based diagram generation
- **Mermaid.js**: Markdown-friendly diagrams
- **draw.io**: Interactive diagram editor
- **Visual Paradigm**: Professional UML modeling

### Standards
- **UML 2.5**: Latest UML specification
- **C4 Model**: Context, containers, components, and code
- **ISO/IEC 19505**: UML specification standard
- **Color Coding**: Consistent color scheme across diagrams

## How to Use

### Viewing Diagrams
- PlantUML files (.puml) can be viewed with PlantUML viewer
- Mermaid diagrams render directly in markdown viewers
- PNG/SVG files for static viewing
- Interactive diagrams in HTML format

### Generating Diagrams
```bash
# Install PlantUML
sudo apt-get install plantuml

# Generate PNG from PlantUML
plantuml diagram.puml

# Generate SVG
plantuml -tsvg diagram.puml