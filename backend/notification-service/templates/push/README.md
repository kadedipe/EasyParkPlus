# Push Notification Templates

This directory contains push notification templates for various notification types in the Parking Management System.

## Available Templates

### Booking Confirmation Templates
- `booking_confirmation.json` - Standard booking confirmation
- `booking_confirmation_rich.json` - Rich format with images and actions
- `booking_confirmation_minimal.json` - Minimal format for limited bandwidth
- `booking_confirmation_with_timer.json` - Timer-based format with countdown

## Template Variables

### Common Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `{{ parking_name }}` | Parking facility name | Downtown Garage |
| `{{ spot_number }}` | Assigned spot | A42 |
| `{{ start_time }}` | Start date/time | 2024-01-15T10:30:00 |
| `{{ end_time }}` | End date/time | 2024-01-15T12:30:00 |
| `{{ vehicle_plate }}` | License plate | ABC-1234 |
| `{{ total_amount }}` | Total cost | 25.50 |
| `{{ currency }}` | Currency code | USD |
| `{{ booking_id }}` | Booking ID | bk_123456789 |
| `{{ booking_reference }}` | Short reference | BK123 |
| `{{ app_url }}` | Application URL | https://parking.com |
| `{{ app_scheme }}` | App deep link scheme | parkingapp:// |
| `{{ image_url }}` | CDN image URL | https://cdn.parking.com |
| `{{ current_time }}` | Current timestamp | 2024-01-15T10:30:00 |
| `{{ time_until_start }}` | Human-readable time | 2 hours |
| `{{ duration }}` | Booking duration | 2 hours |
| `{{ duration_minutes }}` | Duration in minutes | 120 |

### Rich Template Variables
| Variable | Description |
|----------|-------------|
| `{{ parking_address }}` | Full address |
| `{{ spot_type }}` | Type of spot (standard, EV, accessible) |
| `{{ vehicle_model }}` | Vehicle model |
| `{{ payment_method }}` | Payment method used |
| `{{ transaction_id }}` | Transaction ID |
| `{{ qr_data }}` | QR code data |
| `{{ qr_code_url }}` | QR code image URL |
| `{{ map_link }}` | Map link to location |
| `{{ directions_link }}` | Driving directions link |

## Platform Support

### Android
- Priority levels (high, normal)
- Custom sound and vibration
- Channel ID for grouping
- Large icons and images
- Progress indicators
- Chronometer for time-based notifications
- Big picture style for rich content

### iOS (APNS)
- Alert customization (title, body, subtitle)
- Custom sounds
- Badge count
- Category for actions
- Thread ID for grouping
- Time-sensitive interruption level
- Critical alerts with volume control
- Mutable content for custom UI

### Web (Web Push)
- Icons and badges
- Action buttons
- Image support
- Vibration pattern
- Require interaction option
- Custom data payloads
- Deep linking

## Action Types

### Available Actions
- `view` - View booking details
- `view_booking` - Alternative view action
- `show_qr` - Display QR code for entry
- `cancel` - Cancel booking
- `extend` - Extend booking duration
- `get_directions` - Get directions to location
- `directions` - Alternative directions action
- `qr` - Show QR code (web)

### Action Properties
- `id` - Unique action identifier
- `title` - Display text
- `icon` - Icon URL (web) or icon name (native)
- `url` - URL to open (web)
- `authentication_required` - Requires user authentication
- `destructive` - Destructive action (Android)

## Platform-Specific Features

