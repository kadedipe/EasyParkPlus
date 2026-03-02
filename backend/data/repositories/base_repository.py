# parking-management/data/migrations/repositories/base_repository.py
"""
Base repository classes for the parking management system.

This module provides abstract base classes and generic repository implementations
that serve as the foundation for all data access layers in the application.
These classes leverage the enum definitions for type safety and consistency.
"""

from abc import ABC, abstractmethod
from typing import (
    TypeVar, Generic, List, Optional, Dict, Any, 
    Union, Type, Tuple, Callable, Awaitable
)
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
import hashlib
from contextlib import contextmanager
from functools import wraps

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select, 
    update, delete, insert, text, Table, Column
)
from sqlalchemy.orm import Session, Query, joinedload, selectinload
from sqlalchemy.exc import (
    SQLAlchemyError, IntegrityError, DataError,
    OperationalError, PendingRollbackError
)
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.inspection import inspect

from ..models.enums import (
    # Audit enums
    AuditAction, AuditStatus, AuditSeverity, 
    AuditCategory, AuditResourceType,
    
    # General enums
    UserStatus, VehicleStatus, ReservationStatus,
    SpotStatus, PaymentStatus, NotificationStatus
)

# Type variables for generic repository patterns
T = TypeVar('T')  # Entity type
ID = TypeVar('ID')  # ID type (usually int, str, or UUID)
CreateDTO = TypeVar('CreateDTO')  # DTO for creation
UpdateDTO = TypeVar('UpdateDTO')  # DTO for updates

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class RepositoryException(Exception):
    """Base exception for repository layer."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class EntityNotFoundException(RepositoryException):
    """Raised when an entity is not found."""
    def __init__(self, entity_name: str, entity_id: Any):
        self.entity_name = entity_name
        self.entity_id = entity_id
        message = f"{entity_name} with id {entity_id} not found"
        super().__init__(message)


class DuplicateEntityException(RepositoryException):
    """Raised when attempting to create a duplicate entity."""
    def __init__(self, entity_name: str, constraint: str, value: Any):
        self.entity_name = entity_name
        self.constraint = constraint
        self.value = value
        message = f"{entity_name} with {constraint} '{value}' already exists"
        super().__init__(message)


class ValidationException(RepositoryException):
    """Raised when entity validation fails."""
    def __init__(self, entity_name: str, errors: Dict[str, List[str]]):
        self.entity_name = entity_name
        self.errors = errors
        message = f"Validation failed for {entity_name}: {errors}"
        super().__init__(message)


class ConstraintViolationException(RepositoryException):
    """Raised when a database constraint is violated."""
    def __init__(self, message: str, constraint_name: Optional[str] = None):
        self.constraint_name = constraint_name
        super().__init__(message)


class OptimisticLockException(RepositoryException):
    """Raised when optimistic locking fails due to concurrent modification."""
    def __init__(self, entity_name: str, entity_id: Any, expected_version: int):
        self.entity_name = entity_name
        self.entity_id = entity_id
        self.expected_version = expected_version
        message = f"{entity_name} with id {entity_id} was modified by another transaction"
        super().__init__(message)


class ConcurrencyException(RepositoryException):
    """Raised when a concurrency conflict occurs."""
    pass


class DataIntegrityException(RepositoryException):
    """Raised when data integrity is compromised."""
    pass


# ============================================================================
# Query Builders and Helpers
# ============================================================================

class QueryBuilder:
    """Fluent query builder for complex database queries."""
    
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model
        self.query = session.query(model)
        self._filters = []
        self._joins = []
        self._options = []
        self._order_by = []
        self._group_by = []
        self._having = []
        
    def filter(self, *criterion) -> 'QueryBuilder':
        """Add filter condition."""
        self._filters.extend(criterion)
        return self
    
    def filter_by(self, **kwargs) -> 'QueryBuilder':
        """Add simple equality filters."""
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                self._filters.append(getattr(self.model, key) == value)
        return self
    
    def search(self, search_term: str, fields: List[str]) -> 'QueryBuilder':
        """Add text search across specified fields."""
        if search_term and fields:
            conditions = []
            for field in fields:
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    if hasattr(column, 'ilike'):
                        conditions.append(column.ilike(f'%{search_term}%'))
            if conditions:
                self._filters.append(or_(*conditions))
        return self
    
    def join(self, *props, **kwargs) -> 'QueryBuilder':
        """Add join clause."""
        self._joins.append((props, kwargs))
        return self
    
    def options(self, *opts) -> 'QueryBuilder':
        """Add loading options (eager loading, etc.)."""
        self._options.extend(opts)
        return self
    
    def order_by(self, *criterion) -> 'QueryBuilder':
        """Add ordering."""
        self._order_by.extend(criterion)
        return self
    
    def group_by(self, *criterion) -> 'QueryBuilder':
        """Add grouping."""
        self._group_by.extend(criterion)
        return self
    
    def having(self, *criterion) -> 'QueryBuilder':
        """Add having clause."""
        self._having.extend(criterion)
        return self
    
    def limit(self, limit: int) -> 'QueryBuilder':
        """Set result limit."""
        self.query = self.query.limit(limit)
        return self
    
    def offset(self, offset: int) -> 'QueryBuilder':
        """Set result offset."""
        self.query = self.query.offset(offset)
        return self
    
    def build(self) -> Query:
        """Build and return the final query."""
        # Apply joins
        for props, kwargs in self._joins:
            self.query = self.query.join(*props, **kwargs)
        
        # Apply options
        if self._options:
            self.query = self.query.options(*self._options)
        
        # Apply filters
        if self._filters:
            self.query = self.query.filter(and_(*self._filters))
        
        # Apply grouping
        if self._group_by:
            self.query = self.query.group_by(*self._group_by)
        
        # Apply having
        if self._having:
            self.query = self.query.having(and_(*self._having))
        
        # Apply ordering
        if self._order_by:
            self.query = self.query.order_by(*self._order_by)
        
        return self.query
    
    def count(self) -> int:
        """Get count of results."""
        return self.build().count()
    
    def all(self) -> List[T]:
        """Execute and return all results."""
        return self.build().all()
    
    def first(self) -> Optional[T]:
        """Execute and return first result."""
        return self.build().first()
    
    def one(self) -> T:
        """Execute and return exactly one result."""
        return self.build().one()
    
    def one_or_none(self) -> Optional[T]:
        """Execute and return one result or None."""
        return self.build().one_or_none()
    
    def paginate(self, page: int = 1, per_page: int = 20) -> Tuple[List[T], int, int, int]:
        """
        Paginate results.
        
        Returns:
            Tuple of (items, total_count, page, total_pages)
        """
        total = self.count()
        items = self.limit(per_page).offset((page - 1) * per_page).all()
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        return items, total, page, total_pages


# ============================================================================
# Base Repository Interface
# ============================================================================

class IRepository(ABC, Generic[T, ID]):
    """Interface defining the contract for all repositories."""
    
    @abstractmethod
    def get(self, id: ID) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    def get_or_fail(self, id: ID) -> T:
        """Get entity by ID or raise exception."""
        pass
    
    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination."""
        pass
    
    @abstractmethod
    def find(self, **kwargs) -> List[T]:
        """Find entities by criteria."""
        pass
    
    @abstractmethod
    def find_one(self, **kwargs) -> Optional[T]:
        """Find one entity by criteria."""
        pass
    
    @abstractmethod
    def count(self, **kwargs) -> int:
        """Count entities by criteria."""
        pass
    
    @abstractmethod
    def exists(self, **kwargs) -> bool:
        """Check if entity exists."""
        pass
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    def create_many(self, entities: List[T]) -> List[T]:
        """Create multiple entities."""
        pass
    
    @abstractmethod
    def update(self, id: ID, **kwargs) -> Optional[T]:
        """Update entity by ID."""
        pass
    
    @abstractmethod
    def update_entity(self, entity: T) -> T:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    def update_many(self, criteria: Dict[str, Any], values: Dict[str, Any]) -> int:
        """Update multiple entities matching criteria."""
        pass
    
    @abstractmethod
    def delete(self, id: ID) -> bool:
        """Delete entity by ID."""
        pass
    
    @abstractmethod
    def delete_entity(self, entity: T) -> bool:
        """Delete an entity."""
        pass
    
    @abstractmethod
    def delete_many(self, **criteria) -> int:
        """Delete multiple entities matching criteria."""
        pass
    
    @abstractmethod
    def delete_all(self) -> int:
        """Delete all entities."""
        pass
    
    @abstractmethod
    def bulk_insert(self, entities: List[Dict[str, Any]]) -> int:
        """Bulk insert entities from dictionaries."""
        pass
    
    @abstractmethod
    def bulk_update(self, entities: List[T]) -> int:
        """Bulk update entities."""
        pass
    
    @abstractmethod
    def refresh(self, entity: T) -> T:
        """Refresh entity from database."""
        pass
    
    @abstractmethod
    def query(self) -> QueryBuilder:
        """Get a query builder for complex queries."""
        pass


