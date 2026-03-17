# SMS Templates for Verification Codes

This directory contains SMS templates for various verification purposes in the Parking Management System.

## Template Categories

### Standard Verification Templates
- `verification_code.txt` - Primary template for general verification
- `verification_code_alt1.txt` - Alternative format
- `verification_code_alt2.txt` - Alternative with opt-out
- `verification_code_alt3.txt` - Compact format
- `verification_code_compact.txt` - Ultra-compact format
- `verification_code_formal.txt` - Formal business format
- `verification_code_urgent.txt` - Urgent action format
- `verification_code_emoji.txt` - Emoji-enhanced format
- `verification_code_minimal.txt` - Minimal information
- `verification_code_branded.txt` - Branded format with brackets
- `verification_code_multilingual_en_es.txt` - Bilingual (EN/ES)
- `verification_code_with_instructions.txt` - Step-by-step instructions

### Specialized Templates
- `login_code.txt` - Login verification
- `phone_verification.txt` - Phone number verification
- `password_reset_code.txt` - Password reset
- `two_factor_code.txt` - 2FA authentication
- `email_verification_code.txt` - Email verification
- `account_recovery_code.txt` - Account recovery
- `verification_code_security.txt` - Security alert

## Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{ code }}` | Verification code | 123456 |
| `{{ expires_in }}` | Expiration minutes | 10 |
| `{{ app_name }}` | Application name | ParkEase |
| `{{ user_name }}` | User's name | John |
| `{{ support_phone }}` | Support phone | +1234567890 |
| `{{ support_email }}` | Support email | support@park.com |

## Character Limits

SMS messages have strict character limits:
- **GSM 7-bit**: 160 chars (single), 153 chars (multi-part)
- **Unicode**: 70 chars (single), 67 chars (multi-part)

## Usage Examples