### Android
```json
{
  "android": {
    "priority": "high",
    "notification": {
      "channel_id": "booking_notifications",
      "color": "#059669",
      "icon": "@drawable/ic_notification",
      "vibrate": [200, 100, 200],
      "uses_chronometer": true,
      "when": "{{ start_time.timestamp() }}",
      "progress": {
        "max": 100,
        "progress": 0
      }
    }
  }
}
iOS (APNS)
json
{
  "apns": {
    "payload": {
      "aps": {
        "alert": {
          "title": "Booking Confirmed!",
          "body": "Your parking is confirmed",
          "subtitle": "Spot A42"
        },
        "sound": "default",
        "badge": 1,
        "interruption-level": "time-sensitive",
        "relevance-score": 1.0
      }
    },
    "headers": {
      "apns-priority": "10",
      "apns-push-type": "alert"
    }
  }
}
Web Push
json
{
  "webpush": {
    "notification": {
      "title": "Booking Confirmed!",
      "body": "Your parking is confirmed",
      "icon": "/icons/icon-192.png",
      "badge": "/icons/badge-72.png",
      "vibrate": [200, 100, 200],
      "actions": [
        {"action": "view", "title": "View Booking"},
        {"action": "cancel", "title": "Cancel"}
      ]
    },
    "fcm_options": {
      "link": "https://parking.com/bookings/123"
    }
  }
}
Usage Examples
python
from ..templates.push import render_push_notification, validate_push_payload
from datetime import datetime

# Context data
context = {
    "parking_name": "Downtown Garage",
    "spot_number": "A42",
    "vehicle_plate": "ABC-1234",
    "start_time": datetime(2024, 1, 15, 10, 30),
    "end_time": datetime(2024, 1, 15, 12, 30),
    "total_amount": 25.50,
    "currency": "USD",
    "booking_id": "bk_123456789",
    "app_url": "https://parking.com",
    "image_url": "https://cdn.parking.com"
}

# Render for Android
android_payload = render_push_notification(
    "booking_confirmation",
    context,
    platform="android"
)

# Render for iOS
ios_payload = render_push_notification(
    "booking_confirmation",
    context,
    platform="ios"
)

# Render for Web
web_payload = render_push_notification(
    "booking_confirmation",
    context,
    platform="web"
)

# Render rich version for premium users
if context.get("is_premium"):
    rich_payload = render_push_notification(
        "booking_confirmation_rich",
        context
    )

# Validate payload
validation = validate_push_payload(rich_payload)
if not validation["valid"]:
    print(f"Validation errors: {validation['errors']}")
Template Selection Logic
The get_push_template() function automatically selects the appropriate template based on:

Context-Based Selection
Premium users → Rich template

Time-sensitive → Timer template (if start time < 1 hour)

Low bandwidth → Minimal template

Platform specific → Platform-optimized template

Platform-Specific Optimization
Android: Uses channel IDs, vibration patterns, colors

iOS: Uses interruption levels, critical alerts, categories

Web: Uses actions, icons, deep linking

Best Practices
Keep titles short - Maximum 50 characters for Android/iOS

Include action buttons - Provide quick actions

Use deep links - Deep link to relevant content

Set appropriate priority - Use high priority for time-sensitive notifications

Include images - Rich media improves engagement

Test on all platforms - Ensure compatibility

Respect platform limits - Stay within payload size limits (4KB for Android, 2KB for iOS)

Use proper channels - Categorize notifications on Android

Handle user actions - Implement action handlers

Track analytics - Add analytics labels for tracking

Payload Size Limits
Android FCM: 4KB for notification messages, 4KB for data messages

iOS APNS: 4KB for notifications, 2KB for Safari Push

Web Push: 4KB for web push notifications

Error Handling
python
try:
    payload = render_push_notification("booking_confirmation", context)
    validation = validate_push_payload(payload)
    
    if not validation["valid"]:
        # Fall back to minimal template
        payload = render_push_notification("booking_confirmation_minimal", context)
    
except Exception as e:
    # Use fallback payload
    payload = {
        "title": "Booking Confirmed",
        "body": f"Your parking at {context.get('parking_name')} is confirmed",
        "data": {"type": "booking_confirmation"}
    }
Testing
Test Payload Validation
python
from . import validate_push_payload

test_payload = {
    "title": "Test",
    "body": "Test body",
    "data": {"key": "value"}
}

result = validate_push_payload(test_payload)
assert result["valid"] is True
Platform-Specific Testing
Android: Test on different Android versions (8.0+)

iOS: Test on different iOS versions (13.0+)

Web: Test on Chrome, Firefox, Safari, Edge

Analytics
Add analytics tracking to push notifications:

json
{
  "android": {
    "fcm_options": {
      "analytics_label": "booking_confirmation_android"
    }
  },
  "apns": {
    "fcm_options": {
      "analytics_label": "booking_confirmation_ios"
    }
  },
  "webpush": {
    "fcm_options": {
      "analytics_label": "booking_confirmation_web"
    }
  }
}
Security Considerations
Never include sensitive data in notification payloads

Use authentication_required for sensitive actions

Validate user authentication before performing actions

Use HTTPS for all URLs and images

Implement rate limiting for action handlers

Sanitize all user input in templates

# Push Notification Templates - Payment Success

This directory contains push notification templates for payment success notifications in the Parking Management System.

## Payment Templates

### Standard Templates
- `payment_success.json` - Standard payment confirmation
- `payment_success_rich.json` - Rich format with images and detailed information
- `payment_success_minimal.json` - Minimal format for limited bandwidth
- `payment_success_subscription.json` - Subscription-specific payment confirmation

## Template Variables

### Payment-Specific Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `{{ payment_id }}` | Unique payment ID | pay_123456789 |
| `{{ transaction_id }}` | Full transaction ID | tx_123456789 |
| `{{ transaction_short_id }}` | Short transaction ID | 123456 |
| `{{ amount }}` | Payment amount | 25.50 |
| `{{ currency }}` | Currency code | USD |
| `{{ payment_method }}` | Payment method name | Visa •••• 4242 |
| `{{ payment_method_details }}` | Detailed method info | Visa ending in 4242 |
| `{{ payment_method_icon }}` | Method icon URL | https://cdn.parking.com/icons/visa.png |
| `{{ payment_date }}` | Payment date/time | 2024-01-15T10:30:00 |
| `{{ auth_code }}` | Authorization code | AUTH123456 |
| `{{ receipt_url }}` | Full receipt URL | https://parking.com/receipt/123 |
| `{{ receipt_pdf_url }}` | PDF receipt URL | https://parking.com/receipt/123.pdf |
| `{{ receipt_short_url }}` | Shortened receipt URL | pk.com/r/abc123 |
| `{{ invoice_url }}` | Invoice URL | https://parking.com/invoice/123 |
| `{{ invoice_number }}` | Invoice number | INV-2024-001 |
| `{{ booking_id }}` | Associated booking ID | bk_123456789 |
| `{{ parking_name }}` | Parking location | Downtown Garage |
| `{{ spot_number }}` | Parking spot | A42 |
| `{{ start_time }}` | Booking start time | 2024-01-15T10:30:00 |
| `{{ end_time }}` | Booking end time | 2024-01-15T12:30:00 |
| `{{ duration }}` | Booking duration | 2 hours |
| `{{ new_balance }}` | New wallet balance | 50.00 |
| `{{ rewards_points }}` | Rewards points earned | 25 |
| `{{ tax_amount }}` | Tax amount | 2.50 |
| `{{ fee_amount }}` | Processing fee | 1.00 |
| `{{ discount_amount }}` | Discount applied | 5.00 |

### Subscription Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `{{ subscription_id }}` | Subscription ID | sub_123456789 |
| `{{ plan_name }}` | Subscription plan | Monthly Premium |
| `{{ plan_id }}` | Plan ID | plan_monthly_premium |
| `{{ billing_cycle }}` | Billing cycle | month |
| `{{ next_billing_date }}` | Next billing date | 2024-02-15 |

## Platform-Specific Features

### Android
```json
{
  "android": {
    "priority": "high",
    "notification": {
      "channel_id": "payment_notifications",
      "color": "#10B981",
      "icon": "@drawable/ic_payment_success",
      "big_text": "Detailed payment information...",
      "inbox": ["Line 1", "Line 2"]
    }
  }
}
iOS (APNS)
json
{
  "apns": {
    "payload": {
      "aps": {
        "alert": {
          "title": "Payment Successful!",
          "body": "Your payment was processed",
          "subtitle": "Transaction 123456"
        },
        "sound": "payment_success.caf",
        "interruption-level": "time-sensitive"
      }
    }
  }
}
Web Push
json
{
  "webpush": {
    "notification": {
      "title": "💰 Payment Successful!",
      "body": "Your payment was processed",
      "image": "https://cdn.parking.com/payment_banner.jpg",
      "actions": [
        {"action": "view_receipt", "title": "View Receipt"},
        {"action": "download_pdf", "title": "Download PDF"}
      ]
    }
  }
}
Usage Examples
python
from ..templates.push import render_payment_push
from datetime import datetime