# ============================================================================
# Base Repository Implementation
# ============================================================================

class BaseRepository(IRepository[T, ID]):
    """
    Base repository implementation with common CRUD operations.
    
    This class provides a generic implementation of common database operations
    that can be extended by specific repositories.
    """
    
    def __init__(self, session: Session, model_class: Type[T]):
        """
        Initialize the repository.
        
        Args:
            session: SQLAlchemy session
            model_class: The SQLAlchemy model class this repository manages
        """
        self.session = session
        self.model_class = model_class
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Get model metadata
        self.inspector = inspect(model_class)
        self.primary_key = self.inspector.primary_key[0].name if self.inspector.primary_key else 'id'
    
    def _get_entity_name(self) -> str:
        """Get the entity name for error messages."""
        return self.model_class.__name__
    
    def _get_primary_key_value(self, entity: T) -> Any:
        """Extract primary key value from entity."""
        return getattr(entity, self.primary_key)
    
    def _apply_base_filters(self, query: Query) -> Query:
        """
        Apply base filters to query.
        
        Override this method to add global filters (e.g., soft delete, tenant isolation).
        """
        return query
    
    def _validate_entity(self, entity: T, is_create: bool = True) -> None:
        """
        Validate entity before persistence.
        
        Override this method to add custom validation logic.
        
        Args:
            entity: The entity to validate
            is_create: True if this is a create operation, False for update
            
        Raises:
            ValidationException: If validation fails
        """
        pass
    
    def _before_create(self, entity: T) -> None:
        """Hook called before creating an entity."""
        self._validate_entity(entity, is_create=True)
    
    def _after_create(self, entity: T) -> None:
        """Hook called after creating an entity."""
        pass
    
    def _before_update(self, entity: T) -> None:
        """Hook called before updating an entity."""
        self._validate_entity(entity, is_create=False)
    
    def _after_update(self, entity: T) -> None:
        """Hook called after updating an entity."""
        pass
    
    def _before_delete(self, entity: T) -> None:
        """Hook called before deleting an entity."""
        pass
    
    def _after_delete(self, entity: T) -> None:
        """Hook called after deleting an entity."""
        pass
    
    def _before_bulk_operation(self, operation: str, entities: List[T]) -> None:
        """Hook called before bulk operations."""
        pass
    
    def _after_bulk_operation(self, operation: str, entities: List[T], result: int) -> None:
        """Hook called after bulk operations."""
        pass
    
    def _handle_error(self, error: Exception, operation: str, **context) -> None:
        """
        Handle repository errors.
        
        Args:
            error: The exception that occurred
            operation: The operation being performed
            context: Additional context information
            
        Raises:
            RepositoryException: Wrapped repository exception
        """
        self.logger.error(
            f"Error during {operation}: {str(error)}",
            exc_info=True,
            extra={"context": context}
        )
        
        if isinstance(error, IntegrityError):
            self._handle_integrity_error(error, operation, context)
        elif isinstance(error, DataError):
            raise ValidationException(
                self._get_entity_name(),
                {"data": [str(error)]}
            ) from error
        elif isinstance(error, OperationalError):
            raise RepositoryException(f"Database operation failed: {str(error)}") from error
        else:
            raise RepositoryException(f"Unexpected error during {operation}: {str(error)}") from error
    
    def _handle_integrity_error(self, error: IntegrityError, operation: str, context: Dict) -> None:
        """Handle database integrity errors."""
        error_msg = str(error.orig) if error.orig else str(error)
        
        # Check for duplicate key violations
        if "duplicate key" in error_msg.lower() or "unique constraint" in error_msg.lower():
            # Extract constraint name if possible
            import re
            constraint_match = re.search(r'unique constraint "(\w+)"', error_msg)
            constraint = constraint_match.group(1) if constraint_match else "unknown"
            
            raise DuplicateEntityException(
                self._get_entity_name(),
                constraint,
                context.get("value", "unknown")
            ) from error
        
        # Check for foreign key violations
        elif "foreign key" in error_msg.lower() or "foreign key constraint" in error_msg.lower():
            raise ConstraintViolationException(
                f"Foreign key violation: {error_msg}",
                "foreign_key"
            ) from error
        
        # Check for check constraint violations
        elif "check constraint" in error_msg.lower():
            raise ValidationException(
                self._get_entity_name(),
                {"constraint": [error_msg]}
            ) from error
        
        else:
            raise ConstraintViolationException(error_msg) from error
    
    # ========================================================================
    # Read Operations
    # ========================================================================
    
    def get(self, id: ID) -> Optional[T]:
        """Get entity by ID."""
        try:
            query = self.session.query(self.model_class)
            query = self._apply_base_filters(query)
            return query.get(id)
        except Exception as e:
            self._handle_error(e, "get", {"id": id})
    
    def get_or_fail(self, id: ID) -> T:
        """Get entity by ID or raise exception."""
        entity = self.get(id)
        if entity is None:
            raise EntityNotFoundException(self._get_entity_name(), id)
        return entity
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination."""
        try:
            query = self.session.query(self.model_class)
            query = self._apply_base_filters(query)
            
            if skip > 0:
                query = query.offset(skip)
            if limit > 0:
                query = query.limit(limit)
            
            return query.all()
        except Exception as e:
            self._handle_error(e, "get_all", {"skip": skip, "limit": limit})
    
    def find(self, **kwargs) -> List[T]:
        """Find entities by criteria."""
        try:
            query = self.session.query(self.model_class)
            query = self._apply_base_filters(query)
            
            for key, value in kwargs.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.all()
        except Exception as e:
            self._handle_error(e, "find", {"criteria": kwargs})
    
    def find_one(self, **kwargs) -> Optional[T]:
        """Find one entity by criteria."""
        try:
            query = self.session.query(self.model_class)
            query = self._apply_base_filters(query)
            
            for key, value in kwargs.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.first()
        except Exception as e:
            self._handle_error(e, "find_one", {"criteria": kwargs})
    
    def count(self, **kwargs) -> int:
        """Count entities by criteria."""
        try:
            query = self.session.query(func.count(self.model_class.id))
            query = self._apply_base_filters(query)
            
            for key, value in kwargs.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.scalar() or 0
        except Exception as e:
            self._handle_error(e, "count", {"criteria": kwargs})
    
    def exists(self, **kwargs) -> bool:
        """Check if entity exists."""
        try:
            return self.count(**kwargs) > 0
        except Exception as e:
            self._handle_error(e, "exists", {"criteria": kwargs})
    
    # ========================================================================
    # Create Operations
    # ========================================================================
    
    def create(self, entity: T) -> T:
        """Create a new entity."""
        try:
            self._before_create(entity)
            
            self.session.add(entity)
            self.session.flush()  # Flush to get generated IDs without committing
            
            self._after_create(entity)
            
            self.logger.info(f"Created {self._get_entity_name()} with ID: {self._get_primary_key_value(entity)}")
            return entity
        except Exception as e:
            self.session.rollback()
            self._handle_error(e, "create", {"entity": str(entity)})
    
    def create_many(self, entities: List[T]) -> List[T]:
        """Create multiple entities."""
        if not entities:
            return []
        
        try:
            self._before_bulk_operation("create_many", entities)
            
            for entity in entities:
                self._before_create(entity)
                self.session.add(entity)
            
            self.session.flush()
            
            for entity in entities:
                self._after_create(entity)
            
            self._after_bulk_operation("create_many", entities, len(entities))
            
            self.logger.info(f"Created {len(entities)} {self._get_entity_name()} entities")
            return entities
        except Exception as e:
            self.session.rollback()
            self._handle_error(e, "create_many", {"count": len(entities)})
    
    # ========================================================================
    # Update Operations
    # ========================================================================
    
    def update(self, id: ID, **kwargs) -> Optional[T]:
        """Update entity by ID."""
        try:
            entity = self.get(id)
            if not entity:
                return None
            
            # Update attributes
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            
            return self.update_entity(entity)
        except Exception as e:
            self._handle_error(e, "update", {"id": id, "values": kwargs})
    
    def update_entity(self, entity: T) -> T:
        """Update an existing entity."""
        try:
            self._before_update(entity)
            
            # Merge the entity if it's detached
            if entity not in self.session:
                entity = self.session.merge(entity)
            
            self.session.flush()
            
            self._after_update(entity)
            
            self.logger.info(f"Updated {self._get_entity_name()} with ID: {self._get_primary_key_value(entity)}")
            return entity
        except Exception as e:
            self.session.rollback()
            self._handle_error(e, "update_entity", {"entity": str(entity)})
    
    def update_many(self, criteria: Dict[str, Any], values: Dict[str, Any]) -> int:
        """Update multiple entities matching criteria."""
        try:
            # Build the where clause
            where_clause = []
            for key, value in criteria.items():
                if hasattr(self.model_class, key):
                    where_clause.append(getattr(self.model_class, key) == value)
            
            if not where_clause:
                return 0
            
            # Perform bulk update
            stmt = (
                update(self.model_class)
                .where(and_(*where_clause))
                .values(**values)
                .execution_options(synchronize_session="fetch")
            )
            
            result = self.session.execute(stmt)
            self.session.flush()
            
            self.logger.info(f"Updated {result.rowcount} {self._get_entity_name()} entities")
            return result.rowcount
        except Exception as e:
            self.session.rollback()
            self._handle_error(e, "update_many", {"criteria": criteria, "values": values})
    
    # ========================================================================
    # Delete Operations
    # ========================================================================
    
    def delete(self, id: ID) -> bool:
        """Delete entity by ID."""
        try:
            entity = self.get(id)
            if not entity:
                return False
            
            return self.delete_entity(entity)
        except Exception as e:
            self._handle_error(e, "delete", {"id": id})
    
    def delete_entity(self, entity: T) -> bool:
        """Delete an entity."""
        try:
            self._before_delete(entity)
            
            self.session.delete(entity)
            self.session.flush()
            
            self._after_delete(entity)
            
            self.logger.info(f"Deleted {self._get_entity_name()} with ID: {self._get_primary_key_value(entity)}")
            return True
        except Exception as e:
            self.session.rollback()
            self._handle_error(e, "delete_entity", {"entity": str(entity)})
    
    def delete_many(self, **criteria) -> int:
        """Delete multiple entities matching criteria."""
        try:
            # Build the where clause
            where_clause = []
            for key, value in criteria.items():
                if hasattr(self.model_class, key):
                    where_clause.append(getattr(self.model_class, key) == value)
            
            if not where_clause:
                return 0
            
            # Perform bulk delete
            stmt = delete(self.model_class).where(and_(*where_clause))
            result = self.session.execute(stmt)
            self.session.flush()
            
            self.logger.info(f"Deleted {result.rowcount} {self._get_entity_name()} entities")
            return result.rowcount
        except Exception as e:
            self.session.rollback()
            self._handle_error(e, "delete_many", {"criteria": criteria})
    
    def delete_all(self) -> int:
        """Delete all entities."""
        try:
            stmt = delete(self.model_class)
            result = self.session.execute(stmt)
            self.session.flush()
            
            self.logger.info(f"Deleted all {self._get_entity_name()} entities ({result.rowcount})")
            return result.rowcount
        except Exception as e:
            self.session.rollback()
            self._handle_error(e, "delete_all")
    
    # ========================================================================
    # Bulk Operations
    # ========================================================================
    
    def bulk_insert(self, entities: List[Dict[str, Any]]) -> int:
        """Bulk insert entities from dictionaries."""
        if not entities:
            return 0
        
        try:
            self._before_bulk_operation("bulk_insert", [])
            
            stmt = insert(self.model_class).values(entities)
            result = self.session.execute(stmt)
            self.session.flush()
            
            self._after_bulk_operation("bulk_insert", [], result.rowcount)
            
            self.logger.info(f"Bulk inserted {result.rowcount} {self._get_entity_name()} entities")
            return result.rowcount
        except Exception as e:
            self.session.rollback()
            self._handle_error(e, "bulk_insert", {"count": len(entities)})
    
    def bulk_update(self, entities: List[T]) -> int:
        """Bulk update entities."""
        if not entities:
            return 0
        
        try:
            self._before_bulk_operation("bulk_update", entities)
            
            updated_count = 0
            for entity in entities:
                self._before_update(entity)
                self.session.merge(entity)
                updated_count += 1
            
            self.session.flush()
            
            self._after_bulk_operation("bulk_update", entities, updated_count)
            
            self.logger.info(f"Bulk updated {updated_count} {self._get_entity_name()} entities")
            return updated_count
        except Exception as e:
            self.session.rollback()
            self._handle_error(e, "bulk_update", {"count": len(entities)})
    
    # ========================================================================
    # Utility Operations
    # ========================================================================
    
    def refresh(self, entity: T) -> T:
        """Refresh entity from database."""
        try:
            self.session.refresh(entity)
            return entity
        except Exception as e:
            self._handle_error(e, "refresh", {"entity": str(entity)})
    
    def query(self) -> QueryBuilder:
        """Get a query builder for complex queries."""
        return QueryBuilder(self.session, self.model_class)
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            yield
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise
    
    def execute_raw_sql(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute raw SQL and return results as dictionaries."""
        try:
            result = self.session.execute(text(sql), params or {})
            return [dict(row._mapping) for row in result]
        except Exception as e:
            self._handle_error(e, "execute_raw_sql", {"sql": sql})