```python
from ..templates.sms import get_verification_template, calculate_sms_segments
from ..base import template_manager

# Render standard verification
context = {
    "code": "123456",
    "expires_in": "10",
    "app_name": "ParkEase"
}

message = template_manager.render("sms", "verification_code.txt", context)

# Check SMS segments
segments = calculate_sms_segments(message)
print(f"Characters: {segments['characters']}, Segments: {segments['segments']}")

# Smart template selection
template = get_verification_template("urgent", context)
message = template_manager.render("sms", template, context)
Best Practices
Always include expiration time

Never include sensitive data beyond the code

Include security warnings about sharing codes

Provide support contact for issues

Test character counts to avoid truncation

Use consistent branding across templates

Include opt-out instructions where appropriate

Consider international formats for phone numbers

Template Selection Logic
The get_verification_template() function automatically selects the most appropriate template based on context:

Character limits → Minimal template

High urgency → Urgent template

Enterprise users → Formal template

Multilingual → Bilingual template

Default → Standard template

text

This comprehensive SMS template collection includes:

## Key Features

### 1. **Multiple Template Variations**
- 15+ different templates for various scenarios
- Standard, alternative, compact, formal, urgent formats
- Emoji-enhanced and minimal versions
- Specialized templates for specific use cases

### 2. **Security Best Practices**
- Clear warnings about not sharing codes
- Expiration time always included
- Security alerts for suspicious activity
- Support contact information
- Opt-out instructions where appropriate

### 3. **Character Optimization**
- Templates optimized for SMS character limits
- Compact versions for constrained environments
- Segment calculation utility
- Automatic message optimization

### 4. **Specialized Use Cases**
- **Login verification** - For authentication
- **Two-factor authentication** - Extra security layer
- **Password reset** - Account recovery
- **Phone verification** - Confirming phone numbers
- **Email verification** - Email confirmation
- **Account recovery** - Regaining access
- **Security alerts** - Suspicious activity warnings

### 5. **International Support**
- Bilingual template (English/Spanish)
- Generic enough for localization
- Phone number format agnostic
- Unicode support for special characters

### 6. **Template Variables**
- `{{ code }}` - The verification code
- `{{ expires_in }}` - Expiration time in minutes
- `{{ app_name }}` - Application name for branding
- `{{ user_name }}` - Personalized greeting
- `{{ support_phone }}` - Contact number
- `{{ support_email }}` - Email support

### 7. **Utility Functions**
- **Smart template selection** based on context
- **SMS segment calculation** for billing
- **Message optimization** to fit limits
- **Encoding detection** (GSM vs Unicode)

### 8. **Format Variations**
- **Standard** - Balanced information
- **Compact** - Minimal characters
- **Formal** - Professional tone
- **Urgent** - Time-sensitive emphasis
- **Emoji** - Visual enhancement
- **Branded** - Company identification
- **Minimal** - Bare essentials

### 9. **Compliance Features**
- Expiration time for security compliance
- Opt-out instructions (reply STOP)
- Never-share warnings
- Support contact for issues
- Account compromise alerts

### 10. **Integration Ready**
- Works with template manager
- Consistent variable naming
- Easy to extend with new templates
- Documentation included

### 11. **Character Management**
- **GSM 7-bit**: 160 chars per segment
- **Unicode**: 70 chars per segment
- **Multi-part**: 153/67 chars per segment
- Automatic truncation with ellipsis

### 12. **Brand Consistency**
- App name prominently displayed
- Consistent formatting across templates
- Professional tone variations
- Security messaging consistent

# SMS Templates for Booking Confirmations

This directory contains SMS templates for booking confirmations in the Parking Management System.

## Booking Confirmation Templates

### Standard Templates
- `booking_confirmation.txt` - Primary template for standard bookings
- `booking_confirmation_detailed.txt` - Detailed information format
- `booking_confirmation_compact.txt` - Compact format for limited space
- `booking_confirmation_with_address.txt` - Includes full address
- `booking_confirmation_express.txt` - Express format for quick reading

### Specialized Booking Types
- `booking_confirmation_premium.txt` - Premium/VIP booking
- `booking_confirmation_ev.txt` - EV charging spot booking
- `booking_confirmation_monthly.txt` - Monthly pass confirmation
- `booking_confirmation_valet.txt` - Valet service booking
- `booking_confirmation_airport.txt` - Airport parking
- `booking_confirmation_event.txt` - Event parking
- `booking_confirmation_overnight.txt` - Overnight parking
- `booking_confirmation_multiple.txt` - Multiple vehicles
- `booking_confirmation_accessibility.txt` - Accessible parking
- `booking_confirmation_reservation.txt` - Reserved spot
- `booking_confirmation_instant.txt` - Instant booking
- `booking_confirmation_multilingual_en_es.txt` - Bilingual (EN/ES)

## Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{ parking_name }}` | Parking facility name | Downtown Garage |
| `{{ parking_address }}` | Full address | 123 Main St |
| `{{ spot_number }}` | Assigned spot | A42 |
| `{{ start_time }}` | Start date/time | Jan 15, 10:30 AM |
| `{{ end_time }}` | End date/time | Jan 15, 12:30 PM |
| `{{ vehicle_plate }}` | License plate | ABC-1234 |
| `{{ total_amount }}` | Total cost | $25.50 |
| `{{ currency }}` | Currency code | USD |
| `{{ booking_id }}` | Full booking ID | BK-123456 |
| `{{ booking_short_id }}` | Short booking ID | 123456 |
| `{{ qr_short_url }}` | Short URL for QR | pk.com/q/abc123 |
| `{{ support_phone }}` | Support number | +1234567890 |
| `{{ security_phone }}` | Security contact | +1234567891 |
| `{{ valet_location }}` | Valet drop-off | Main Entrance |
| `{{ valet_phone }}` | Valet contact | +1234567892 |
| `{{ event_name }}` | Event name | Concert |
| `{{ venue_name }}` | Venue name | Stadium |
| `{{ charger_type }}` | EV charger type | Level 2 |
| `{{ charger_power }}` | Charger power | 50kW |
| `{{ shuttle_info }}` | Shuttle details | Every 15min |
| `{{ entrance_location }}` | Nearest entrance | North Gate |
| `{{ assistance_phone }}` | Assistance number | +1234567893 |
| `{{ entry_code }}` | Numeric entry code | 1234# |

