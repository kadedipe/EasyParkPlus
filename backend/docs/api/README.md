# Parking Management System API Documentation

## Overview
The Parking Management System API provides a comprehensive set of endpoints for managing parking facilities, reservations, payments, and user accounts.

**Base URL**: `https://api.parking-management.com/api/v1`

## Authentication
Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:
Authorization: Bearer <your-jwt-token>

text

## API Response Format
All API responses follow a consistent format:

### Success Response
```json
{
  "status": "success",
  "data": {
    // Response data
  },
  "message": "Optional success message"
}
Error Response
json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {} // Optional additional details
  }
}
Rate Limiting
API requests are limited to 100 requests per minute per IP

Authentication endpoints are limited to 10 requests per minute

Rate limit headers are included in all responses:

X-RateLimit-Limit

X-RateLimit-Remaining

X-RateLimit-Reset

API Endpoints
Authentication
Register User

Login

Refresh Token

Logout

Change Password

Reset Password

Users
Get Current User

Update Profile

Get User Vehicles

Add Vehicle

Update Vehicle

Delete Vehicle

Parking Spots
List Parking Spots

Get Parking Spot

Check Availability

Get Spot Status

Get Spot Map

Reservations
Create Reservation

Get Reservations

Get Reservation

Update Reservation

Cancel Reservation

Extend Reservation

Check-in

Check-out

Payments
Process Payment

Get Payments

Get Payment

Refund Payment

Get Payment Methods

Add Payment Method

Delete Payment Method

Reviews
Create Review

Get Reviews

Update Review

Delete Review

Get Spot Ratings

Waitlist
Join Waitlist

Check Waitlist Status

Leave Waitlist

Get Waitlist Position

Admin Endpoints
Dashboard Stats

Manage Users

Manage Parking Spots

View Reports

Manage Pricing Rules

View Audit Logs

Webhooks
Payment Webhook

Reservation Webhook

Error Codes
Code	Description
AUTH_001	Invalid credentials
AUTH_002	Token expired
AUTH_003	Invalid token
AUTH_004	Insufficient permissions
USER_001	User not found
USER_002	Email already exists
USER_003	Invalid user data
VEHICLE_001	Vehicle not found
VEHICLE_002	License plate already exists
SPOT_001	Parking spot not found
SPOT_002	Spot not available
SPOT_003	Invalid spot type
RES_001	Reservation not found
RES_002	Reservation already exists
RES_003	Cannot modify reservation
RES_004	Check-in failed
PAY_001	Payment failed
PAY_002	Invalid payment method
PAY_003	Refund failed
REV_001	Review not found
REV_002	Already reviewed
WAIT_001	Already on waitlist
WAIT_002	Not on waitlist
ADMIN_001	Admin access required
Data Models
User
json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "phone": "+1234567890",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
Vehicle
json
{
  "id": "uuid",
  "user_id": "uuid",
  "license_plate": "ABC123",
  "vehicle_type": "car",
  "make": "Toyota",
  "model": "Camry",
  "color": "Blue",
  "is_default": true,
  "created_at": "2024-01-01T00:00:00Z"
}
Parking Spot
json
{
  "id": "uuid",
  "spot_number": "A123",
  "spot_type": "standard",
  "floor": 1,
  "section": "A",
  "status": "available",
  "price_per_hour": 2.50,
  "features": ["covered", "ev_charging"],
  "coordinates": {
    "x": 10,
    "y": 20
  },
  "created_at": "2024-01-01T00:00:00Z"
}
Reservation
json
{
  "id": "uuid",
  "user_id": "uuid",
  "vehicle_id": "uuid",
  "spot_id": "uuid",
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T12:00:00Z",
  "status": "confirmed",
  "total_price": 5.00,
  "check_in_time": null,
  "check_out_time": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
Payment
json
{
  "id": "uuid",
  "reservation_id": "uuid",
  "amount": 5.00,
  "currency": "USD",
  "status": "completed",
  "payment_method": "credit_card",
  "transaction_id": "txn_123456",
  "created_at": "2024-01-01T00:00:00Z"
}
Review
json
{
  "id": "uuid",
  "user_id": "uuid",
  "spot_id": "uuid",
  "reservation_id": "uuid",
  "rating": 5,
  "comment": "Great parking spot!",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
Waitlist Entry
json
{
  "id": "uuid",
  "user_id": "uuid",
  "spot_type": "standard",
  "preferred_time": "2024-01-01T10:00:00Z",
  "status": "waiting",
  "position": 3,
  "created_at": "2024-01-01T00:00:00Z"
}
Pagination
List endpoints support pagination with the following query parameters:

page: Page number (default: 1)

limit: Items per page (default: 20, max: 100)

sort: Sort field (prefix with - for descending)

filter: Filter criteria

Example:

text
GET /api/v1/reservations?page=2&limit=10&sort=-created_at&filter[status]=confirmed
Response includes pagination metadata:

json
{
  "status": "success",
  "data": [],
  "pagination": {
    "current_page": 2,
    "total_pages": 10,
    "total_items": 95,
    "items_per_page": 10,
    "next_page": 3,
    "prev_page": 1
  }
}
Webhooks
Webhooks allow real-time notifications for events:

reservation.created

reservation.updated

reservation.cancelled

reservation.checkin

reservation.checkout

payment.completed

payment.failed

payment.refunded

Configure webhook endpoints in the admin panel.

text

## 2. Authentication API Documentation

**`parking-management/backend/docs/api/auth.md`**

```markdown
# Authentication API