# Context for standard payment
context = {
    "payment_id": "pay_123456789",
    "transaction_short_id": "123456",
    "amount": 25.50,
    "currency": "USD",
    "payment_method": "Visa •••• 4242",
    "payment_date": datetime(2024, 1, 15, 10, 30),
    "receipt_short_url": "pk.com/r/abc123",
    "app_url": "https://parking.com",
    "app_scheme": "parkingapp"
}

# Render for Android
android_payload = render_payment_push(context, platform="android")

# Render for iOS
ios_payload = render_payment_push(context, platform="ios")

# Render for Web
web_payload = render_payment_push(context, platform="web")

# Render rich version for premium user
premium_context = {**context, "is_premium": True, "rewards_points": 25}
rich_payload = render_payment_push(premium_context)

# Render subscription payment
subscription_context = {
    **context,
    "is_subscription": True,
    "plan_name": "Monthly Premium",
    "subscription_id": "sub_123456789",
    "next_billing_date": datetime(2024, 2, 15)
}
subscription_payload = render_payment_push(subscription_context)

# Validate payload
from . import validate_push_payload
validation = validate_push_payload(android_payload)
if validation["valid"]:
    print("Payload is valid")
else:
    print(f"Validation errors: {validation['errors']}")
Payment Status Icons
Status	Icon	Description
Success	💰	Payment successful
Failed	❌	Payment failed
Pending	⏳	Payment pending
Refunded	↩️	Payment refunded
Subscription	🔄	Subscription renewal
Best Practices
Security
Never include full credit card numbers - Use masked format (•••• 4242)

