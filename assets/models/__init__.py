"""Models package initialization for the parking management system.

This module exports all database models and provides utility functions
for model management and relationships.
"""

from typing import Dict, Type, List, Any, Optional
from datetime import datetime

# Import all models
from .user import User
from .vehicle import Vehicle
from .parking_spot import ParkingSpot
from .reservation import Reservation
from .payment import Payment
from .notification import Notification
from .audit_log import AuditLog
from .waitlist import WaitlistEntry
from .price_rule import PriceRule
from .review import Review
from .maintenance import MaintenanceRecord

# Define model registry for dynamic access
MODEL_REGISTRY: Dict[str, Type] = {
    'user': User,
    'vehicle': Vehicle,
    'parking_spot': ParkingSpot,
    'reservation': Reservation,
    'payment': Payment,
    'notification': Notification,
    'audit_log': AuditLog,
    'waitlist_entry': WaitlistEntry,
    'price_rule': PriceRule,
    'review': Review,
    'maintenance_record': MaintenanceRecord,
}

# Define model relationships for reference
MODEL_RELATIONSHIPS = {
    'User': {
        'vehicles': ('Vehicle', 'user_id'),
        'reservations': ('Reservation', 'user_id'),
        'payments': ('Payment', 'user_id'),
        'notifications': ('Notification', 'user_id'),
        'reviews': ('Review', 'user_id'),
        'waitlist_entries': ('WaitlistEntry', 'user_id'),
    },
    'Vehicle': {
        'user': ('User', 'user_id'),
        'reservations': ('Reservation', 'vehicle_id'),
    },
    'ParkingSpot': {
        'reservations': ('Reservation', 'spot_id'),
        'maintenance_records': ('MaintenanceRecord', 'spot_id'),
        'current_reservation': ('Reservation', 'current_reservation_id'),
        'current_vehicle': ('Vehicle', 'current_vehicle_id'),
    },
    'Reservation': {
        'user': ('User', 'user_id'),
        'spot': ('ParkingSpot', 'spot_id'),
        'vehicle': ('Vehicle', 'vehicle_id'),
        'payments': ('Payment', 'reservation_id'),
    },
    'Payment': {
        'user': ('User', 'user_id'),
        'reservation': ('Reservation', 'reservation_id'),
    },
    'Notification': {
        'user': ('User', 'user_id'),
    },
    'WaitlistEntry': {
        'user': ('User', 'user_id'),
        'spot': ('ParkingSpot', 'spot_id'),
    },
    'Review': {
        'user': ('User', 'user_id'),
        'reservation': ('Reservation', 'reservation_id'),
    },
    'MaintenanceRecord': {
        'spot': ('ParkingSpot', 'spot_id'),
        'created_by': ('User', 'created_by'),
    },
}

# Export all models
__all__ = [
    'User',
    'Vehicle',
    'ParkingSpot',
    'Reservation',
    'Payment',
    'Notification',
    'AuditLog',
    'WaitlistEntry',
    'PriceRule',
    'Review',
    'MaintenanceRecord',
    'MODEL_REGISTRY',
    'MODEL_RELATIONSHIPS',
    'get_model',
    'get_model_relationships',
    'get_related_models',
    'get_tablename',
    'model_to_dict',
    'get_model_fields',
    'create_model_instance',
    'get_model_by_tablename',
]


def get_model(model_name: str) -> Optional[Type]:
    """Get a model class by name (case-insensitive).
    
    Args:
        model_name: Name of the model (e.g., 'user', 'User', 'reservation')
        
    Returns:
        Model class if found, None otherwise
    """
    return MODEL_REGISTRY.get(model_name.lower())


def get_model_by_tablename(table_name: str) -> Optional[Type]:
    """Get a model class by its database table name.
    
    Args:
        table_name: Database table name
        
    Returns:
        Model class if found, None otherwise
    """
    table_to_model = {
        get_tablename(model): model_name 
        for model_name, model in MODEL_REGISTRY.items()
    }
    model_name = table_to_model.get(table_name)
    return get_model(model_name) if model_name else None


def get_tablename(model_class: Type) -> str:
    """Get the database table name for a model.
    
    Args:
        model_class: Model class
        
    Returns:
        Table name as string
    """
    if hasattr(model_class, '__tablename__'):
        return model_class.__tablename__
    return model_class.__name__.lower()


def get_model_relationships(model_name: str) -> Dict[str, tuple]:
    """Get relationships for a specific model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Dictionary of relationship names to (related_model, foreign_key) tuples
    """
    # Capitalize first letter for relationship lookup
    model_key = model_name.capitalize()
    return MODEL_RELATIONSHIPS.get(model_key, {})


def get_related_models(model_name: str) -> List[str]:
    """Get list of related model names for a given model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        List of related model names
    """
    relationships = get_model_relationships(model_name)
    return [rel[0] for rel in relationships.values()]