## Register User
Creates a new user account.

**Endpoint**: `POST /api/v1/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "phone": "+1234567890"
}
Response (201 Created):

json
{
  "status": "success",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe",
      "phone": "+1234567890",
      "role": "user",
      "created_at": "2024-01-01T00:00:00Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
Error Responses:

400 Bad Request: Invalid input data

409 Conflict: Email already exists

422 Unprocessable Entity: Validation error

Login
Authenticates a user and returns JWT tokens.

Endpoint: POST /api/v1/auth/login

Request Body:

json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "user"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600
  }
}
Error Responses:

401 Unauthorized: Invalid credentials

403 Forbidden: Account disabled

Refresh Token
Obtains a new access token using a refresh token.

Endpoint: POST /api/v1/auth/refresh

Request Body:

json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600
  }
}
Error Responses:

401 Unauthorized: Invalid refresh token

403 Forbidden: Token expired

Logout
Invalidates the current JWT token.

Endpoint: POST /api/v1/auth/logout

Headers:

text
Authorization: Bearer <token>
Response (200 OK):

json
{
  "status": "success",
  "message": "Successfully logged out"
}
Change Password
Changes the authenticated user's password.

Endpoint: POST /api/v1/auth/change-password

Headers:

text
Authorization: Bearer <token>
Request Body:

json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!",
  "confirm_password": "NewPass456!"
}
Response (200 OK):

json
{
  "status": "success",
  "message": "Password changed successfully"
}
Error Responses:

400 Bad Request: Invalid input

401 Unauthorized: Incorrect current password

Request Password Reset
Sends a password reset email.

Endpoint: POST /api/v1/auth/request-reset

Request Body:

json
{
  "email": "user@example.com"
}
Response (200 OK):

json
{
  "status": "success",
  "message": "Password reset email sent"
}
Reset Password
Resets password using reset token.

Endpoint: POST /api/v1/auth/reset-password

Request Body:

json
{
  "token": "reset-token-from-email",
  "new_password": "NewPass456!",
  "confirm_password": "NewPass456!"
}
Response (200 OK):

json
{
  "status": "success",
  "message": "Password reset successfully"
}
Error Responses:

400 Bad Request: Invalid token

401 Unauthorized: Token expired

text

## 3. Parking API Documentation

**`parking-management/backend/docs/api/parking.md`**

```markdown
# Parking API

## List Parking Spots
Returns a paginated list of parking spots with optional filtering.

**Endpoint**: `GET /api/v1/parking/spots`

**Headers**:
Authorization: Bearer <token>

text

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `spot_type` | string | Filter by spot type (standard, handicapped, ev, motorcycle) |
| `status` | string | Filter by status (available, occupied, reserved, maintenance) |
| `floor` | integer | Filter by floor number |
| `section` | string | Filter by section |
| `available` | boolean | Show only available spots |
| `features` | string | Comma-separated list of features (covered, ev_charging, near_elevator) |
| `sort` | string | Sort field (spot_number, price_per_hour, floor) |
| `page` | integer | Page number (default: 1) |
| `limit` | integer | Items per page (default: 20) |

