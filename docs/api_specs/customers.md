
## 7. **customers.md** - Customers API

```markdown
# Customers API

## Overview
Manage customer accounts, profiles, preferences, and loyalty programs.

## Endpoints

### Create Customer Account
Register a new customer.

**POST** `/customers`

**Request Body:**
```json
{
  "email": "john.doe@example.com",
  "password": "securePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1-555-0123",
  "date_of_birth": "1990-01-01",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "USA"
  },
  "preferences": {
    "language": "en",
    "currency": "USD",
    "notifications": {
      "email": true,
      "sms": false,
      "push": true
    },
    "default_vehicle_type": "car",
    "preferred_slot_type": "regular"
  },
  "marketing_consent": true
}