
## 9. **webhooks.md** - Webhooks API

```markdown
# Webhooks API

## Overview
Webhooks allow you to receive real-time notifications when events occur in the parking system. Configure webhook endpoints to receive HTTP POST requests with event data.

## Events

### Available Events

#### Parking Lot Events
- `parking_lot.created` - New parking lot created
- `parking_lot.updated` - Parking lot details updated
- `parking_lot.deleted` - Parking lot deleted
- `parking_lot.status_changed` - Parking lot status changed
- `occupancy.threshold_reached` - Occupancy threshold reached (e.g., 80% full)
- `occupancy.low` - Occupancy below threshold (e.g., 20% full)

#### Slot Events
- `slot.created` - New parking slot created
- `slot.updated` - Slot details updated
- `slot.status_changed` - Slot status changed
- `slot.reserved` - Slot reserved for future use
- `slot.occupied` - Slot occupied by vehicle
- `slot.vacated` - Slot vacated by vehicle
- `slot.maintenance_scheduled` - Maintenance scheduled for slot
- `slot.maintenance_completed` - Maintenance completed on slot

#### Session Events
- `session.created` - New parking session created (vehicle entered)
- `session.updated` - Session updated
- `session.completed` - Session completed (vehicle exited)
- `session.extended` - Session extended
- `session.cancelled` - Session cancelled
- `session.overstayed` - Vehicle overstayed allowed time
- `session.grace_period_ending` - Grace period ending soon
- `session.payment_required` - Payment required for session

#### Payment Events
- `payment.created` - New payment created
- `payment.succeeded` - Payment successfully completed
- `payment.failed` - Payment failed
- `payment.refunded` - Payment refunded
- `invoice.generated` - Invoice generated
- `invoice.paid` - Invoice paid
- `receipt.sent` - Receipt sent to customer
- `refund.processed` - Refund processed

#### Customer Events
- `customer.created` - New customer registered
- `customer.updated` - Customer profile updated
- `customer.verified` - Customer email verified
- `customer.suspended` - Customer account suspended
- `customer.deleted` - Customer account deleted
- `vehicle.added` - Vehicle added to customer
- `vehicle.removed` - Vehicle removed from customer
- `loyalty.points_earned` - Loyalty points earned
- `loyalty.tier_upgraded` - Loyalty tier upgraded
- `monthly_pass.purchased` - Monthly pass purchased
- `monthly_pass.expiring` - Monthly pass expiring soon
- `monthly_pass.renewed` - Monthly pass renewed

#### System Events
- `system.maintenance.scheduled` - System maintenance scheduled
- `system.maintenance.completed` - System maintenance completed
- `system.error` - System error occurred
- `api.limit.approaching` - API rate limit approaching
- `api.limit.exceeded` - API rate limit exceeded

## Endpoints

### Create Webhook
Create a new webhook endpoint.

**POST** `/webhooks`

**Request Body:**
```json
{
  "name": "Production Webhook",
  "url": "https://your-server.com/webhooks/parking",
  "events": [
    "session.created",
    "session.completed",
    "payment.succeeded",
    "payment.failed"
  ],
  "secret": "your_webhook_secret_here",
  "enabled": true,
  "retry_policy": {
    "max_attempts": 3,
    "retry_delay": 60,
    "backoff_multiplier": 2
  },
  "headers": {
    "X-Custom-Header": "CustomValue"
  },
  "metadata": {
    "environment": "production",
    "team": "operations"
  }
}