## Character Limits

SMS messages have strict character limits:
- **GSM 7-bit**: 160 chars (single), 153 chars (multi-part)
- **Unicode**: 70 chars (single), 67 chars (multi-part)

## Usage Examples

```python
from ..templates.sms import get_booking_template, calculate_sms_segments
from ..base import template_manager
from datetime import datetime

# Standard booking
context = {
    "parking_name": "Downtown Garage",
    "spot_number": "A42",
    "start_time": datetime(2024, 1, 15, 10, 30),
    "end_time": datetime(2024, 1, 15, 12, 30),
    "vehicle_plate": "ABC-1234",
    "total_amount": 25.50,
    "currency": "USD",
    "qr_short_url": "pk.com/q/abc123",
    "support_phone": "+1234567890"
}

# Smart template selection based on booking type
template = get_booking_template("ev" if context.get("is_ev") else "standard", context)
message = template_manager.render("sms", template, context)

# Check SMS segments
segments = calculate_sms_segments(message)
print(f"Characters: {segments['characters']}, Segments: {segments['segments']}")

# EV charging booking
ev_context = {**context, "is_ev": True, "charger_type": "Level 2", "charger_power": "50"}
ev_template = get_booking_template("ev", ev_context)
ev_message = template_manager.render("sms", ev_template, ev_context)
Template Selection Logic
The get_booking_template() function automatically selects the most appropriate template based on:

Booking Type Detection
EV Charging → EV template

Monthly Pass → Monthly template

Valet Service → Valet template

Airport Parking → Airport template

Event Parking → Event template

Overnight → Overnight template

Multiple Vehicles → Multiple template

Accessible → Accessibility template

Premium → Premium template

Context-Based Selection
Character limits → Compact template

Detailed preference → Detailed template

Express preference → Express template

Multilingual → Bilingual template

Default → Standard template

Best Practices
Include essential information - Location, spot, time, vehicle

QR code short URL - Easy access to digital pass

Support contact - For immediate assistance

Clear formatting - Use separators for readability

Test character counts - Avoid truncation

Booking-specific details - EV, valet, accessible as needed

Consistent branding - Use app name consistently

Time format clarity - Include AM/PM or 24hr format

Currency display - Clear with proper formatting

Emergency contacts - For after-hours issues

text

This comprehensive SMS booking confirmation template collection includes:

## Key Features

### 1. **Multiple Template Variations**
- 17+ different templates for various booking scenarios
- Standard, detailed, compact formats
- Specialized templates for EV, valet, airport, events
- Premium and accessible parking options

### 2. **Booking Type Support**
- **Standard parking** - Regular spot booking
- **EV charging** - Electric vehicle spots with charger details
- **Monthly passes** - Long-term parking subscriptions
- **Valet service** - Drop-off/pickup service
- **Airport parking** - With shuttle information
- **Event parking** - Venue and event details
- **Overnight** - Multi-day parking
- **Multiple vehicles** - Group bookings
- **Accessible** - ADA compliant spots
- **Premium/VIP** - Enhanced service

### 3. **Essential Information**
- Parking location and spot number
- Date and time range
- Vehicle plate number
- Total cost with currency
- QR code short URL for entry
- Support contact information
- Booking ID reference

### 4. **Specialized Details**
- **EV**: Charger type and power
- **Valet**: Drop-off location and valet contact
- **Airport**: Shuttle details
- **Event**: Event and venue names
- **Monthly**: Pass validity period
- **Accessible**: Entrance location and assistance
- **Premium**: VIP/concierge contact

### 5. **Format Optimization**
- Compact versions for limited space
- Detailed versions for comprehensive info
- Express versions for quick scanning
- Multilingual for diverse audiences

### 6. **Smart Template Selection**
- Automatic detection based on booking type
- Context-aware template selection
- Character limit optimization
- User preference integration

### 7. **Security Features**
- QR codes for secure entry
- Booking IDs for reference
- Emergency contact numbers
- Support information

### 8. **International Support**
- Bilingual template (English/Spanish)
- Flexible date/time formatting
- Currency code support
- International phone numbers

### 9. **Template Variables**
| Category | Variables |
|----------|-----------|
| **Location** | `parking_name`, `parking_address`, `spot_number` |
| **Time** | `start_time`, `end_time`, `start_date`, `end_date` |
| **Vehicle** | `vehicle_plate`, `vehicle_count` |
| **Payment** | `total_amount`, `currency` |
| **Booking** | `booking_id`, `booking_short_id` |
| **Access** | `qr_short_url`, `entry_code` |
| **Contact** | `support_phone`, `security_phone`, `assistance_phone` |
| **Special** | `charger_type`, `event_name`, `shuttle_info`, `valet_location` |

### 10. **Utility Functions**
- **Smart template selection** based on booking type
- **SMS segment calculation** for billing
- **Message optimization** to fit limits
- **Encoding detection** (GSM vs Unicode)

### 11. **Compliance Features**
- Clear booking confirmation
- Support contact always included
- Emergency numbers where applicable
- QR code for verification

### 12. **Integration Ready**
- Works with template manager
- Consistent variable naming
- Easy to extend with new templates
- Comprehensive documentation

# SMS Templates for Payment Confirmations

This directory contains SMS templates for payment confirmations in the Parking Management System.

## Payment Confirmation Templates

### Standard Templates
- `payment_success.txt` - Primary template for standard payments
- `payment_success_detailed.txt` - Detailed information format
- `payment_success_compact.txt` - Compact format for limited space
- `payment_success_express.txt` - Express format for quick reading

### Context-Specific Templates
- `payment_success_booking.txt` - Booking-related payments
- `payment_success_subscription.txt` - Subscription payments
- `payment_success_invoice.txt` - Invoice payments
- `payment_success_wallet.txt` - Wallet top-ups
- `payment_success_deposit.txt` - Security deposits
- `payment_success_refund.txt` - Refund confirmations
- `payment_success_credit.txt` - Credit applications
- `payment_success_premium.txt` - Premium membership
- `payment_success_installment.txt` - Installment payments
- `payment_success_merchant.txt` - Merchant payments

### Payment Method Specific
- `payment_success_card.txt` - Credit/debit card payments
- `payment_success_cash.txt` - Cash payments
- `payment_success_bank_transfer.txt` - Bank transfers

### Special Formats
- `payment_success_multilingual_en_es.txt` - Bilingual (EN/ES)
- `payment_success_security.txt` - Enhanced security details

## Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{ amount }}` | Payment amount | 25.50 |
| `{{ currency }}` | Currency code | USD |
| `{{ payment_method }}` | Payment method | Visa |
| `{{ payment_method_short }}` | Short method | VISA |
| `{{ payment_method_es }}` | Spanish method | Tarjeta |
| `{{ transaction_id }}` | Full transaction ID | tx_123456789 |
| `{{ transaction_short_id }}` | Short transaction ID | 123456 |
| `{{ payment_date }}` | Date/time of payment | 2024-01-15 10:30 |
| `{{ receipt_short_url }}` | Short URL for receipt | pk.com/r/abc123 |
| `{{ support_phone }}` | Support number | +1234567890 |
| `{{ booking_short_id }}` | Short booking ID | BK123 |
| `{{ booking_short_url }}` | Short booking URL | pk.com/b/abc123 |
| `{{ parking_name }}` | Parking location | Downtown Garage |
| `{{ plan_name }}` | Subscription plan | Monthly Premium |
| `{{ billing_cycle }}` | Billing cycle | month |
| `{{ next_billing_date }}` | Next billing date | Feb 15, 2024 |
| `{{ invoice_number }}` | Invoice number | INV-2024-001 |
| `{{ due_date }}` | Invoice due date | Jan 30, 2024 |
| `{{ new_balance }}` | New wallet balance | 50.00 |
| `{{ wallet_short_url }}` | Wallet URL | pk.com/w/abc123 |
| `{{ original_transaction_short }}` | Original transaction | tx_123456 |
| `{{ refund_short_id }}` | Short refund ID | ref_123456 |
| `{{ refund_timeframe }}` | Refund timing | 3-5 business days |
| `{{ account_name }}` | Account name | John Doe |
| `{{ reference_short_id }}` | Short reference | ref_123 |
| `{{ membership_level }}` | Membership level | Gold |
| `{{ valid_until }}` | Membership expiry | Dec 31, 2024 |
| `{{ concierge_phone }}` | Concierge contact | +1234567891 |
| `{{ card_brand }}` | Card brand | Visa |
| `{{ card_last4 }}` | Last 4 digits | 4242 |
| `{{ auth_code }}` | Authorization code | 123456 |
| `{{ payment_location }}` | Payment location | Main Office |
| `{{ cashier_name }}` | Cashier name | John |
| `{{ bank_reference }}` | Bank reference | BTR-123456 |
| `{{ settlement_date }}` | Settlement date | Jan 20, 2024 |
| `{{ merchant_name }}` | Merchant name | Parking Co |
| `{{ description }}` | Payment description | Monthly parking |
| `{{ merchant_reference }}` | Merchant reference | MR-123456 |
| `{{ merchant_phone }}` | Merchant phone | +1234567892 |
| `{{ installment_number }}` | Installment count | 1 |
| `{{ total_installments }}` | Total installments | 12 |
| `{{ next_payment_date }}` | Next installment | Feb 15, 2024 |