# ============================================================================
# Specialized Repository Mixins
# ============================================================================

class SoftDeleteMixin:
    """Mixin adding soft delete functionality."""
    
    deleted_at: Optional[datetime]
    
    def soft_delete(self, id: ID) -> Optional[T]:
        """Soft delete an entity by ID."""
        if not hasattr(self, 'model_class') or not hasattr(self.model_class, 'deleted_at'):
            raise RepositoryException("Model does not support soft delete")
        
        try:
            entity = self.get(id)
            if not entity:
                return None
            
            entity.deleted_at = datetime.utcnow()
            return self.update_entity(entity)
        except Exception as e:
            self._handle_error(e, "soft_delete", {"id": id})
    
    def soft_delete_many(self, **criteria) -> int:
        """Soft delete multiple entities."""
        if not hasattr(self, 'model_class') or not hasattr(self.model_class, 'deleted_at'):
            raise RepositoryException("Model does not support soft delete")
        
        try:
            return self.update_many(criteria, {"deleted_at": datetime.utcnow()})
        except Exception as e:
            self._handle_error(e, "soft_delete_many", {"criteria": criteria})
    
    def restore(self, id: ID) -> Optional[T]:
        """Restore a soft-deleted entity."""
        if not hasattr(self, 'model_class') or not hasattr(self.model_class, 'deleted_at'):
            raise RepositoryException("Model does not support soft delete")
        
        try:
            # Override base filters to include deleted items
            original_apply_filters = self._apply_base_filters
            self._apply_base_filters = lambda q: q
            
            entity = self.get(id)
            
            # Restore original filter method
            self._apply_base_filters = original_apply_filters
            
            if not entity or not entity.deleted_at:
                return None
            
            entity.deleted_at = None
            return self.update_entity(entity)
        except Exception as e:
            self._handle_error(e, "restore", {"id": id})
    
    def get_deleted(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get soft-deleted entities."""
        if not hasattr(self, 'model_class') or not hasattr(self.model_class, 'deleted_at'):
            raise RepositoryException("Model does not support soft delete")
        
        try:
            query = self.session.query(self.model_class)
            query = query.filter(self.model_class.deleted_at.isnot(None))
            
            if skip > 0:
                query = query.offset(skip)
            if limit > 0:
                query = query.limit(limit)
            
            return query.all()
        except Exception as e:
            self._handle_error(e, "get_deleted", {"skip": skip, "limit": limit})


class TimestampMixin:
    """Mixin for timestamped entities."""
    
    created_at: datetime
    updated_at: Optional[datetime]
    
    def _before_create(self, entity: T) -> None:
        """Set timestamps before create."""
        if hasattr(entity, 'created_at'):
            entity.created_at = datetime.utcnow()
        if hasattr(entity, 'updated_at'):
            entity.updated_at = None
        super()._before_create(entity)
    
    def _before_update(self, entity: T) -> None:
        """Update timestamp before update."""
        if hasattr(entity, 'updated_at'):
            entity.updated_at = datetime.utcnow()
        super()._before_update(entity)


class AuditMixin:
    """Mixin for auditable entities."""
    
    created_by: Optional[int]
    updated_by: Optional[int]
    audit_action: Optional[AuditAction]
    audit_status: Optional[AuditStatus]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._audit_context = {}
    
    def set_audit_context(self, user_id: Optional[int] = None, **context):
        """Set audit context for operations."""
        self._audit_context = {
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            **context
        }
    
    def _before_create(self, entity: T) -> None:
        """Set audit fields before create."""
        if hasattr(entity, 'created_by') and 'user_id' in self._audit_context:
            entity.created_by = self._audit_context['user_id']
        
        if hasattr(entity, 'audit_action'):
            entity.audit_action = AuditAction.CREATE
        if hasattr(entity, 'audit_status'):
            entity.audit_status = AuditStatus.SUCCESS
        
        super()._before_create(entity)
    
    def _before_update(self, entity: T) -> None:
        """Set audit fields before update."""
        if hasattr(entity, 'updated_by') and 'user_id' in self._audit_context:
            entity.updated_by = self._audit_context['user_id']
        
        if hasattr(entity, 'audit_action'):
            entity.audit_action = AuditAction.UPDATE
        
        super()._before_update(entity)
    
    def _before_delete(self, entity: T) -> None:
        """Set audit fields before delete."""
        if hasattr(entity, 'audit_action'):
            entity.audit_action = AuditAction.DELETE
        super()._before_delete(entity)


class VersionedMixin:
    """Mixin for optimistic locking with version field."""
    
    version: int
    
    def _before_update(self, entity: T) -> None:
        """Check version before update."""
        if hasattr(entity, 'version'):
            # Get current version from database
            current = self.session.query(self.model_class.version).filter(
                getattr(self.model_class, self.primary_key) == self._get_primary_key_value(entity)
            ).scalar()
            
            if current is not None and current != entity.version:
                raise OptimisticLockException(
                    self._get_entity_name(),
                    self._get_primary_key_value(entity),
                    entity.version
                )
            
            entity.version += 1
        
        super()._before_update(entity)


class CacheableMixin:
    """Mixin for cacheable repositories."""
    
    def __init__(self, *args, cache_ttl: int = 300, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_ttl = cache_ttl
        self._cache = {}
    
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """Generate cache key for method call."""
        key_parts = [method]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, key: str):
        """Get item from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if (datetime.utcnow() - timestamp).total_seconds() < self.cache_ttl:
                return value
            else:
                del self._cache[key]
        return None
    
    def _put_in_cache(self, key: str, value: Any):
        """Put item in cache."""
        self._cache[key] = (value, datetime.utcnow())
    
    def _clear_cache(self):
        """Clear all cache."""
        self._cache.clear()
    
    def get(self, id: ID) -> Optional[T]:
        """Get with caching."""
        cache_key = self._get_cache_key("get", id)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        entity = super().get(id)
        if entity:
            self._put_in_cache(cache_key, entity)
        return entity
    
    def create(self, entity: T) -> T:
        """Create and invalidate cache."""
        result = super().create(entity)
        self._clear_cache()
        return result
    
    def update(self, id: ID, **kwargs) -> Optional[T]:
        """Update and invalidate cache."""
        result = super().update(id, **kwargs)
        self._clear_cache()
        return result
    
    def delete(self, id: ID) -> bool:
        """Delete and invalidate cache."""
        result = super().delete(id)
        self._clear_cache()
        return result


class SearchableMixin:
    """Mixin for searchable repositories."""
    
    def search(self, query: str, fields: Optional[List[str]] = None, limit: int = 20) -> List[T]:
        """
        Search entities by text query.
        
        Args:
            query: Search query string
            fields: Specific fields to search (if None, uses default searchable fields)
            limit: Maximum number of results
        """
        searchable_fields = fields or self._get_searchable_fields()
        
        try:
            qb = self.query().search(query, searchable_fields)
            if limit > 0:
                qb.limit(limit)
            return qb.all()
        except Exception as e:
            self._handle_error(e, "search", {"query": query, "fields": fields})
    
    def _get_searchable_fields(self) -> List[str]:
        """
        Get default searchable fields.
        
        Override this method to specify which fields are searchable.
        """
        return []


class PaginationMixin:
    """Mixin for pagination helpers."""
    
    def paginate(self, page: int = 1, per_page: int = 20, **filters) -> Tuple[List[T], Dict[str, Any]]:
        """
        Paginate results with filters.
        
        Returns:
            Tuple of (items, pagination_info)
        """
        query = self.session.query(self.model_class)
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model_class, key) and value is not None:
                query = query.filter(getattr(self.model_class, key) == value)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1
        
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'next_page': page + 1 if has_next else None,
            'prev_page': page - 1 if has_prev else None
        }
        
        return items, pagination_info