def model_to_dict(
    model_instance: Any,
    exclude_fields: Optional[List[str]] = None,
    include_relationships: bool = False,
    depth: int = 0,
    max_depth: int = 3
) -> Dict[str, Any]:
    """Convert a model instance to a dictionary.
    
    Args:
        model_instance: SQLAlchemy model instance
        exclude_fields: List of field names to exclude
        include_relationships: Whether to include relationship data
        depth: Current recursion depth
        max_depth: Maximum recursion depth for relationships
        
    Returns:
        Dictionary representation of the model
    """
    if not model_instance:
        return {}
    
    if exclude_fields is None:
        exclude_fields = []
    
    result = {}
    
    # Get all columns
    for column in model_instance.__table__.columns:
        field_name = column.name
        if field_name not in exclude_fields:
            value = getattr(model_instance, field_name)
            # Handle datetime objects
            if isinstance(value, datetime):
                value = value.isoformat()
            result[field_name] = value
    
    # Include relationships if requested and within depth limit
    if include_relationships and depth < max_depth:
        for rel_name in model_instance.__mapper__.relationships.keys():
            if rel_name not in exclude_fields:
                rel_value = getattr(model_instance, rel_name)
                if rel_value is not None:
                    if hasattr(rel_value, '__iter__') and not isinstance(rel_value, str):
                        # Handle collections
                        result[rel_name] = [
                            model_to_dict(
                                item, 
                                exclude_fields, 
                                include_relationships, 
                                depth + 1, 
                                max_depth
                            )
                            for item in rel_value
                        ]
                    else:
                        # Handle single relationship
                        result[rel_name] = model_to_dict(
                            rel_value, 
                            exclude_fields, 
                            include_relationships, 
                            depth + 1, 
                            max_depth
                        )
    
    return result


def get_model_fields(model_name: str) -> List[Dict[str, Any]]:
    """Get field information for a model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        List of dictionaries containing field information
    """
    model_class = get_model(model_name)
    if not model_class:
        return []
    
    fields = []
    
    # Get column information
    for column in model_class.__table__.columns:
        field_info = {
            'name': column.name,
            'type': str(column.type),
            'nullable': column.nullable,
            'primary_key': column.primary_key,
            'unique': column.unique,
            'default': str(column.default) if column.default else None,
            'autoincrement': column.autoincrement,
        }
        fields.append(field_info)
    
    return fields


def create_model_instance(
    model_name: str,
    data: Dict[str, Any],
    validate: bool = True
) -> Optional[Any]:
    """Create a model instance from dictionary data.
    
    Args:
        model_name: Name of the model
        data: Dictionary of field values
        validate: Whether to validate the data before creation
        
    Returns:
        Model instance if successful, None otherwise
    """
    model_class = get_model(model_name)
    if not model_class:
        return None
    
    # Filter data to only include valid fields
    valid_fields = {col.name for col in model_class.__table__.columns}
    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
    
    # Create instance
    instance = model_class(**filtered_data)
    
    # Validate if requested
    if validate and hasattr(instance, 'validate'):
        if not instance.validate():
            return None
    
    return instance


def get_model_docstring(model_name: str) -> Optional[str]:
    """Get the docstring for a model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Model docstring if available, None otherwise
    """
    model_class = get_model(model_name)
    if model_class and model_class.__doc__:
        return model_class.__doc__.strip()
    return None


def get_all_models() -> List[str]:
    """Get list of all registered model names.
    
    Returns:
        List of model names
    """
    return list(MODEL_REGISTRY.keys())


def get_model_count() -> int:
    """Get the total number of registered models.
    
    Returns:
        Number of registered models
    """
    return len(MODEL_REGISTRY)


def get_models_by_module(module_name: str) -> List[str]:
    """Get models defined in a specific module.
    
    Args:
        module_name: Name of the module (e.g., 'user', 'payment')
        
    Returns:
        List of model names in that module
    """
    # This is a simplified version - in practice, you might want to
    # inspect the actual module contents
    if module_name == 'user':
        return ['User']
    elif module_name == 'vehicle':
        return ['Vehicle']
    elif module_name == 'parking_spot':
        return ['ParkingSpot']
    elif module_name == 'reservation':
        return ['Reservation']
    elif module_name == 'payment':
        return ['Payment']
    elif module_name == 'notification':
        return ['Notification']
    elif module_name == 'audit':
        return ['AuditLog']
    elif module_name == 'waitlist':
        return ['WaitlistEntry']
    elif module_name == 'pricing':
        return ['PriceRule']
    elif module_name == 'reviews':
        return ['Review']
    elif module_name == 'maintenance':
        return ['MaintenanceRecord']
    return []


def get_model_metadata(model_name: str) -> Dict[str, Any]:
    """Get metadata for a model including table info and relationships.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Dictionary containing model metadata
    """
    model_class = get_model(model_name)
    if not model_class:
        return {}
    
    return {
        'name': model_name,
        'class_name': model_class.__name__,
        'table_name': get_tablename(model_class),
        'fields': get_model_fields(model_name),
        'relationships': get_model_relationships(model_name),
        'docstring': get_model_docstring(model_name),
        'has_timestamps': hasattr(model_class, 'created_at') or hasattr(model_class, 'updated_at'),
    }


def get_model_constants() -> Dict[str, Any]:
    """Get all model-related constants.
    
    Returns:
        Dictionary of model constants
    """
    return {
        'model_registry': MODEL_REGISTRY,
        'model_relationships': MODEL_RELATIONSHIPS,
        'model_count': get_model_count(),
        'all_models': get_all_models(),
    }


# Initialize any model-specific configurations or registrations
def _initialize_models() -> None:
    """Initialize model configurations and registrations."""
    # This function can be used to set up any model-specific
    # configurations, listeners, or registrations
    pass


# Run initialization
_initialize_models()