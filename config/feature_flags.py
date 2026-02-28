"""Feature flags configuration."""

from typing import Dict, Any, List
from datetime import datetime

from . import config


class FeatureFlags:
    """Feature flags configuration."""
    
    # Core features
    RESERVATION_CONFIRMATION: bool = config.FEATURE_RESERVATION_CONFIRMATION
    WAITLIST: bool = config.FEATURE_WAITLIST
    RECURRING_RESERVATIONS: bool = config.FEATURE_RECURRING_RESERVATIONS
    PAYMENT_REFUNDS: bool = config.FEATURE_PAYMENT_REFUNDS
    NOTIFICATIONS: bool = config.FEATURE_NOTIFICATIONS
    ANALYTICS: bool = config.FEATURE_ANALYTICS
    
    # Beta features
    BETA_FEATURES: Dict[str, bool] = {
        "qr_code_checkin": False,
        "license_plate_recognition": False,
        "dynamic_pricing": False,
        "ai_recommendations": False,
        "voice_commands": False,
    }
    
    # Feature rollout percentages
    ROLLOUT_PERCENTAGES: Dict[str, int] = {
        "qr_code_checkin": 25,  # 25% of users
        "dynamic_pricing": 10,   # 10% of users
    }
    
    # Feature availability by environment
    ENVIRONMENT_AVAILABILITY: Dict[str, List[str]] = {
        "development": list(BETA_FEATURES.keys()) + [
            "reservation_confirmation",
            "waitlist",
            "recurring_reservations",
            "payment_refunds",
            "notifications",
            "analytics",
        ],
        "staging": [
            "reservation_confirmation",
            "waitlist",
            "recurring_reservations",
            "payment_refunds",
            "notifications",
        ],
        "production": [
            "reservation_confirmation",
            "waitlist",
            "recurring_reservations",
            "payment_refunds",
            "notifications",
            "analytics",
        ],
    }
    
    # Feature dependencies
    DEPENDENCIES: Dict[str, List[str]] = {
        "qr_code_checkin": ["notifications"],
        "dynamic_pricing": ["analytics"],
    }
    
    # Scheduled feature rollouts
    SCHEDULED_ROLLOUTS: Dict[str, datetime] = {
        "qr_code_checkin": datetime(2024, 3, 1),
        "license_plate_recognition": datetime(2024, 4, 1),
        "dynamic_pricing": datetime(2024, 5, 1),
    }
    
    def is_enabled(self, feature: str, user_id: Optional[int] = None) -> bool:
        """Check if feature is enabled."""
        # Check core features
        if hasattr(self, feature.upper()):
            return getattr(self, feature.upper())
        
        # Check beta features
        if feature in self.BETA_FEATURES:
            # Check environment availability
            if feature not in self.ENVIRONMENT_AVAILABILITY.get(config.ENV, []):
                return False
            
            # Check rollout percentage
            if user_id and feature in self.ROLLOUT_PERCENTAGES:
                import hashlib
                hash_val = int(hashlib.md5(f"{user_id}:{feature}".encode()).hexdigest(), 16)
                percentage = self.ROLLOUT_PERCENTAGES[feature]
                return (hash_val % 100) < percentage
            
            return self.BETA_FEATURES[feature]
        
        return False
    
    def get_enabled_features(self, user_id: Optional[int] = None) -> List[str]:
        """Get list of enabled features."""
        enabled = []
        
        # Check core features
        core_features = [
            "reservation_confirmation",
            "waitlist",
            "recurring_reservations",
            "payment_refunds",
            "notifications",
            "analytics",
        ]
        
        for feature in core_features:
            if self.is_enabled(feature, user_id):
                enabled.append(feature)
        
        # Check beta features
        for feature in self.BETA_FEATURES:
            if self.is_enabled(feature, user_id):
                enabled.append(feature)
        
        return enabled


feature_flags = FeatureFlags()