**Response** (200 OK):
```json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "spot_number": "A101",
      "spot_type": "standard",
      "floor": 1,
      "section": "A",
      "status": "available",
      "price_per_hour": 2.50,
      "features": ["covered", "near_elevator"],
      "coordinates": {
        "x": 10.5,
        "y": 15.2
      },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 5,
    "total_items": 100,
    "items_per_page": 20
  }
}
Get Parking Spot
Returns detailed information about a specific parking spot.

Endpoint: GET /api/v1/parking/spots/{spot_id}

Headers:

text
Authorization: Bearer <token>
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "spot_number": "A101",
    "spot_type": "standard",
    "floor": 1,
    "section": "A",
    "status": "available",
    "price_per_hour": 2.50,
    "features": ["covered", "near_elevator"],
    "dimensions": {
      "length": 5.0,
      "width": 2.5,
      "height": 2.0
    },
    "coordinates": {
      "x": 10.5,
      "y": 15.2
    },
    "current_reservation": null,
    "maintenance_history": [],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
Check Availability
Checks spot availability for a specific time period.

Endpoint: GET /api/v1/parking/availability

Headers:

text
Authorization: Bearer <token>
Query Parameters:

Parameter	Type	Required	Description
start_time	datetime	Yes	Start time (ISO 8601)
end_time	datetime	Yes	End time (ISO 8601)
spot_type	string	No	Preferred spot type
features	string	No	Required features
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "available_spots": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "spot_number": "A101",
        "spot_type": "standard",
        "floor": 1,
        "price_per_hour": 2.50,
        "features": ["covered"],
        "total_price": 5.00
      }
    ],
    "total_available": 15,
    "requested_period": {
      "start_time": "2024-01-01T10:00:00Z",
      "end_time": "2024-01-01T12:00:00Z",
      "duration_hours": 2
    }
  }
}
Get Spot Status
Returns real-time status of parking spots.

Endpoint: GET /api/v1/parking/status

Headers:

text
Authorization: Bearer <token>
Query Parameters:

Parameter	Type	Description
floor	integer	Filter by floor
section	string	Filter by section
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "summary": {
      "total_spots": 200,
      "available": 45,
      "occupied": 150,
      "reserved": 3,
      "maintenance": 2
    },
    "by_type": {
      "standard": { "total": 150, "available": 35 },
      "handicapped": { "total": 10, "available": 2 },
      "ev": { "total": 30, "available": 5 },
      "motorcycle": { "total": 10, "available": 3 }
    },
    "by_floor": [
      {
        "floor": 1,
        "total": 50,
        "available": 12,
        "sections": {
          "A": { "total": 25, "available": 5 },
          "B": { "total": 25, "available": 7 }
        }
      }
    ],
    "updated_at": "2024-01-01T10:30:00Z"
  }
}
Get Spot Map
Returns a visual representation of the parking layout.

Endpoint: GET /api/v1/parking/map

Headers:

text
Authorization: Bearer <token>
Query Parameters:

Parameter	Type	Description
floor	integer	Floor number (default: 1)
format	string	Response format (json or svg)
Response (200 OK) - JSON format:

json
{
  "status": "success",
  "data": {
    "floor": 1,
    "dimensions": {
      "width": 100,
      "height": 80
    },
    "sections": [
      {
        "id": "A",
        "name": "Section A",
        "bounds": {
          "x": 0,
          "y": 0,
          "width": 50,
          "height": 40
        }
      }
    ],
    "spots": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "number": "A101",
        "type": "standard",
        "status": "available",
        "coordinates": {
          "x": 10,
          "y": 15,
          "width": 5,
          "height": 2.5
        },
        "rotation": 0
      }
    ],
    "legend": {
      "available": "#00ff00",
      "occupied": "#ff0000",
      "reserved": "#ffff00",
      "maintenance": "#808080"
    }
  }
}
Admin Endpoints
Create Parking Spot
Endpoint: POST /api/v1/admin/parking/spots

Headers:

text
Authorization: Bearer <admin-token>
Request Body:

json
{
  "spot_number": "B202",
  "spot_type": "ev",
  "floor": 2,
  "section": "B",
  "price_per_hour": 3.50,
  "features": ["ev_charging", "covered"],
  "dimensions": {
    "length": 5.0,
    "width": 2.5,
    "height": 2.0
  },
  "coordinates": {
    "x": 20.5,
    "y": 30.2
  }
}
Update Parking Spot
Endpoint: PUT /api/v1/admin/parking/spots/{spot_id}

Delete Parking Spot
Endpoint: DELETE /api/v1/admin/parking/spots/{spot_id}

Set Maintenance Mode
Endpoint: POST /api/v1/admin/parking/spots/{spot_id}/maintenance

json
{
  "status": "maintenance",
  "reason": "Repairing sensor",
  "estimated_duration_hours": 24
}
text

## 4. Reservations API Documentation

**`parking-management/backend/docs/api/reservations.md`**

```markdown
# Reservations API

## Create Reservation
Creates a new parking reservation.

**Endpoint**: `POST /api/v1/reservations`

**Headers**:
Authorization: Bearer <token>

text