## Character Limits

SMS messages have strict character limits:
- **GSM 7-bit**: 160 chars (single), 153 chars (multi-part)
- **Unicode**: 70 chars (single), 67 chars (multi-part)

## Usage Examples

```python
from ..templates.sms import get_payment_template, calculate_sms_segments
from ..base import template_manager
from datetime import datetime

# Standard payment
context = {
    "amount": 25.50,
    "currency": "USD",
    "payment_method": "Visa •••• 4242",
    "transaction_short_id": "123456",
    "receipt_short_url": "pk.com/r/abc123",
    "support_phone": "+1234567890"
}

# Smart template selection based on payment type
template = get_payment_template("booking" if context.get("is_booking_payment") else "standard", context)
message = template_manager.render("sms", template, context)

# Check SMS segments
segments = calculate_sms_segments(message)
print(f"Characters: {segments['characters']}, Segments: {segments['segments']}")

# Booking payment
booking_context = {
    **context,
    "is_booking_payment": True,
    "booking_short_id": "BK123",
    "parking_name": "Downtown Garage",
    "booking_date": datetime(2024, 1, 15, 10, 30),
    "booking_short_url": "pk.com/b/abc123"
}
booking_template = get_payment_template("booking", booking_context)
booking_message = template_manager.render("sms", booking_template, booking_context)

# Subscription payment
subscription_context = {
    **context,
    "is_subscription": True,
    "plan_name": "Monthly Premium",
    "billing_cycle": "month",
    "next_billing_date": datetime(2024, 2, 15),
    "subscription_short_url": "pk.com/s/abc123"
}
subscription_template = get_payment_template("subscription", subscription_context)
subscription_message = template_manager.render("sms", subscription_template, subscription_context)
Template Selection Logic
The get_payment_template() function automatically selects the most appropriate template based on:

Payment Type Detection
Booking Payment → Booking template

Subscription → Subscription template

Invoice → Invoice template

Wallet Top-up → Wallet template

Deposit → Deposit template

Refund → Refund template

Credit → Credit template

Premium → Premium template

Installment → Installment template

Merchant → Merchant template

Payment Method Based
Card → Card template

Cash → Cash template

Bank Transfer → Bank transfer template

Context-Based Selection
Character limits → Compact template

Detailed preference → Detailed template

Express preference → Express template

High security → Security template

Multilingual → Bilingual template

Default → Standard template

Best Practices
Include essential information - Amount, method, reference

Receipt link - Easy access to digital receipt

Support contact - For payment issues

Clear formatting - Use separators for readability

Test character counts - Avoid truncation

Context-specific details - Booking ID, subscription info as needed

Security indicators - Verified status for high-value transactions

Time format clarity - Include date and time

Currency display - Clear with proper formatting

Short URLs - Use URL shorteners for space efficiency

text

This comprehensive SMS payment confirmation template collection includes:

## Key Features

### 1. **Multiple Template Variations**
- 20+ different templates for various payment scenarios
- Standard, detailed, compact, express formats
- Context-specific templates for different payment types
- Payment method-specific templates

### 2. **Payment Type Support**
- **Standard payments** - General payment confirmation
- **Booking payments** - Parking booking payments
- **Subscription payments** - Recurring billing
- **Invoice payments** - Bill/invoice settlements
- **Wallet top-ups** - Digital wallet funding
- **Security deposits** - Refundable deposits
- **Refunds** - Money returned to customer
- **Credit applications** - Credits applied to account
- **Premium memberships** - VIP/loyalty payments
- **Installment payments** - Partial payment plans
- **Merchant payments** - Business-to-business

### 3. **Payment Method Support**
- **Card payments** - Credit/debit cards with last 4 digits
- **Cash payments** - In-person cash transactions
- **Bank transfers** - Wire/ACH transfers

### 4. **Essential Information**
- Payment amount with currency
- Payment method details
- Transaction reference
- Date and time
- Receipt short URL
- Support contact

### 5. **Context-Specific Details**
- **Booking**: Location, booking ID, date
- **Subscription**: Plan name, next billing date
- **Invoice**: Invoice number, due date
- **Wallet**: New balance
- **Deposit**: Refundable status
- **Refund**: Original transaction, timeframe
- **Card**: Card brand, last 4 digits, auth code
- **Premium**: Membership level, expiry

### 6. **Format Optimization**
- Compact versions for limited space
- Detailed versions for comprehensive info
- Express versions for quick scanning
- Security-focused for high-value transactions
- Multilingual for diverse audiences

### 7. **Smart Template Selection**
- Automatic detection based on payment type
- Context-aware template selection
- Character limit optimization
- User preference integration
- Payment method detection

### 8. **Security Features**
- Transaction IDs for reference
- Authorization codes for verification
- Verified status indicators
- Support contact for issues
- Secure receipt URLs

### 9. **International Support**
- Bilingual template (English/Spanish)
- Flexible date/time formatting
- Currency code support
- International phone numbers

### 10. **Template Variables**
| Category | Variables |
|----------|-----------|
| **Payment** | `amount`, `currency`, `payment_method`, `transaction_id` |
| **Receipt** | `receipt_short_url`, `receipt_number` |
| **Time** | `payment_date`, `due_date`, `next_billing_date` |
| **Contact** | `support_phone`, `merchant_phone`, `concierge_phone` |
| **Booking** | `booking_short_id`, `parking_name`, `booking_short_url` |
| **Subscription** | `plan_name`, `billing_cycle`, `subscription_short_url` |
| **Wallet** | `new_balance`, `wallet_short_url` |
| **Card** | `card_brand`, `card_last4`, `auth_code` |
| **Refund** | `original_transaction_short`, `refund_short_id` |
| **Premium** | `membership_level`, `valid_until` |

### 11. **Utility Functions**
- **Smart template selection** based on payment type
- **SMS segment calculation** for billing
- **Message optimization** to fit limits
- **Encoding detection** (GSM vs Unicode)

### 12. **Compliance Features**
- Clear payment confirmation
- Transaction references for tracking
- Support contact always included
- Receipt URLs for documentation
- Security verification where needed

### 13. **Integration Ready**
- Works with template manager
- Consistent variable naming
- Easy to extend with new templates
- Comprehensive documentation