Include transaction IDs for reference

Provide receipt links for documentation

Use HTTPS for all URLs

Validate authentication before action execution

User Experience
Clear amount display with currency

Payment method visibility - Show how user paid

Action buttons - Provide quick access to receipt and details

Timestamp - Show when payment occurred

Contextual information - Include booking details if applicable

Performance
Optimize image sizes - Use appropriate dimensions for each platform

Short URLs - Use URL shorteners for space efficiency

Minimal payload - Stay within size limits (4KB Android, 2KB iOS)

Lazy loading - Don't pre-load heavy assets

Analytics
Add analytics labels - Track engagement per platform

Track action clicks - Monitor user interactions

Measure conversion - Track receipt views and downloads

Platform tracking - Separate metrics by platform

Error Handling
python
try:
    payload = render_payment_push(context)
    validation = validate_push_payload(payload)
    
    if not validation["valid"]:
        # Fall back to minimal template
        payload = render_payment_push(
            context, 
            platform="all"
        )
        
except Exception as e:
    # Ultimate fallback
    payload = {
        "title": "Payment Update",
        "body": f"Payment of {context.get('amount')} {context.get('currency')}",
        "data": {"type": "payment"}
    }
Testing
python
# Test payload validation
def test_payment_push_validation():
    from . import validate_push_payload
    
    valid_payload = {
        "title": "Test",
        "body": "Test body",
        "data": {"type": "payment_success"}
    }
    
    result = validate_push_payload(valid_payload)
    assert result["valid"] is True
    assert len(result["errors"]) == 0

# Test template rendering
def test_payment_template_rendering():
    context = {
        "amount": 25.50,
        "currency": "USD",
        "payment_method": "Visa",
        "payment_id": "pay_123"
    }
    
    payload = render_payment_push(context)
    assert "title" in payload
    assert "body" in payload
    assert "data" in payload
    assert payload["data"]["type"] == "payment_success"
Security Considerations
No sensitive data in notification payloads

Receipt URLs should require authentication

Transaction IDs are safe to include

Use short-lived tokens for deep links

Implement rate limiting on action handlers

Validate user session before processing actions

# Push Notification Templates - Welcome

This directory contains push notification templates for welcoming new users in the Parking Management System.

## Welcome Templates

### Standard Templates
- `welcome.json` - Standard welcome notification
- `welcome_rich.json` - Rich format with bonus offers and multiple actions
- `welcome_minimal.json` - Minimal format for basic welcome
- `welcome_bonus.json` - Bonus-focused welcome with claim action
- `welcome_tips.json` - Tips and tricks for new users

## Template Variables

### Welcome-Specific Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `{{ user_id }}` | Unique user ID | usr_123456789 |
| `{{ user_name }}` | User's name | John Doe |
| `{{ user_email }}` | User's email | john@example.com |
| `{{ welcome_bonus }}` | Welcome bonus amount | 10 |
| `{{ currency }}` | Currency code | USD |
| `{{ welcome_code }}` | Welcome bonus code | WELCOME2024 |
| `{{ referral_code }}` | User's referral code | JOHN123 |
| `{{ bonus_expiry }}` | Bonus expiration date | 2024-02-15 |
| `{{ onboarding_completed }}` | Onboarding status | false |
| `{{ app_url }}` | Application URL | https://parking.com |
| `{{ app_scheme }}` | App deep link scheme | parkingapp:// |
| `{{ image_url }}` | CDN image URL | https://cdn.parking.com |
| `{{ current_time }}` | Current timestamp | 2024-01-15T10:30:00 |

