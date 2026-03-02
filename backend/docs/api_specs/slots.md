
## 5. **slots.md** - Parking Slots API

```markdown
# Parking Slots API

## Overview
Manage individual parking slots within parking lots, including slot configuration, status, and maintenance.

## Endpoints

### List Slots
Get all parking slots for a parking lot.

**GET** `/parking-lots/{lot_id}/slots`

**Query Parameters:**
- `status` (string) - Filter by status (available, occupied, reserved, maintenance)
- `slot_type` (string) - Filter by slot type (regular, premium, ev, disabled)
- `floor` (string) - Filter by floor level
- `zone` (string) - Filter by zone
- `page` (integer) - Page number
- `limit` (integer) - Items per page
- `sort_by` (string) - Sort field (number, floor, zone)

**Response:**
```json
{
  "success": true,
  "data": {
    "slots": [
      {
        "id": "slot_123456789",
        "parking_lot_id": "lot_123456789",
        "slot_number": "A-15",
        "slot_type": "regular",
        "status": "available",
        "floor": "B1",
        "zone": "A",
        "dimensions": {
          "length": 5.0,
          "width": 2.5,
          "height": 2.2
        },
        "features": ["lighting", "security_camera"],
        "hourly_rate": 5.0,
        "current_session": null,
        "last_occupied": "2024-01-09T18:30:00Z",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-10T10:30:00Z"
      },
      {
        "id": "slot_987654321",
        "parking_lot_id": "lot_123456789",
        "slot_number": "P-01",
        "slot_type": "premium",
        "status": "occupied",
        "floor": "B1",
        "zone": "P",
        "dimensions": {
          "length": 5.5,
          "width": 2.8,
          "height": 2.5
        },
        "features": ["lighting", "security_camera", "covered"],
        "hourly_rate": 8.0,
        "current_session": {
          "session_id": "sess_123456789",
          "license_plate": "ABC123",
          "entry_time": "2024-01-10T08:30:00Z"
        },
        "last_occupied": null,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-10T08:30:00Z"
      }
    ],
    "summary": {
      "total": 500,
      "available": 150,
      "occupied": 350,
      "maintenance": 0,
      "reserved": 0
    },
    "pagination": {
      "total": 500,
      "page": 1,
      "limit": 20,
      "total_pages": 25
    }
  }
}