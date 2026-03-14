"""
CRUD package initialization.
Export all CRUD instances for easy importing.
"""

from .audit import audit

# Export CRUD instances
__all__ = [
    "audit"
]