class FilterMixin:
    """Mixin for advanced filtering."""
    
    def filter_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """Filter by complex criteria."""
        query = self.session.query(self.model_class)
        
        for key, value in criteria.items():
            if value is None:
                continue
            
            # Handle special operators
            if key.endswith('__gt'):
                field = key[:-4]
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field) > value)
            elif key.endswith('__gte'):
                field = key[:-5]
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field) >= value)
            elif key.endswith('__lt'):
                field = key[:-4]
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field) < value)
            elif key.endswith('__lte'):
                field = key[:-5]
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field) <= value)
            elif key.endswith('__in'):
                field = key[:-4]
                if hasattr(self.model_class, field) and isinstance(value, (list, tuple)):
                    query = query.filter(getattr(self.model_class, field).in_(value))
            elif key.endswith('__like'):
                field = key[:-6]
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field).like(f"%{value}%"))
            elif key.endswith('__ilike'):
                field = key[:-7]
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field).ilike(f"%{value}%"))
            elif key.endswith('__isnull'):
                field = key[:-8]
                if hasattr(self.model_class, field):
                    if value:
                        query = query.filter(getattr(self.model_class, field).is_(None))
                    else:
                        query = query.filter(getattr(self.model_class, field).isnot(None))
            else:
                # Simple equality
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
        
        return query.all()


