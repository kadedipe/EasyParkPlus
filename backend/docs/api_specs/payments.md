
## 6. **payments.md** - Payments API

```markdown
# Payments API

## Overview
Handle payment processing, invoices, refunds, and payment methods for parking services.

## Endpoints

### Process Payment
Process a payment for a parking session or invoice.

**POST** `/payments/process`

**Request Body:**
```json
{
  "session_id": "sess_123456789",
  "amount": 17.55,
  "currency": "USD",
  "payment_method": "credit_card",
  "payment_details": {
    "card_number": "4242424242424242",
    "exp_month": "12",
    "exp_year": "2025",
    "cvc": "123",
    "cardholder_name": "John Doe"
  },
  "customer_email": "john@example.com",
  "send_receipt": true
}