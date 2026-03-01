"""Cache key constants."""

from typing import Dict, Any


class CacheKeys:
    """Cache key constants with formatting methods."""
    
    USER = "user:{id}"
    RESERVATION = "reservation:{id}"
    SPOT = "spot:{id}"
    VEHICLE = "vehicle:{id}"
    USER_RESERVATIONS = "user:{user_id}:reservations"
    SPOT_AVAILABILITY = "spot:{spot_id}:availability:{date}"
    STATS = "stats:{type}:{period}"
    SESSION = "session:{session_id}"
    
    @classmethod
    def format_key(cls, key_template: str, **kwargs) -> str:
        """Format a cache key with provided parameters."""
        return key_template.format(**kwargs)
    
    @classmethod
    def user_key(cls, user_id: int) -> str:
        """Get formatted user cache key."""
        return cls.format_key(cls.USER, id=user_id)
    
    @classmethod
    def reservation_key(cls, reservation_id: int) -> str:
        """Get formatted reservation cache key."""
        return cls.format_key(cls.RESERVATION, id=reservation_id)
    
    @classmethod
    def spot_key(cls, spot_id: int) -> str:
        """Get formatted spot cache key."""
        return cls.format_key(cls.SPOT, id=spot_id)
    
    @classmethod
    def user_reservations_key(cls, user_id: int) -> str:
        """Get formatted user reservations cache key."""
        return cls.format_key(cls.USER_RESERVATIONS, user_id=user_id)