class BatchOperationMixin:
    """Mixin for batch operations."""
    
    def batch_create(self, entities: List[T], batch_size: int = 100) -> int:
        """Create entities in batches."""
        total_created = 0
        
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            created = len(self.create_many(batch))
            total_created += created
            
            if i + batch_size < len(entities):
                self.session.commit()
        
        return total_created
    
    def batch_update(self, updates: List[Tuple[ID, Dict[str, Any]]], batch_size: int = 100) -> int:
        """Update entities in batches."""
        total_updated = 0
        
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            for entity_id, values in batch:
                if self.update(entity_id, **values):
                    total_updated += 1
            
            if i + batch_size < len(updates):
                self.session.commit()
        
        return total_updated
    
    def batch_delete(self, ids: List[ID], batch_size: int = 100) -> int:
        """Delete entities in batches."""
        total_deleted = 0
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            for entity_id in batch_ids:
                if self.delete(entity_id):
                    total_deleted += 1
            
            if i + batch_size < len(ids):
                self.session.commit()
        
        return total_deleted


class TransactionMixin:
    """Mixin for transaction management."""
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions."""
        try:
            yield
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
    
    def in_transaction(self, func: Callable, *args, **kwargs):
        """Execute a function within a transaction."""
        with self.transaction():
            return func(*args, **kwargs)
    
    async def in_transaction_async(self, func: Callable[..., Awaitable], *args, **kwargs):
        """Execute an async function within a transaction."""
        with self.transaction():
            return await func(*args, **kwargs)


# ============================================================================
# Combined Repository Classes
# ============================================================================

class SoftDeleteRepository(SoftDeleteMixin, BaseRepository[T, ID]):
    """Repository with soft delete support."""
    pass


class TimestampedRepository(TimestampMixin, BaseRepository[T, ID]):
    """Repository with timestamp support."""
    pass


class AuditableRepository(AuditMixin, TimestampMixin, BaseRepository[T, ID]):
    """Repository with audit and timestamp support."""
    pass


class VersionedRepository(VersionedMixin, BaseRepository[T, ID]):
    """Repository with optimistic locking support."""
    pass


class CacheableRepository(CacheableMixin, BaseRepository[T, ID]):
    """Repository with caching support."""
    pass


class SearchableRepository(SearchableMixin, BaseRepository[T, ID]):
    """Repository with search support."""
    pass


class FullFeatureRepository(
    SoftDeleteMixin,
    TimestampMixin,
    AuditMixin,
    VersionedMixin,
    CacheableMixin,
    SearchableMixin,
    PaginationMixin,
    FilterMixin,
    BatchOperationMixin,
    TransactionMixin,
    BaseRepository[T, ID]
):
    """
    Full-featured repository with all mixins.
    
    This repository combines all functionality for entities that need
    comprehensive features like soft delete, auditing, versioning, etc.
    """
    pass


# ============================================================================
# Repository Factory
# ============================================================================

class RepositoryFactory:
    """
    Factory for creating and caching repository instances.
    """
    
    _instances: Dict[str, BaseRepository] = {}
    
    @classmethod
    def get_repository(cls, repo_class: Type[BaseRepository], session: Session, **kwargs) -> BaseRepository:
        """
        Get or create a repository instance.
        
        Args:
            repo_class: The repository class to instantiate
            session: SQLAlchemy session
            **kwargs: Additional arguments for repository initialization
        
        Returns:
            Repository instance
        """
        # Create a cache key based on class and session id
        cache_key = f"{repo_class.__name__}:{id(session)}"
        
        if cache_key not in cls._instances:
            cls._instances[cache_key] = repo_class(session, **kwargs)
        
        return cls._instances[cache_key]
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached repository instances."""
        cls._instances.clear()