**Request Body**:
```json
{
  "spot_id": "550e8400-e29b-41d4-a716-446655440000",
  "vehicle_id": "550e8400-e29b-41d4-a716-446655440001",
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T12:00:00Z",
  "notes": "Will arrive at 10:15"
}
Response (201 Created):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "user_id": "550e8400-e29b-41d4-a716-446655440003",
    "spot_id": "550e8400-e29b-41d4-a716-446655440000",
    "vehicle_id": "550e8400-e29b-41d4-a716-446655440001",
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T12:00:00Z",
    "status": "confirmed",
    "total_price": 5.00,
    "price_breakdown": {
      "base_price": 5.00,
      "discount": 0,
      "tax": 0,
      "final_price": 5.00
    },
    "qr_code": "data:image/png;base64,...",
    "check_in_time": null,
    "check_out_time": null,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
Get User Reservations
Returns all reservations for the authenticated user.

Endpoint: GET /api/v1/reservations

Headers:

text
Authorization: Bearer <token>
Query Parameters:

Parameter	Type	Description
status	string	Filter by status (confirmed, active, completed, cancelled)
from_date	date	Filter by start date
to_date	date	Filter by end date
page	integer	Page number
limit	integer	Items per page
sort	string	Sort field
Response (200 OK):

json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "spot": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "spot_number": "A101",
        "spot_type": "standard",
        "floor": 1
      },
      "vehicle": {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "license_plate": "ABC123",
        "vehicle_type": "car"
      },
      "start_time": "2024-01-01T10:00:00Z",
      "end_time": "2024-01-01T12:00:00Z",
      "status": "confirmed",
      "total_price": 5.00,
      "check_in_time": null,
      "check_out_time": null,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 3,
    "total_items": 25
  }
}
Get Reservation
Returns details of a specific reservation.

Endpoint: GET /api/v1/reservations/{reservation_id}

Headers:

text
Authorization: Bearer <token>
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "full_name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890"
    },
    "spot": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "spot_number": "A101",
      "spot_type": "standard",
      "floor": 1,
      "section": "A",
      "price_per_hour": 2.50,
      "features": ["covered"]
    },
    "vehicle": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "license_plate": "ABC123",
      "make": "Toyota",
      "model": "Camry",
      "color": "Blue"
    },
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T12:00:00Z",
    "status": "confirmed",
    "total_price": 5.00,
    "price_breakdown": {
      "base_price": 5.00,
      "discount_applied": null,
      "tax": 0,
      "final_price": 5.00
    },
    "payment": {
      "id": "550e8400-e29b-41d4-a716-446655440004",
      "status": "pending",
      "amount": 5.00
    },
    "qr_code": "data:image/png;base64,...",
    "check_in_time": null,
    "check_out_time": null,
    "notes": "Will arrive at 10:15",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
Update Reservation
Updates an existing reservation.

Endpoint: PUT /api/v1/reservations/{reservation_id}

Headers:

text
Authorization: Bearer <token>
Request Body:

json
{
  "start_time": "2024-01-01T11:00:00Z",
  "end_time": "2024-01-01T13:00:00Z",
  "vehicle_id": "550e8400-e29b-41d4-a716-446655440001",
  "notes": "Updated arrival time"
}
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "start_time": "2024-01-01T11:00:00Z",
    "end_time": "2024-01-01T13:00:00Z",
    "total_price": 5.00,
    "updated_at": "2024-01-01T09:00:00Z"
  }
}
Cancel Reservation
Cancels a reservation.

Endpoint: DELETE /api/v1/reservations/{reservation_id}

Headers:

text
Authorization: Bearer <token>
Query Parameters:

Parameter	Type	Description
reason	string	Cancellation reason
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "status": "cancelled",
    "cancelled_at": "2024-01-01T09:30:00Z",
    "refund_amount": 5.00,
    "refund_status": "processed"
  }
}
Extend Reservation
Extends the duration of an active reservation.

Endpoint: POST /api/v1/reservations/{reservation_id}/extend

Headers:

text
Authorization: Bearer <token>
Request Body:

json
{
  "new_end_time": "2024-01-01T14:00:00Z"
}
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "original_end_time": "2024-01-01T12:00:00Z",
    "new_end_time": "2024-01-01T14:00:00Z",
    "additional_charge": 5.00,
    "total_price": 10.00,
    "status": "confirmed"
  }
}
Check-in
Performs check-in for a reservation.

Endpoint: POST /api/v1/reservations/{reservation_id}/checkin

Headers:

text
Authorization: Bearer <token>
Request Body (optional):

json
{
  "qr_code_data": "base64-encoded-qr"
}
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "check_in_time": "2024-01-01T10:05:00Z",
    "status": "active",
    "gate_opened": true,
    "spot_accessible": true
  }
}
Check-out
Performs check-out for an active reservation.

Endpoint: POST /api/v1/reservations/{reservation_id}/checkout

Headers:

text
Authorization: Bearer <token>
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "check_out_time": "2024-01-01T12:05:00Z",
    "actual_duration_hours": 2.08,
    "final_charge": 5.20,
    "overage_charge": 0.20,
    "payment_status": "processed"
  }
}
Get Reservation QR Code
Returns the QR code for a reservation.

Endpoint: GET /api/v1/reservations/{reservation_id}/qr

Headers:

text
Authorization: Bearer <token>
Query Parameters:

Parameter	Type	Description
format	string	Response format (json, png, svg)
size	integer	QR code size in pixels
Response (200 OK) - JSON format:

json
{
  "status": "success",
  "data": {
    "qr_code": "data:image/png;base64,...",
    "reservation_id": "550e8400-e29b-41d4-a716-446655440002",
    "valid_until": "2024-01-01T12:00:00Z"
  }
}
text

## 5. Payments API Documentation

**`parking-management/backend/docs/api/payments.md`**

```markdown
# Payments API

## Process Payment
Processes payment for a reservation.

**Endpoint**: `POST /api/v1/payments`

**Headers**:
Authorization: Bearer <token>

text