### Onboarding Steps
| Step | Description |
|------|-------------|
| complete_profile | Complete user profile |
| add_vehicle | Add vehicle details |
| find_parking | Find and book parking |
| invite_friends | Invite friends |

## Platform-Specific Features

### Android
```json
{
  "android": {
    "priority": "high",
    "notification": {
      "channel_id": "welcome_notifications",
      "color": "#667EEA",
      "icon": "@drawable/ic_welcome",
      "big_text": "Welcome message with details...",
      "inbox": ["Tip 1", "Tip 2", "Tip 3"],
      "progress": {
        "max": 100,
        "progress": 0
      }
    }
  }
}
iOS (APNS)
json
{
  "apns": {
    "payload": {
      "aps": {
        "alert": {
          "title": "Welcome!",
          "body": "Thanks for joining",
          "subtitle": "Complete your profile"
        },
        "sound": "welcome.caf",
        "badge": 1,
        "interruption-level": "active"
      }
    }
  }
}
Web Push
json
{
  "webpush": {
    "notification": {
      "title": "🎉 Welcome!",
      "body": "Thanks for joining!",
      "image": "https://cdn.parking.com/welcome_banner.jpg",
      "actions": [
        {"action": "get_started", "title": "Get Started"},
        {"action": "invite", "title": "Invite Friends"}
      ]
    }
  }
}
Usage Examples
python
from ..templates.push import render_welcome_push
from datetime import datetime

# Context for new user with welcome bonus
context = {
    "user_id": "usr_123456789",
    "user_name": "John Doe",
    "user_email": "john@example.com",
    "welcome_bonus": 10,
    "currency": "USD",
    "welcome_code": "WELCOME2024",
    "referral_code": "JOHN123",
    "app_url": "https://parking.com",
    "app_scheme": "parkingapp",
    "image_url": "https://cdn.parking.com",
    "current_time": datetime(2024, 1, 15, 10, 30)
}

# Render welcome notification
payload = render_welcome_push(context)

# Render for specific platform
android_payload = render_welcome_push(context, platform="android")
ios_payload = render_welcome_push(context, platform="ios")
web_payload = render_welcome_push(context, platform="web")

# Render rich version for premium bonus
premium_context = {**context, "has_welcome_bonus": True, "welcome_bonus": 25}
rich_payload = render_welcome_push(premium_context)

# Validate payload
from . import validate_push_payload
validation = validate_push_payload(payload)
if validation["valid"]:
    print("Payload is valid")
else:
    print(f"Validation errors: {validation['errors']}")
Welcome Journey
First-Time Users
Welcome Notification - Greet user and introduce app

Bonus Offer - Incentivize profile completion

Onboarding Tips - Guide user through features

First Booking - Encourage first parking booking

Action Buttons
Action	Purpose
Get Started	Start onboarding process
Complete Profile	Fill user profile information
Add Vehicle	Register vehicle details
Find Parking	Search for available parking
Invite Friends	Share referral link
Claim Bonus	Collect welcome bonus
View Tips	See pro tips and tricks
Best Practices
Personalization
Use user's name - Personalize welcome message

Highlight bonus - Emphasize welcome bonus value

Clear next steps - Guide user through onboarding

Action buttons - Provide easy access to key features

Engagement
Timely delivery - Send immediately after registration

Bonus incentive - Encourage profile completion

Multiple actions - Offer various engagement options

Social sharing - Include invite friends option

Platform Optimization
Rich content - Use images for better engagement

Action buttons - Platform-appropriate actions

Notification channels - Proper categorization

Sound effects - Welcoming notification sounds

Analytics
Track opens - Monitor notification engagement

Action clicks - Track which actions users take

Conversion rate - Measure onboarding completion

Bonus claims - Track bonus redemption rate

Security Considerations
No sensitive data in notification payloads

Referral codes are safe to share

Bonus codes should have expiration

Validate user before processing actions

Rate limit action handlers

A/B Testing Suggestions
Test Variations
Title length - Short vs descriptive

Bonus amount - Different bonus values

Action buttons - 2 vs 4 actions

Rich media - With/without images

Delivery timing - Immediate vs delayed

Success Metrics
Open rate - Percentage of delivered notifications opened

Action rate - Percentage of users who take action

Onboarding completion - Profile completion rate

First booking - Time to first parking booking

Referral rate - Number of invites sent