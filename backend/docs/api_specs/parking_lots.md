
## 3. **parking_lots.md** - Parking Lots API

```markdown
# Parking Lots API

## Overview
Manage parking lots, including creation, configuration, and real-time status monitoring.

## Endpoints

### List Parking Lots
Retrieve a list of parking lots.

**GET** `/parking-lots`

**Query Parameters:**
- `page` (integer, default: 1) - Page number
- `limit` (integer, default: 20, max: 100) - Items per page
- `status` (string) - Filter by status (active, inactive, maintenance)
- `type` (string) - Filter by type (indoor, outdoor, multi_level)
- `sort_by` (string) - Sort field (name, created_at, capacity)
- `sort_order` (string) - Sort order (asc, desc)

**Response:**
```json
{
  "success": true,
  "data": {
    "parking_lots": [
      {
        "id": "lot_123456789",
        "name": "Downtown Parking",
        "address": {
          "street": "123 Main St",
          "city": "New York",
          "state": "NY",
          "postal_code": "10001",
          "country": "USA"
        },
        "total_slots": 500,
        "available_slots": 150,
        "occupied_slots": 350,
        "hourly_rate": 5.0,
        "daily_rate": 40.0,
        "monthly_rate": 300.0,
        "slot_types": {
          "regular": 400,
          "premium": 80,
          "ev": 20
        },
        "operating_hours": {
          "monday": {"open": "06:00", "close": "22:00"},
          "tuesday": {"open": "06:00", "close": "22:00"},
          "wednesday": {"open": "06:00", "close": "22:00"},
          "thursday": {"open": "06:00", "close": "22:00"},
          "friday": {"open": "06:00", "close": "23:00"},
          "saturday": {"open": "08:00", "close": "23:00"},
          "sunday": {"open": "08:00", "close": "21:00"}
        },
        "features": ["security_cameras", "ev_charging", "valet", "car_wash"],
        "status": "active",
        "created_at": "2024-01-10T10:30:00Z",
        "updated_at": "2024-01-10T10:30:00Z"
      }
    ],
    "pagination": {
      "total": 1,
      "page": 1,
      "limit": 20,
      "total_pages": 1
    }
  }
}