**Request Body**:
```json
{
  "reservation_id": "550e8400-e29b-41d4-a716-446655440002",
  "payment_method_id": "550e8400-e29b-41d4-a716-446655440005",
  "amount": 5.00,
  "currency": "USD"
}
Response (201 Created):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440004",
    "reservation_id": "550e8400-e29b-41d4-a716-446655440002",
    "amount": 5.00,
    "currency": "USD",
    "status": "completed",
    "payment_method": {
      "id": "550e8400-e29b-41d4-a716-446655440005",
      "type": "credit_card",
      "last4": "4242"
    },
    "transaction_id": "txn_123456789",
    "receipt_url": "https://api.parking-management.com/receipts/123",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
Get Payments
Returns payment history for the authenticated user.

Endpoint: GET /api/v1/payments

Headers:

text
Authorization: Bearer <token>
Query Parameters:

Parameter	Type	Description
status	string	Filter by status
from_date	date	Filter by date range
to_date	date	Filter by date range
page	integer	Page number
limit	integer	Items per page
Response (200 OK):

json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440004",
      "reservation": {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "spot_number": "A101",
        "start_time": "2024-01-01T10:00:00Z",
        "end_time": "2024-01-01T12:00:00Z"
      },
      "amount": 5.00,
      "status": "completed",
      "payment_method": "credit_card",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 2,
    "total_items": 15
  }
}
Get Payment
Returns details of a specific payment.

Endpoint: GET /api/v1/payments/{payment_id}

Headers:

text
Authorization: Bearer <token>
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440004",
    "reservation": {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "spot_number": "A101",
      "start_time": "2024-01-01T10:00:00Z",
      "end_time": "2024-01-01T12:00:00Z"
    },
    "amount": 5.00,
    "currency": "USD",
    "status": "completed",
    "payment_method": {
      "id": "550e8400-e29b-41d4-a716-446655440005",
      "type": "credit_card",
      "brand": "visa",
      "last4": "4242",
      "expiry_month": 12,
      "expiry_year": 2025
    },
    "transaction_id": "txn_123456789",
    "receipt_url": "https://api.parking-management.com/receipts/123",
    "metadata": {
      "billing_address": {
        "line1": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "US"
      }
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
Refund Payment
Processes a refund for a payment.

Endpoint: POST /api/v1/payments/{payment_id}/refund

Headers:

text
Authorization: Bearer <token>
Request Body:

json
{
  "amount": 5.00,
  "reason": "Cancelled reservation"
}
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440006",
    "original_payment_id": "550e8400-e29b-41d4-a716-446655440004",
    "amount": 5.00,
    "status": "completed",
    "refund_transaction_id": "ref_123456789",
    "processed_at": "2024-01-01T10:00:00Z"
  }
}
Payment Methods
Get Payment Methods
Endpoint: GET /api/v1/payments/methods

Headers:

text
Authorization: Bearer <token>
Response (200 OK):

json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440005",
      "type": "credit_card",
      "brand": "visa",
      "last4": "4242",
      "expiry_month": 12,
      "expiry_year": 2025,
      "is_default": true,
      "billing_address": {
        "line1": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "US"
      },
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
Add Payment Method
Endpoint: POST /api/v1/payments/methods

Headers:

text
Authorization: Bearer <token>
Request Body:

json
{
  "type": "credit_card",
  "payment_method_details": {
    "card_number": "4242424242424242",
    "expiry_month": 12,
    "expiry_year": 2025,
    "cvv": "123",
    "cardholder_name": "John Doe"
  },
  "billing_address": {
    "line1": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "US"
  },
  "is_default": true
}
Response (201 Created):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440007",
    "type": "credit_card",
    "brand": "visa",
    "last4": "4242",
    "expiry_month": 12,
    "expiry_year": 2025,
    "is_default": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
Delete Payment Method
Endpoint: DELETE /api/v1/payments/methods/{method_id}

Headers:

text
Authorization: Bearer <token>
Response (200 OK):

json
{
  "status": "success",
  "message": "Payment method deleted successfully"
}
Set Default Payment Method
Endpoint: PUT /api/v1/payments/methods/{method_id}/default

Headers:

text
Authorization: Bearer <token>
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440005",
    "is_default": true
  }
}
Receipts
Get Receipt
Endpoint: GET /api/v1/payments/{payment_id}/receipt

Headers:

text
Authorization: Bearer <token>
Query Parameters:

Parameter	Type	Description
format	string	Response format (json, pdf, html)
Response (200 OK) - PDF format:
Returns PDF file with receipt details.

Webhook
Handles payment provider webhooks.

Endpoint: POST /api/v1/payments/webhook

Headers:

text
X-Webhook-Signature: <signature>
Request Body:

json
{
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_123456789",
      "amount": 500,
      "currency": "usd",
      "status": "succeeded"
    }
  }
}
Response (200 OK):

json
{
  "status": "success",
  "received": true
}
text

## 6. Admin API Documentation

**`parking-management/backend/docs/api/admin.md`**

```markdown
# Admin API

All admin endpoints require authentication with admin privileges.

## Dashboard

### Get Dashboard Stats
Returns summary statistics for the admin dashboard.

**Endpoint**: `GET /api/v1/admin/dashboard`

**Headers**:
Authorization: Bearer <admin-token>

text

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "summary": {
      "total_users": 1250,
      "active_users_today": 342,
      "total_reservations": 5678,
      "active_reservations": 123,
      "total_revenue_today": 4567.89,
      "total_revenue_month": 123456.78,
      "occupancy_rate": 78.5,
      "average_duration": 2.3
    },
    "charts": {
      "reservations_by_hour": [
        {"hour": 8, "count": 45},
        {"hour": 9, "count": 78},
        {"hour": 10, "count": 92}
      ],
      "revenue_by_day": [
        {"date": "2024-01-01", "amount": 1234.56},
        {"date": "2024-01-02", "amount": 1456.78}
      ],
      "spot_utilization": [
        {"spot_type": "standard", "utilization": 82},
        {"spot_type": "handicapped", "utilization": 45},
        {"spot_type": "ev", "utilization": 67}
      ]
    },
    "alerts": [
      {
        "type": "maintenance_needed",
        "spot_id": "550e8400-e29b-41d4-a716-446655440000",
        "message": "Sensor malfunction detected",
        "severity": "high",
        "created_at": "2024-01-01T10:00:00Z"
      }
    ],
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
User Management
List Users
Endpoint: GET /api/v1/admin/users

Headers:

text
Authorization: Bearer <admin-token>
Query Parameters:

Parameter	Type	Description
role	string	Filter by role
status	string	Filter by status
search	string	Search by name or email
page	integer	Page number
limit	integer	Items per page
Response (200 OK):

json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "email": "john@example.com",
      "full_name": "John Doe",
      "phone": "+1234567890",
      "role": "user",
      "status": "active",
      "total_reservations": 15,
      "total_spent": 75.50,
      "joined_at": "2023-01-01T00:00:00Z",
      "last_active": "2024-01-01T10:00:00Z"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 25,
    "total_items": 1250
  }
}
Get User Details
Endpoint: GET /api/v1/admin/users/{user_id}

