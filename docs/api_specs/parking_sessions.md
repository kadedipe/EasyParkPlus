
## 4. **parking_sessions.md** - Parking Sessions API

```markdown
# Parking Sessions API

## Overview
Manage vehicle entry, exit, and active parking sessions.

## Endpoints

### Check Vehicle In
Register a vehicle entry.

**POST** `/parking-sessions/check-in`

**Request Body:**
```json
{
  "parking_lot_id": "lot_123456789",
  "license_plate": "ABC123",
  "vehicle_type": "car",
  "slot_type_preference": "regular",
  "vehicle_details": {
    "make": "Toyota",
    "model": "Camry",
    "color": "Blue"
  },
  "driver_details": {
    "name": "John Doe",
    "phone": "+1-555-0123",
    "email": "john@example.com"
  },
  "payment_method": "credit_card",
  "is_monthly_pass": false
}