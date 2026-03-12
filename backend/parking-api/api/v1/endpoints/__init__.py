"""
API v1 endpoints package.
"""

from . import (
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

__all__ = [
    'auth',
    'users',
    'vehicles',
    'parking',
    'reservations',
    'payments',
    'reviews',
    'waitlist',
    'admin',
    'health'
]