Headers:

text
Authorization: Bearer <admin-token>
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "email": "john@example.com",
      "full_name": "John Doe",
      "phone": "+1234567890",
      "role": "user",
      "status": "active",
      "email_verified": true,
      "phone_verified": false,
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-01T10:00:00Z"
    },
    "statistics": {
      "total_reservations": 15,
      "completed_reservations": 12,
      "cancelled_reservations": 3,
      "total_spent": 75.50,
      "average_rating": 4.5,
      "loyalty_points": 150
    },
    "recent_activity": [
      {
        "type": "reservation",
        "description": "Reserved spot A101",
        "timestamp": "2024-01-01T09:00:00Z"
      }
    ],
    "vehicles": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "license_plate": "ABC123",
        "make": "Toyota",
        "model": "Camry",
        "color": "Blue",
        "is_default": true
      }
    ]
  }
}
Update User
Endpoint: PUT /api/v1/admin/users/{user_id}

Headers:

text
Authorization: Bearer <admin-token>
Request Body:

json
{
  "full_name": "John Updated",
  "phone": "+1987654321",
  "role": "premium",
  "status": "active",
  "email_verified": true
}
Delete User
Endpoint: DELETE /api/v1/admin/users/{user_id}

Headers:

text
Authorization: Bearer <admin-token>
Reports
Generate Report
Endpoint: POST /api/v1/admin/reports

Headers:

text
Authorization: Bearer <admin-token>
Request Body:

json
{
  "report_type": "revenue",
  "date_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "format": "json",
  "group_by": "day",
  "filters": {
    "spot_types": ["standard", "ev"],
    "payment_methods": ["credit_card"]
  }
}
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "report_id": "rep_123456",
    "generated_at": "2024-01-01T12:00:00Z",
    "report_data": {
      "summary": {
        "total_revenue": 123456.78,
        "total_transactions": 2345,
        "average_transaction": 52.65
      },
      "breakdown": [
        {
          "date": "2024-01-01",
          "revenue": 4567.89,
          "transactions": 87,
          "spot_types": {
            "standard": 3456.78,
            "ev": 1111.11
          }
        }
      ]
    },
    "download_url": "/api/v1/admin/reports/rep_123456/download"
  }
}
Pricing Rules
List Pricing Rules
Endpoint: GET /api/v1/admin/pricing-rules

Headers:

text
Authorization: Bearer <admin-token>
Response (200 OK):

json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440008",
      "name": "Weekend Premium",
      "rule_type": "time_based",
      "conditions": {
        "days": ["saturday", "sunday"],
        "hours": {"start": 9, "end": 18}
      },
      "adjustment": {
        "type": "multiplier",
        "value": 1.5
      },
      "applicable_to": ["standard", "ev"],
      "priority": 1,
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
Create Pricing Rule
Endpoint: POST /api/v1/admin/pricing-rules

Headers:

text
Authorization: Bearer <admin-token>
Request Body:

json
{
  "name": "Early Bird Special",
  "rule_type": "time_based",
  "conditions": {
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "hours": {"start": 6, "end": 9}
  },
  "adjustment": {
    "type": "fixed_discount",
    "value": 2.00
  },
  "applicable_to": ["standard"],
  "priority": 2,
  "is_active": true
}
Audit Logs
Get Audit Logs
Endpoint: GET /api/v1/admin/audit-logs

Headers:

text
Authorization: Bearer <admin-token>
Query Parameters:

Parameter	Type	Description
user_id	uuid	Filter by user
action	string	Filter by action type
resource	string	Filter by resource type
from_date	date	Start date
to_date	date	End date
page	integer	Page number
limit	integer	Items per page
Response (200 OK):

json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440009",
      "timestamp": "2024-01-01T10:30:00Z",
      "user": {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "email": "admin@example.com",
        "full_name": "Admin User"
      },
      "action": "UPDATE",
      "resource": "user",
      "resource_id": "550e8400-e29b-41d4-a716-446655440003",
      "details": {
        "changes": {
          "role": ["user", "premium"]
        }
      },
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0..."
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 15,
    "total_items": 289
  }
}
System Settings
Get Settings
Endpoint: GET /api/v1/admin/settings

Headers:

text
Authorization: Bearer <admin-token>
Response (200 OK):

json
{
  "status": "success",
  "data": {
    "parking": {
      "base_price_per_hour": 2.50,
      "grace_period_minutes": 15,
      "max_reservation_duration_hours": 24,
      "advance_booking_days": 30,
      "cancellation_policy": "free_up_to_1_hour"
    },
    "notifications": {
      "email_enabled": true,
      "sms_enabled": true,
      "push_enabled": false,
      "reminder_minutes": [30, 60]
    },
    "payments": {
      "accepted_methods": ["credit_card", "debit_card", "paypal"],
      "currency": "USD",
      "tax_rate": 8.5,
      "deposit_required": false,
      "deposit_amount": 0
    },
    "system": {
      "maintenance_mode": false,
      "debug_mode": false,
      "log_level": "info",
      "cache_ttl_seconds": 300
    }
  }
}
Update Settings
Endpoint: PUT /api/v1/admin/settings

Headers:

text
Authorization: Bearer <admin-token>
Request Body:

