
## 8. **reports.md** - Reports API

```markdown
# Reports API

## Overview
Generate and retrieve various reports for business intelligence, analytics, and operational insights.

## Endpoints

### Get Occupancy Report
Get parking occupancy report.

**GET** `/reports/occupancy`

**Query Parameters:**
- `parking_lot_id` (string) - Filter by parking lot
- `period` (string) - Time period (today, yesterday, last_7_days, last_30_days, custom)
- `start_date` (string) - Start date for custom period (YYYY-MM-DD)
- `end_date` (string) - End date for custom period (YYYY-MM-DD)
- `granularity` (string) - hourly, daily, weekly, monthly
- `slot_type` (string) - Filter by slot type
- `format` (string) - json, csv, pdf

**Response:**
```json
{
  "success": true,
  "data": {
    "report": {
      "title": "Parking Occupancy Report",
      "period": "2024-01-01 to 2024-01-10",
      "generated_at": "2024-01-10T10:30:00Z",
      "summary": {
        "total_slots": 500,
        "average_occupancy_rate": 0.72,
        "peak_occupancy_rate": 0.95,
        "peak_time": "2024-01-09T17:00:00Z",
        "total_vehicle_count": 8420,
        "average_duration": "2.3 hours"
      },
      "daily_data": [
        {
          "date": "2024-01-01",
          "total_vehicles": 750,
          "average_occupancy": 0.65,
          "peak_occupancy": 0.85,
          "peak_hour": "08:00-09:00",
          "revenue": 5625.00
        },
        {
          "date": "2024-01-02",
          "total_vehicles": 820,
          "average_occupancy": 0.68,
          "peak_occupancy": 0.90,
          "peak_hour": "17:00-18:00",
          "revenue": 6150.00
        }
      ],
      "hourly_average": [
        {"hour": "00:00", "occupancy": 0.15},
        {"hour": "01:00", "occupancy": 0.12},
        {"hour": "08:00", "occupancy": 0.85},
        {"hour": "17:00", "occupancy": 0.90},
        {"hour": "23:00", "occupancy": 0.20}
      ],
      "by_slot_type": {
        "regular": {"average_occupancy": 0.75, "peak_occupancy": 0.98},
        "premium": {"average_occupancy": 0.65, "peak_occupancy": 0.85},
        "ev": {"average_occupancy": 0.45, "peak_occupancy": 0.70}
      },
      "recommendations": [
        "Increase EV slots by 10% based on growing demand",
        "Consider dynamic pricing during peak hours",
        "Add more premium slots in Zone A"
      ]
    }
  }
}