# ============================================================================
# Utility function for creating paginated responses
# ============================================================================

def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    per_page: int,
    item_serializer: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Create a standardized paginated response.
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number
        per_page: Items per page
        item_serializer: Optional function to serialize items
    
    Returns:
        Paginated response dictionary
    """
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    serialized_items = [
        item_serializer(item) if item_serializer else item
        for item in items
    ]
    
    return {
        'data': serialized_items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'next_page': page + 1 if has_next else None,
            'prev_page': page - 1 if has_prev else None
        }
    }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Base Classes
    'BaseRepository',
    'IRepository',
    
    # Mixins
    'SoftDeleteMixin',
    'TimestampMixin',
    'AuditMixin',
    'VersionedMixin',
    'CacheableMixin',
    'SearchableMixin',
    'PaginationMixin',
    'FilterMixin',
    'BatchOperationMixin',
    'TransactionMixin',
    
    # Combined Classes
    'SoftDeleteRepository',
    'TimestampedRepository',
    'AuditableRepository',
    'VersionedRepository',
    'CacheableRepository',
    'SearchableRepository',
    'FullFeatureRepository',
    
    # Query Builder
    'QueryBuilder',
    
    # Factory
    'RepositoryFactory',
    
    # Exceptions
    'RepositoryException',
    'EntityNotFoundException',
    'DuplicateEntityException',
    'ValidationException',
    'ConstraintViolationException',
    'OptimisticLockException',
    'ConcurrencyException',
    'DataIntegrityException',
    
    # Utilities
    'create_paginated_response',
]