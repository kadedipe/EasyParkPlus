
## 3. **domain_model.md** - Domain Model

```markdown
# Domain Model

## Overview

This document defines the core domain model for the Parking Management System. The domain model represents the business entities, their relationships, and the business rules that govern them.

## Core Concepts

### Bounded Contexts

The system is divided into the following bounded contexts:

1. **Parking Management Context**: Core parking operations
2. **Customer Management Context**: Customer profiles and relationships
3. **Payment & Billing Context**: Financial transactions
4. **IoT & Devices Context**: Physical device management
5. **Analytics & Reporting Context**: Business intelligence

## Core Entities

### 1. ParkingLot

**Description**: Represents a physical parking facility with multiple parking slots.

**Attributes**:
```yaml
id: UUID
name: String
address: Address
total_slots: Integer
available_slots: Integer
hourly_rate: Decimal
daily_rate: Decimal
monthly_rate: Decimal
slot_types: Map<SlotType, Integer>
operating_hours: Map<DayOfWeek, TimeRange>
features: List<Feature>
status: ParkingLotStatus
coordinates: GeoPoint
contact_info: ContactInfo
created_at: DateTime
updated_at: DateTime