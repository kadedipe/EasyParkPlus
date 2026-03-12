"""
API package for Parking Management System.
This package contains all API-related code including routes, dependencies, and middleware.
"""

from fastapi import APIRouter

from .v1.api import api_router as api_v1_router

# Create main API router
api_router = APIRouter()

# Include versioned API routers
api_router.include_router(api_v1_router, prefix="/v1")

# API metadata
__version__ = "1.0.0"
__api_title__ = "Parking Management System API"
__api_description__ = """
# Parking Management System API

## Overview
This API provides comprehensive functionality for managing parking facilities,
including reservations, payments, user management, and real-time parking spot monitoring.

## Features
- 🔐 **Authentication & Authorization**: JWT-based authentication with role-based access control
- 🅿️ **Parking Management**: Real-time parking spot availability and status
- 📅 **Reservations**: Create, modify, and cancel parking reservations
- 💳 **Payments**: Secure payment processing with multiple payment methods
- 👤 **User Management**: Profile management and vehicle registration
- ⭐ **Reviews**: Rate and review parking spots
- 📊 **Analytics**: Detailed reporting and analytics for administrators
- 🔔 **Notifications**: Email, SMS, and push notifications
- 📱 **Mobile Ready**: RESTful API designed for mobile applications

## Authentication
Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:

Authorization: Bearer <your-access-token>


## Rate Limiting
API requests are rate-limited based on user tier:
- Free tier: 100 requests per minute
- Basic tier: 200 requests per minute
- Premium tier: 1000 requests per minute
- Enterprise: Custom limits

## Pagination
List endpoints support pagination with the following query parameters:
- `page`: Page number (default: 1)
- `size`: Items per page (default: 20, max: 100)
- `sort`: Sort field (prefix with - for descending)

## Error Handling
All errors follow a consistent format:
```json
{
    "status": "error",
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "details": {} // Optional additional details
    }
}

Versioning
The API is versioned through the URL path. Current version: v1

Support
For API support, contact: api-support@parking-management.com
"""

all = [
"api_router",
"version",
"api_title",
"api_description"
]


## Version-specific API Router

**`parking-management/backend/parking-api/api/v1/api.py`**

```python
"""
API v1 router configuration.
"""

from fastapi import APIRouter

from .endpoints import (
    auth,
    users,
    vehicles,
    parking,
    reservations,
    payments,
    reviews,
    waitlist,
    admin,
    health
)

# Create API v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["vehicles"])
api_router.include_router(parking.router, prefix="/parking", tags=["parking"])
api_router.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(waitlist.router, prefix="/waitlist", tags=["waitlist"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(health.router, prefix="/health", tags=["health"])

# API metadata for v1
__version__ = "1.0.0"
__api_version__ = "v1"