json
{
  "parking": {
    "base_price_per_hour": 3.00,
    "grace_period_minutes": 10
  },
  "system": {
    "maintenance_mode": false
  }
}
text

## 7. OpenAPI/Swagger Specification

**`parking-management/backend/docs/api/openapi.yaml`**

```yaml
openapi: 3.0.0
info:
  title: Parking Management System API
  description: API for managing parking facilities, reservations, and payments
  version: 1.0.0
  contact:
    name: API Support
    email: support@parking-management.com
  license:
    name: Proprietary

servers:
  - url: https://api.parking-management.com/api/v1
    description: Production server
  - url: http://localhost:8000/api/v1
    description: Development server

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        full_name:
          type: string
        phone:
          type: string
        role:
          type: string
          enum: [user, admin, manager]
        is_active:
          type: boolean
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
    
    Vehicle:
      type: object
      properties:
        id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        license_plate:
          type: string
        vehicle_type:
          type: string
          enum: [car, motorcycle, truck, ev]
        make:
          type: string
        model:
          type: string
        color:
          type: string
        is_default:
          type: boolean
    
    ParkingSpot:
      type: object
      properties:
        id:
          type: string
          format: uuid
        spot_number:
          type: string
        spot_type:
          type: string
          enum: [standard, handicapped, ev, motorcycle]
        floor:
          type: integer
        section:
          type: string
        status:
          type: string
          enum: [available, occupied, reserved, maintenance]
        price_per_hour:
          type: number
          format: float
        features:
          type: array
          items:
            type: string
        coordinates:
          type: object
          properties:
            x:
              type: number
            y:
              type: number
    
    Reservation:
      type: object
      properties:
        id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        spot_id:
          type: string
          format: uuid
        vehicle_id:
          type: string
          format: uuid
        start_time:
          type: string
          format: date-time
        end_time:
          type: string
          format: date-time
        status:
          type: string
          enum: [pending, confirmed, active, completed, cancelled]
        total_price:
          type: number
          format: float
        check_in_time:
          type: string
          format: date-time
          nullable: true
        check_out_time:
          type: string
          format: date-time
          nullable: true
    
    Payment:
      type: object
      properties:
        id:
          type: string
          format: uuid
        reservation_id:
          type: string
          format: uuid
        amount:
          type: number
          format: float
        currency:
          type: string
        status:
          type: string
          enum: [pending, completed, failed, refunded]
        payment_method:
          type: string
        transaction_id:
          type: string
    
    Review:
      type: object
      properties:
        id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        spot_id:
          type: string
          format: uuid
        rating:
          type: integer
          minimum: 1
          maximum: 5
        comment:
          type: string
        created_at:
          type: string
          format: date-time
    
    Error:
      type: object
      properties:
        status:
          type: string
          enum: [error]
        error:
          type: object
          properties:
            code:
              type: string
            message:
              type: string
            details:
              type: object

  responses:
    UnauthorizedError:
      description: Authentication required
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    
    ForbiddenError:
      description: Insufficient permissions
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    
    NotFoundError:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    
    ValidationError:
      description: Validation error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

paths:
  # Authentication endpoints
  /auth/register:
    post:
      tags: [Authentication]
      summary: Register a new user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - password
                - full_name
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
                  format: password
                full_name:
                  type: string
                phone:
                  type: string
      responses:
        '201':
          description: User created successfully
        '400':
          $ref: '#/components/responses/ValidationError'
        '409':
          description: Email already exists
  
  /auth/login:
    post:
      tags: [Authentication]
      summary: Login user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - password
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
                  format: password
      responses:
        '200':
          description: Login successful
        '401':
          description: Invalid credentials
  
  # Parking spots endpoints
  /parking/spots:
    get:
      tags: [Parking]
      summary: List parking spots
      security:
        - bearerAuth: []
      parameters:
        - name: spot_type
          in: query
          schema:
            type: string
        - name: status
          in: query
          schema:
            type: string
        - name: floor
          in: query
          schema:
            type: integer
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: List of parking spots
        '401':
          $ref: '#/components/responses/UnauthorizedError'
  
  /parking/spots/{spot_id}:
    get:
      tags: [Parking]
      summary: Get parking spot details
      security:
        - bearerAuth: []
      parameters:
        - name: spot_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Parking spot details
        '404':
          $ref: '#/components/responses/NotFoundError'
  
  /parking/availability:
    get:
      tags: [Parking]
      summary: Check spot availability
      security:
        - bearerAuth: []
      parameters:
        - name: start_time
          in: query
          required: true
          schema:
            type: string
            format: date-time
        - name: end_time
          in: query
          required: true
          schema:
            type: string
            format: date-time
        - name: spot_type
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Availability information
  
  # Reservations endpoints
  /reservations:
    post:
      tags: [Reservations]
      summary: Create a reservation
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - spot_id
                - vehicle_id
                - start_time
                - end_time
              properties:
                spot_id:
                  type: string
                  format: uuid
                vehicle_id:
                  type: string
                  format: uuid
                start_time:
                  type: string
                  format: date-time
                end_time:
                  type: string
                  format: date-time
                notes:
                  type: string
      responses:
        '201':
          description: Reservation created
        '400':
          $ref: '#/components/responses/ValidationError'
    
    get:
      tags: [Reservations]
      summary: Get user reservations
      security:
        - bearerAuth: []
      parameters:
        - name: status
          in: query
          schema:
            type: string
        - name: page
          in: query
          schema:
            type: integer
        - name: limit
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: List of reservations
  
  /reservations/{reservation_id}:
    get:
      tags: [Reservations]
      summary: Get reservation details
      security:
        - bearerAuth: []
      parameters:
        - name: reservation_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Reservation details
    
    put:
      tags: [Reservations]
      summary: Update reservation
      security:
        - bearerAuth: []
      parameters:
        - name: reservation_id
          in: path
          required: true
      requestBody:
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: Reservation updated
    
    delete:
      tags: [Reservations]
      summary: Cancel reservation
      security:
        - bearerAuth: []
      parameters:
        - name: reservation_id
          in: path
          required: true
      responses:
        '200':
          description: Reservation cancelled
  
  /reservations/{reservation_id}/checkin:
    post:
      tags: [Reservations]
      summary: Check-in to reservation
      security:
        - bearerAuth: []
      parameters:
        - name: reservation_id
          in: path
          required: true
      responses:
        '200':
          description: Check-in successful
  
  /reservations/{reservation_id}/checkout:
    post:
      tags: [Reservations]
      summary: Check-out from reservation
      security:
        - bearerAuth: []
      parameters:
        - name: reservation_id
          in: path
          required: true
      responses:
        '200':
          description: Check-out successful
  
  # Payments endpoints
  /payments:
    post:
      tags: [Payments]
      summary: Process payment
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - reservation_id
                - payment_method_id
              properties:
                reservation_id:
                  type: string
                  format: uuid
                payment_method_id:
                  type: string
                  format: uuid
                amount:
                  type: number
                currency:
                  type: string
                  default: USD
      responses:
        '201':
          description: Payment processed
    
    get:
      tags: [Payments]
      summary: Get payment history
      security:
        - bearerAuth: []
      parameters:
        - name: status
          in: query
          schema:
            type: string
        - name: page
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: Payment history
  
  /payments/methods:
    get:
      tags: [Payments]
      summary: Get payment methods
      security:
        - bearerAuth: []
      responses:
        '200':
          description: List of payment methods
    
    post:
      tags: [Payments]
      summary: Add payment method
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - type
                - payment_method_details
              properties:
                type:
                  type: string
                  enum: [credit_card, debit_card, paypal]
                payment_method_details:
                  type: object
                is_default:
                  type: boolean
      responses:
        '201':
          description: Payment method added
  
  /payments/methods/{method_id}:
    delete:
      tags: [Payments]
      summary: Delete payment method
      security:
        - bearerAuth: []
      parameters:
        - name: method_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Payment method deleted
  
  # Reviews endpoints
  /reviews:
    post:
      tags: [Reviews]
      summary: Create review
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - spot_id
                - reservation_id
                - rating
              properties:
                spot_id:
                  type: string
                  format: uuid
                reservation_id:
                  type: string
                  format: uuid
                rating:
                  type: integer
                  minimum: 1
                  maximum: 5
                comment:
                  type: string
      responses:
        '201':
          description: Review created
    
    get:
      tags: [Reviews]
      summary: Get reviews
      parameters:
        - name: spot_id
          in: query
          schema:
            type: string
            format: uuid
        - name: page
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: List of reviews
  
  # Admin endpoints
  /admin/dashboard:
    get:
      tags: [Admin]
      summary: Get dashboard statistics
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Dashboard statistics
        '403':
          $ref: '#/components/responses/ForbiddenError'
  
  /admin/users:
    get:
      tags: [Admin]
      summary: List all users
      security:
        - bearerAuth: []
      parameters:
        - name: role
          in: query
          schema:
            type: string
        - name: status
          in: query
          schema:
            type: string
        - name: page
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: List of users
  
  /admin/audit-logs:
    get:
      tags: [Admin]
      summary: Get audit logs
      security:
        - bearerAuth: []
      parameters:
        - name: from_date
          in: query
          schema:
            type: string
            format: date
        - name: to_date
          in: query
          schema:
            type: string
            format: date
        - name: action
          in: query
          schema:
            type: string
        - name: page
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: Audit logs
  
  /admin/reports:
    post:
      tags: [Admin]
      summary: Generate report
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - report_type
                - date_range
              properties:
                report_type:
                  type: string
                  enum: [revenue, occupancy, users, reservations]
                date_range:
                  type: object
                  properties:
                    start_date:
                      type: string
                      format: date
                    end_date:
                      type: string
                      format: date
                format:
                  type: string
                  enum: [json, csv, pdf]
                  default: json
      responses:
        '200':
          description: Report generated
  
  /health:
    get:
      tags: [Health]
      summary: Health check
      responses:
        '200':
          description: API is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: healthy
                  version:
                    type: string
                  timestamp:
                    type: string
                    format: date-time

tags:
  - name: Authentication
    description: User authentication operations
  - name: Users
    description: User profile operations
  - name: Parking
    description: Parking spot operations
  - name: Reservations
    description: Reservation operations
  - name: Payments
    description: Payment operations
  - name: Reviews
    description: Review operations
  - name: Admin
    description: Admin operations
  - name: Health
    description: Health check
This comprehensive API documentation provides:

Detailed endpoint descriptions with request/response examples

Authentication requirements

Error handling

Data models

Pagination

Rate limiting

Webhooks

OpenAPI/Swagger specification