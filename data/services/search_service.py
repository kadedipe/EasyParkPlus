# parking-management/data/services/search_service.py
"""
Search service module for the parking management system.

This module provides comprehensive search functionality across all domains
with advanced filtering, full-text search, faceted search, and result ranking.
"""

from typing import (
    List, Optional, Dict, Any, Tuple, Union, Callable, TypeVar, Generic,
    Set, Iterator
)
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
import re
from enum import Enum
from functools import reduce
import operator

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    String, Integer, Float, Boolean, DateTime, Date,
    Text, cast, union, literal
)
from sqlalchemy.orm import Session, Query
from sqlalchemy.sql.expression import text

from ..repositories import (
    UserRepository,
    VehicleRepository,
    ParkingSpotRepository,
    ReservationRepository,
    PaymentRepository,
    AuditLogRepository
)
from .base_service import BaseService, ServiceException, with_retry
from ..models.enums import (
    # Domain enums for filtering
    UserStatus,
    UserRole,
    VehicleStatus,
    VehicleType,
    SpotType,
    SpotStatus,
    ReservationStatus,
    PaymentStatus,
    AuditSeverity,
    
    # Search enums
    SearchOperator,
    SortOrder,
    SearchScope,
    ResultFormat
)

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# Custom Exceptions
# ============================================================================

class SearchServiceException(ServiceException):
    """Base exception for search service."""
    pass


class InvalidSearchQueryException(SearchServiceException):
    """Raised when search query is invalid."""
    pass


class UnsupportedSearchScopeException(SearchServiceException):
    """Raised when search scope is not supported."""
    pass


class SearchIndexException(SearchServiceException):
    """Raised when search index operation fails."""
    pass


# ============================================================================
# Search Models
# ============================================================================

class SearchFilter:
    """
    Represents a search filter condition.
    
    Examples:
        SearchFilter(field='status', operator='eq', value='active')
        SearchFilter(field='created_at', operator='between', value=['2024-01-01', '2024-12-31'])
        SearchFilter(field='amount', operator='gt', value=100)
    """
    
    def __init__(
        self,
        field: str,
        operator: str,
        value: Any,
        boolean: str = 'and'
    ):
        """
        Initialize a search filter.
        
        Args:
            field: Field name to filter on
            operator: Comparison operator (eq, ne, gt, lt, gte, lte, contains, in, between)
            value: Value to compare against
            boolean: Boolean operator (and, or) for combining with other filters
        """
        self.field = field
        self.operator = operator
        self.value = value
        self.boolean = boolean
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'field': self.field,
            'operator': self.operator,
            'value': self.value,
            'boolean': self.boolean
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchFilter':
        """Create from dictionary."""
        return cls(
            field=data['field'],
            operator=data['operator'],
            value=data['value'],
            boolean=data.get('boolean', 'and')
        )


class SearchSort:
    """Represents a sort specification."""
    
    def __init__(
        self,
        field: str,
        order: str = 'asc'
    ):
        """
        Initialize a sort specification.
        
        Args:
            field: Field to sort by
            order: Sort order ('asc' or 'desc')
        """
        self.field = field
        self.order = order
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'field': self.field,
            'order': self.order
        }


class SearchQuery:
    """
    Represents a complete search query.
    
    Supports:
    - Full-text search
    - Field-specific filters
    - Sorting
    - Pagination
    - Faceting
    - Highlighting
    """
    
    def __init__(
        self,
        query: Optional[str] = None,
        scope: Union[str, List[str]] = 'all',
        filters: Optional[List[Union[Dict, SearchFilter]]] = None,
        sorts: Optional[List[Union[Dict, SearchSort]]] = None,
        page: int = 1,
        page_size: int = 20,
        fields: Optional[List[str]] = None,
        facets: Optional[List[str]] = None,
        highlight: bool = False,
        explain: bool = False
    ):
        """
        Initialize a search query.
        
        Args:
            query: Full-text search query
            scope: Search scope(s) (users, vehicles, spots, reservations, payments, all)
            filters: List of filters
            sorts: List of sort specifications
            page: Page number (1-based)
            page_size: Number of results per page
            fields: Fields to return (None for all)
            facets: Fields to generate facets for
            highlight: Whether to highlight matches
            explain: Whether to include explanation
        """
        self.query = query
        self.scope = scope if isinstance(scope, list) else [scope]
        self.filters = []
        self.sorts = []
        self.page = page
        self.page_size = min(page_size, 100)  # Max 100 per page
        self.fields = fields
        self.facets = facets or []
        self.highlight = highlight
        self.explain = explain
        
        # Parse filters
        if filters:
            for f in filters:
                if isinstance(f, dict):
                    self.filters.append(SearchFilter.from_dict(f))
                elif isinstance(f, SearchFilter):
                    self.filters.append(f)
        
        # Parse sorts
        if sorts:
            for s in sorts:
                if isinstance(s, dict):
                    self.sorts.append(SearchSort(**s))
                elif isinstance(s, SearchSort):
                    self.sorts.append(s)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query': self.query,
            'scope': self.scope,
            'filters': [f.to_dict() for f in self.filters],
            'sorts': [s.to_dict() for s in self.sorts],
            'page': self.page,
            'page_size': self.page_size,
            'fields': self.fields,
            'facets': self.facets,
            'highlight': self.highlight,
            'explain': self.explain
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchQuery':
        """Create from dictionary."""
        return cls(
            query=data.get('query'),
            scope=data.get('scope', 'all'),
            filters=data.get('filters', []),
            sorts=data.get('sorts', []),
            page=data.get('page', 1),
            page_size=data.get('page_size', 20),
            fields=data.get('fields'),
            facets=data.get('facets', []),
            highlight=data.get('highlight', False),
            explain=data.get('explain', False)
        )


class SearchResult:
    """Represents a single search result."""
    
    def __init__(
        self,
        id: Any,
        type: str,
        score: float,
        data: Dict[str, Any],
        highlights: Optional[Dict[str, List[str]]] = None
    ):
        self.id = id
        self.type = type
        self.score = score
        self.data = data
        self.highlights = highlights or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'type': self.type,
            'score': self.score,
            'data': self.data,
            'highlights': self.highlights
        }


class SearchResponse:
    """Represents a complete search response."""
    
    def __init__(
        self,
        results: List[SearchResult],
        total: int,
        page: int,
        page_size: int,
        facets: Optional[Dict[str, Dict[Any, int]]] = None,
        suggestion: Optional[str] = None,
        took_ms: int = 0,
        explain: Optional[Dict] = None
    ):
        self.results = results
        self.total = total
        self.page = page
        self.page_size = page_size
        self.facets = facets or {}
        self.suggestion = suggestion
        self.took_ms = took_ms
        self.explain = explain
        
        self.total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        self.has_next = page < self.total_pages
        self.has_prev = page > 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'results': [r.to_dict() for r in self.results],
            'total': self.total,
            'page': self.page,
            'page_size': self.page_size,
            'total_pages': self.total_pages,
            'has_next': self.has_next,
            'has_prev': self.has_prev,
            'facets': self.facets,
            'suggestion': self.suggestion,
            'took_ms': self.took_ms,
            'explain': self.explain
        }


# ============================================================================
# Search Index
# ============================================================================

class SearchIndex:
    """
    Search index for a specific entity type.
    
    Manages indexing, searching, and faceting for a domain entity.
    """
    
    def __init__(
        self,
        name: str,
        entity_type: str,
        repository: Any,
        searchable_fields: List[str],
        filterable_fields: List[str],
        sortable_fields: List[str],
        facet_fields: List[str],
        field_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize a search index.
        
        Args:
            name: Index name
            entity_type: Entity type identifier
            repository: Repository for the entity
            searchable_fields: Fields that can be full-text searched
            filterable_fields: Fields that can be filtered
            sortable_fields: Fields that can be sorted
            facet_fields: Fields that can be faceted
            field_weights: Weights for scoring (higher = more important)
        """
        self.name = name
        self.entity_type = entity_type
        self.repository = repository
        self.searchable_fields = searchable_fields
        self.filterable_fields = filterable_fields
        self.sortable_fields = sortable_fields
        self.facet_fields = facet_fields
        self.field_weights = field_weights or {
            field: 1.0 for field in searchable_fields
        }
    
    def build_query(
        self,
        search_query: SearchQuery,
        base_query: Optional[Query] = None
    ) -> Query:
        """
        Build a SQLAlchemy query from a search query.
        
        Args:
            search_query: Search query
            base_query: Optional base query to start from
            
        Returns:
            SQLAlchemy query
        """
        model = self.repository.model_class
        query = base_query or self.repository.session.query(model)
        
        # Apply filters
        for filter_ in search_query.filters:
            if filter_.field in self.filterable_fields:
                query = self._apply_filter(query, model, filter_)
        
        # Apply full-text search
        if search_query.query:
            query = self._apply_full_text_search(query, model, search_query.query)
        
        # Apply sorting
        if search_query.sorts:
            for sort in search_query.sorts:
                if sort.field in self.sortable_fields:
                    column = getattr(model, sort.field)
                    if sort.order.lower() == 'desc':
                        query = query.order_by(desc(column))
                    else:
                        query = query.order_by(asc(column))
        else:
            # Default sort by relevance if search query, otherwise by id
            if search_query.query:
                query = query.order_by(desc(text('relevance')))
            else:
                query = query.order_by(desc(model.id))
        
        return query
    
    def _apply_filter(
        self,
        query: Query,
        model: Any,
        filter_: SearchFilter
    ) -> Query:
        """Apply a single filter to the query."""
        column = getattr(model, filter_.field)
        
        if filter_.operator == 'eq':
            return query.filter(column == filter_.value)
        elif filter_.operator == 'ne':
            return query.filter(column != filter_.value)
        elif filter_.operator == 'gt':
            return query.filter(column > filter_.value)
        elif filter_.operator == 'lt':
            return query.filter(column < filter_.value)
        elif filter_.operator == 'gte':
            return query.filter(column >= filter_.value)
        elif filter_.operator == 'lte':
            return query.filter(column <= filter_.value)
        elif filter_.operator == 'contains':
            return query.filter(column.contains(filter_.value))
        elif filter_.operator == 'icontains':
            return query.filter(column.ilike(f'%{filter_.value}%'))
        elif filter_.operator == 'startswith':
            return query.filter(column.startswith(filter_.value))
        elif filter_.operator == 'endswith':
            return query.filter(column.endswith(filter_.value))
        elif filter_.operator == 'in':
            return query.filter(column.in_(filter_.value))
        elif filter_.operator == 'not_in':
            return query.filter(~column.in_(filter_.value))
        elif filter_.operator == 'between':
            return query.filter(column.between(filter_.value[0], filter_.value[1]))
        elif filter_.operator == 'is_null':
            return query.filter(column.is_(None)) if filter_.value else query.filter(column.isnot(None))
        
        return query
    
    def _apply_full_text_search(
        self,
        query: Query,
        model: Any,
        search_term: str
    ) -> Query:
        """Apply full-text search to the query."""
        # Split search term into keywords
        keywords = search_term.lower().split()
        
        # Build search conditions
        conditions = []
        for field in self.searchable_fields:
            column = getattr(model, field)
            if hasattr(column, 'type') and isinstance(column.type, (String, Text)):
                field_conditions = []
                for keyword in keywords:
                    field_conditions.append(column.ilike(f'%{keyword}%'))
                if field_conditions:
                    conditions.append(or_(*field_conditions))
        
        if conditions:
            query = query.filter(or_(*conditions))
        
        # Calculate relevance score
        if hasattr(model, 'id'):
            # Add a relevance column for sorting
            relevance_cases = []
            for i, field in enumerate(self.searchable_fields):
                column = getattr(model, field)
                weight = self.field_weights.get(field, 1.0)
                
                for keyword in keywords:
                    # Exact match gets highest score
                    exact_match = func.lower(column) == keyword.lower()
                    # Contains match gets medium score
                    contains_match = column.ilike(f'%{keyword}%')
                    
                    relevance_cases.append(
                        func.cast(exact_match, Integer) * weight * 10
                    )
                    relevance_cases.append(
                        func.cast(contains_match, Integer) * weight
                    )
            
            if relevance_cases:
                relevance = reduce(operator.add, relevance_cases)
                query = query.add_columns(relevance.label('relevance'))
        
        return query
    
    def extract_facets(
        self,
        query: Query,
        facet_fields: List[str]
    ) -> Dict[str, Dict[Any, int]]:
        """
        Extract facet counts from a query.
        
        Args:
            query: Base query
            facet_fields: Fields to generate facets for
            
        Returns:
            Dictionary mapping field to value counts
        """
        facets = {}
        model = self.repository.model_class
        
        for field in facet_fields:
            if field in self.facet_fields:
                column = getattr(model, field)
                
                # Get count by value
                facet_query = (
                    self.repository.session.query(
                        column,
                        func.count(model.id).label('count')
                    )
                    .filter(model.id.in_(query.subquery().select().with_only_columns([model.id])))
                    .group_by(column)
                    .order_by(desc('count'))
                    .limit(20)  # Limit to top 20 facet values
                )
                
                facets[field] = {
                    str(row[0]): row[1] for row in facet_query.all()
                    if row[0] is not None
                }
        
        return facets
    
    def get_suggestion(
        self,
        search_term: str
    ) -> Optional[str]:
        """
        Get a suggested correction for a search term.
        
        Args:
            search_term: Original search term
            
        Returns:
            Suggested term or None
        """
        # This would implement spell correction logic
        # For now, return None
        return None
    
    def format_result(
        self,
        item: Any,
        fields: Optional[List[str]] = None,
        highlight: bool = False,
        search_term: Optional[str] = None
    ) -> SearchResult:
        """
        Format a result item.
        
        Args:
            item: Database item
            fields: Fields to include
            highlight: Whether to highlight matches
            search_term: Search term for highlighting
            
        Returns:
            Formatted search result
        """
        # Convert to dictionary
        if hasattr(item, 'to_dict'):
            data = item.to_dict()
        else:
            # Basic conversion
            data = {}
            for column in item.__table__.columns:
                if fields is None or column.name in fields:
                    value = getattr(item, column.name)
                    if isinstance(value, (datetime, date)):
                        value = value.isoformat()
                    elif isinstance(value, Enum):
                        value = value.value
                    data[column.name] = value
        
        # Generate highlights
        highlights = {}
        if highlight and search_term:
            keywords = search_term.lower().split()
            for field in self.searchable_fields:
                if field in data and data[field]:
                    field_value = str(data[field])
                    highlighted = self._highlight_text(field_value, keywords)
                    if highlighted != field_value:
                        highlights[field] = [highlighted]
        
        # Calculate score (simplified)
        score = 1.0
        if hasattr(item, 'relevance'):
            score = float(item.relevance)
        
        return SearchResult(
            id=item.id,
            type=self.entity_type,
            score=score,
            data=data,
            highlights=highlights
        )
    
    def _highlight_text(self, text: str, keywords: List[str]) -> str:
        """Highlight keywords in text."""
        for keyword in keywords:
            pattern = re.compile(f'({re.escape(keyword)})', re.IGNORECASE)
            text = pattern.sub(r'<em>\1</em>', text)
        return text


# ============================================================================
# Search Service
# ============================================================================

class SearchService(BaseService):
    """
    Comprehensive search service for all domains.
    
    Provides unified search across users, vehicles, parking spots,
    reservations, payments, and audit logs with advanced features.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the search service.
        
        Args:
            session: SQLAlchemy session
        """
        super().__init__(session)
        
        # Initialize repositories
        self.user_repo = UserRepository(session)
        self.vehicle_repo = VehicleRepository(session)
        self.spot_repo = ParkingSpotRepository(session)
        self.reservation_repo = ReservationRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.audit_repo = AuditLogRepository(session)
        
        # Initialize search indexes
        self.indexes = self._init_indexes()
        
        logger.info(f"SearchService initialized with {len(self.indexes)} indexes")
    
    def _init_indexes(self) -> Dict[str, SearchIndex]:
        """Initialize search indexes for all domains."""
        return {
            'users': SearchIndex(
                name='users',
                entity_type='user',
                repository=self.user_repo,
                searchable_fields=['email', 'username', 'first_name', 'last_name', 'phone'],
                filterable_fields=['status', 'role', 'created_at', 'email_verified', 'mfa_enabled'],
                sortable_fields=['id', 'email', 'created_at', 'last_login_at'],
                facet_fields=['status', 'role'],
                field_weights={
                    'email': 2.0,
                    'username': 1.5,
                    'first_name': 1.0,
                    'last_name': 1.0,
                    'phone': 1.0
                }
            ),
            'vehicles': SearchIndex(
                name='vehicles',
                entity_type='vehicle',
                repository=self.vehicle_repo,
                searchable_fields=['license_plate', 'vin', 'make', 'model', 'color'],
                filterable_fields=['status', 'vehicle_type', 'fuel_type', 'year', 'created_at'],
                sortable_fields=['id', 'year', 'created_at', 'license_plate'],
                facet_fields=['status', 'vehicle_type', 'fuel_type', 'make'],
                field_weights={
                    'license_plate': 3.0,
                    'vin': 2.5,
                    'make': 1.5,
                    'model': 1.5,
                    'color': 0.5
                }
            ),
            'parking_spots': SearchIndex(
                name='parking_spots',
                entity_type='parking_spot',
                repository=self.spot_repo,
                searchable_fields=['spot_number', 'location_description', 'notes'],
                filterable_fields=['status', 'spot_type', 'zone_id', 'is_covered', 'has_ev_charging'],
                sortable_fields=['id', 'spot_number', 'created_at'],
                facet_fields=['status', 'spot_type', 'zone_id'],
                field_weights={
                    'spot_number': 2.0,
                    'location_description': 1.0
                }
            ),
            'reservations': SearchIndex(
                name='reservations',
                entity_type='reservation',
                repository=self.reservation_repo,
                searchable_fields=['confirmation_code', 'notes'],
                filterable_fields=['status', 'reservation_type', 'user_id', 'spot_id', 
                                 'vehicle_id', 'start_time', 'end_time', 'created_at'],
                sortable_fields=['id', 'start_time', 'end_time', 'created_at', 'total_amount'],
                facet_fields=['status', 'reservation_type'],
                field_weights={
                    'confirmation_code': 3.0,
                    'notes': 0.5
                }
            ),
            'payments': SearchIndex(
                name='payments',
                entity_type='payment',
                repository=self.payment_repo,
                searchable_fields=['transaction_id', 'description'],
                filterable_fields=['status', 'payment_method', 'currency', 'user_id', 
                                 'created_at', 'amount'],
                sortable_fields=['id', 'amount', 'created_at'],
                facet_fields=['status', 'payment_method', 'currency'],
                field_weights={
                    'transaction_id': 3.0,
                    'description': 0.5
                }
            ),
            'audit_logs': SearchIndex(
                name='audit_logs',
                entity_type='audit_log',
                repository=self.audit_repo,
                searchable_fields=['actor_email', 'actor_name', 'resource_id', 'ip_address'],
                filterable_fields=['action', 'category', 'severity', 'resource_type', 
                                 'actor_id', 'created_at'],
                sortable_fields=['id', 'created_at'],
                facet_fields=['action', 'category', 'severity', 'resource_type'],
                field_weights={
                    'actor_email': 1.5,
                    'actor_name': 1.0,
                    'resource_id': 1.0,
                    'ip_address': 0.5
                }
            )
        }
    
    # ========================================================================
    # Main Search Methods
    # ========================================================================
    
    @with_retry(max_retries=2)
    def search(
        self,
        query: Union[str, Dict, SearchQuery]
    ) -> SearchResponse:
        """
        Perform a unified search across all domains.
        
        Args:
            query: Search query (string, dict, or SearchQuery object)
            
        Returns:
            Search response with results and metadata
            
        Raises:
            InvalidSearchQueryException: If query is invalid
            UnsupportedSearchScopeException: If scope is not supported
        """
        import time
        start_time = time.time()
        
        # Parse query
        if isinstance(query, str):
            search_query = SearchQuery(query=query)
        elif isinstance(query, dict):
            search_query = SearchQuery.from_dict(query)
        elif isinstance(query, SearchQuery):
            search_query = query
        else:
            raise InvalidSearchQueryException(f"Invalid query type: {type(query)}")
        
        # Validate scopes
        valid_scopes = list(self.indexes.keys()) + ['all']
        for scope in search_query.scope:
            if scope not in valid_scopes:
                raise UnsupportedSearchScopeException(f"Unsupported scope: {scope}")
        
        results = []
        total = 0
        all_facets = {}
        
        # Determine which indexes to search
        indexes_to_search = []
        if 'all' in search_query.scope:
            indexes_to_search = list(self.indexes.values())
        else:
            indexes_to_search = [
                self.indexes[scope] for scope in search_query.scope
                if scope in self.indexes
            ]
        
        # Search each index
        for index in indexes_to_search:
            index_results, index_total, index_facets = self._search_index(
                index, search_query
            )
            
            results.extend(index_results)
            total += index_total
            
            # Merge facets
            for field, counts in index_facets.items():
                if field not in all_facets:
                    all_facets[field] = {}
                all_facets[field].update(counts)
        
        # Sort combined results by score
        results.sort(key=lambda r: r.score, reverse=True)
        
        # Apply pagination
        start = (search_query.page - 1) * search_query.page_size
        end = start + search_query.page_size
        paginated_results = results[start:end]
        
        # Get suggestion if no results
        suggestion = None
        if total == 0 and search_query.query:
            suggestion = self._get_suggestion(search_query.query, indexes_to_search)
        
        took_ms = int((time.time() - start_time) * 1000)
        
        return SearchResponse(
            results=paginated_results,
            total=total,
            page=search_query.page,
            page_size=search_query.page_size,
            facets=all_facets,
            suggestion=suggestion,
            took_ms=took_ms,
            explain={'query': search_query.to_dict()} if search_query.explain else None
        )
    
    def _search_index(
        self,
        index: SearchIndex,
        search_query: SearchQuery
    ) -> Tuple[List[SearchResult], int, Dict[str, Dict[Any, int]]]:
        """
        Search a single index.
        
        Returns:
            Tuple of (results, total_count, facets)
        """
        # Build query
        query = index.build_query(search_query)
        
        # Get total count
        count_query = query.subquery()
        total = self.session.query(func.count()).select_from(count_query).scalar() or 0
        
        # Get facets if requested
        facets = {}
        if search_query.facets:
            facets = index.extract_facets(query, search_query.facets)
        
        # Apply pagination
        query = query.limit(search_query.page_size).offset(
            (search_query.page - 1) * search_query.page_size
        )
        
        # Execute query
        items = query.all()
        
        # Format results
        results = [
            index.format_result(
                item[0] if isinstance(item, tuple) else item,
                fields=search_query.fields,
                highlight=search_query.highlight,
                search_term=search_query.query
            )
            for item in items
        ]
        
        return results, total, facets
    
    def _get_suggestion(
        self,
        search_term: str,
        indexes: List[SearchIndex]
    ) -> Optional[str]:
        """Get search suggestion from indexes."""
        for index in indexes:
            suggestion = index.get_suggestion(search_term)
            if suggestion:
                return suggestion
        return None
    
    # ========================================================================
    # Domain-Specific Search Methods
    # ========================================================================
    
    def search_users(
        self,
        query: Optional[str] = None,
        filters: Optional[List[Dict]] = None,
        sorts: Optional[List[Dict]] = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs
    ) -> SearchResponse:
        """
        Search users only.
        
        Args:
            query: Search query
            filters: List of filters
            sorts: List of sort specifications
            page: Page number
            page_size: Items per page
            **kwargs: Additional search parameters
            
        Returns:
            Search response
        """
        search_query = SearchQuery(
            query=query,
            scope=['users'],
            filters=filters,
            sorts=sorts,
            page=page,
            page_size=page_size,
            **kwargs
        )
        return self.search(search_query)
    
    def search_vehicles(
        self,
        query: Optional[str] = None,
        filters: Optional[List[Dict]] = None,
        sorts: Optional[List[Dict]] = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs
    ) -> SearchResponse:
        """Search vehicles only."""
        search_query = SearchQuery(
            query=query,
            scope=['vehicles'],
            filters=filters,
            sorts=sorts,
            page=page,
            page_size=page_size,
            **kwargs
        )
        return self.search(search_query)
    
    def search_parking_spots(
        self,
        query: Optional[str] = None,
        filters: Optional[List[Dict]] = None,
        sorts: Optional[List[Dict]] = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs
    ) -> SearchResponse:
        """Search parking spots only."""
        search_query = SearchQuery(
            query=query,
            scope=['parking_spots'],
            filters=filters,
            sorts=sorts,
            page=page,
            page_size=page_size,
            **kwargs
        )
        return self.search(search_query)
    
    def search_reservations(
        self,
        query: Optional[str] = None,
        filters: Optional[List[Dict]] = None,
        sorts: Optional[List[Dict]] = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs
    ) -> SearchResponse:
        """Search reservations only."""
        search_query = SearchQuery(
            query=query,
            scope=['reservations'],
            filters=filters,
            sorts=sorts,
            page=page,
            page_size=page_size,
            **kwargs
        )
        return self.search(search_query)
    
    def search_payments(
        self,
        query: Optional[str] = None,
        filters: Optional[List[Dict]] = None,
        sorts: Optional[List[Dict]] = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs
    ) -> SearchResponse:
        """Search payments only."""
        search_query = SearchQuery(
            query=query,
            scope=['payments'],
            filters=filters,
            sorts=sorts,
            page=page,
            page_size=page_size,
            **kwargs
        )
        return self.search(search_query)
    
    def search_audit_logs(
        self,
        query: Optional[str] = None,
        filters: Optional[List[Dict]] = None,
        sorts: Optional[List[Dict]] = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs
    ) -> SearchResponse:
        """Search audit logs only."""
        search_query = SearchQuery(
            query=query,
            scope=['audit_logs'],
            filters=filters,
            sorts=sorts,
            page=page,
            page_size=page_size,
            **kwargs
        )
        return self.search(search_query)
    
    # ========================================================================
    # Advanced Search Features
    # ========================================================================
    
    def suggest(
        self,
        prefix: str,
        scope: Union[str, List[str]] = 'all',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get search suggestions as you type.
        
        Args:
            prefix: Prefix to match
            scope: Search scope(s)
            limit: Maximum suggestions per scope
            
        Returns:
            List of suggestions with metadata
        """
        suggestions = []
        
        # Determine scopes
        scopes = [scope] if isinstance(scope, str) else scope
        if 'all' in scopes:
            scopes = list(self.indexes.keys())
        
        for scope_name in scopes:
            if scope_name not in self.indexes:
                continue
            
            index = self.indexes[scope_name]
            
            # Build prefix query
            search_query = SearchQuery(
                query=prefix,
                scope=[scope_name],
                page_size=limit
            )
            
            # Search
            results, _, _ = self._search_index(index, search_query)
            
            # Format suggestions
            for result in results[:limit]:
                suggestions.append({
                    'type': result.type,
                    'id': result.id,
                    'text': self._format_suggestion_text(result),
                    'data': result.data
                })
        
        return suggestions
    
    def _format_suggestion_text(self, result: SearchResult) -> str:
        """Format result as suggestion text."""
        if result.type == 'user':
            return f"{result.data.get('first_name', '')} {result.data.get('last_name', '')} ({result.data.get('email', '')})"
        elif result.type == 'vehicle':
            return f"{result.data.get('license_plate')} - {result.data.get('make')} {result.data.get('model')}"
        elif result.type == 'parking_spot':
            return f"Spot {result.data.get('spot_number')} (Zone {result.data.get('zone_id')})"
        elif result.type == 'reservation':
            return f"Reservation {result.data.get('confirmation_code')}"
        elif result.type == 'payment':
            return f"Payment {result.data.get('transaction_id')}"
        elif result.type == 'audit_log':
            return f"Audit: {result.data.get('action')} by {result.data.get('actor_email')}"
        return str(result.id)
    
    def explain(
        self,
        query: Union[str, Dict, SearchQuery]
    ) -> Dict[str, Any]:
        """
        Explain how a search query will be executed.
        
        Args:
            query: Search query
            
        Returns:
            Query execution plan explanation
        """
        # Parse query
        if isinstance(query, str):
            search_query = SearchQuery(query=query, explain=True)
        elif isinstance(query, dict):
            search_query = SearchQuery.from_dict(query)
            search_query.explain = True
        elif isinstance(query, SearchQuery):
            search_query = query
            search_query.explain = True
        
        explanation = {
            'query': search_query.to_dict(),
            'indexes': [],
            'estimated_total': 0
        }
        
        # Determine indexes
        indexes_to_explain = []
        if 'all' in search_query.scope:
            indexes_to_explain = list(self.indexes.values())
        else:
            indexes_to_explain = [
                self.indexes[scope] for scope in search_query.scope
                if scope in self.indexes
            ]
        
        for index in indexes_to_explain:
            # Build query to get SQL
            query = index.build_query(search_query)
            sql = str(query.statement.compile(
                compile_kwargs={"literal_binds": True}
            ))
            
            # Estimate rows
            count_query = query.subquery()
            estimated = self.session.query(func.count()).select_from(count_query).scalar() or 0
            
            explanation['indexes'].append({
                'name': index.name,
                'entity_type': index.entity_type,
                'sql': sql,
                'estimated_rows': estimated,
                'searchable_fields': index.searchable_fields,
                'filterable_fields': index.filterable_fields
            })
            
            explanation['estimated_total'] += estimated
        
        return explanation
    
    # ========================================================================
    # Search Index Management
    # ========================================================================
    
    def reindex_all(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Reindex all data.
        
        Args:
            batch_size: Number of items to process per batch
            
        Returns:
            Dictionary with reindex counts per entity type
        """
        results = {}
        
        for name, index in self.indexes.items():
            try:
                count = self.reindex_entity(name, batch_size)
                results[name] = count
                logger.info(f"Reindexed {count} {name}")
            except Exception as e:
                logger.error(f"Failed to reindex {name}: {e}")
                results[name] = -1
        
        return results
    
    def reindex_entity(
        self,
        entity_type: str,
        batch_size: int = 100
    ) -> int:
        """
        Reindex a specific entity type.
        
        Args:
            entity_type: Entity type to reindex
            batch_size: Batch size for processing
            
        Returns:
            Number of items reindexed
            
        Raises:
            SearchIndexException: If reindexing fails
        """
        if entity_type not in self.indexes:
            raise UnsupportedSearchScopeException(f"Unknown entity type: {entity_type}")
        
        index = self.indexes[entity_type]
        repo = index.repository
        
        try:
            # Get all items
            items = repo.get_all()
            total = len(items)
            
            # Process in batches
            for i in range(0, total, batch_size):
                batch = items[i:i+batch_size]
                self._index_batch(index, batch)
                logger.debug(f"Indexed batch {i//batch_size + 1} of {entity_type}")
            
            return total
            
        except Exception as e:
            raise SearchIndexException(f"Failed to reindex {entity_type}: {e}")
    
    def _index_batch(self, index: SearchIndex, items: List[Any]) -> None:
        """
        Index a batch of items.
        
        This would typically update a search engine like Elasticsearch.
        For now, it's a placeholder.
        """
        # Placeholder for actual indexing logic
        pass
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_searchable_fields(self, entity_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get searchable fields for entity types.
        
        Args:
            entity_type: Optional entity type to filter
            
        Returns:
            Dictionary mapping entity type to searchable fields
        """
        if entity_type:
            if entity_type in self.indexes:
                return {
                    entity_type: self.indexes[entity_type].searchable_fields
                }
            return {}
        
        return {
            name: index.searchable_fields
            for name, index in self.indexes.items()
        }
    
    def get_filterable_fields(self, entity_type: Optional[str] = None) -> Dict[str, List[str]]:
        """Get filterable fields for entity types."""
        if entity_type:
            if entity_type in self.indexes:
                return {
                    entity_type: self.indexes[entity_type].filterable_fields
                }
            return {}
        
        return {
            name: index.filterable_fields
            for name, index in self.indexes.items()
        }
    
    def get_facet_fields(self, entity_type: Optional[str] = None) -> Dict[str, List[str]]:
        """Get facet fields for entity types."""
        if entity_type:
            if entity_type in self.indexes:
                return {
                    entity_type: self.indexes[entity_type].facet_fields
                }
            return {}
        
        return {
            name: index.facet_fields
            for name, index in self.indexes.items()
        }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main service
    'SearchService',
    
    # Search models
    'SearchFilter',
    'SearchSort',
    'SearchQuery',
    'SearchResult',
    'SearchResponse',
    
    # Search index
    'SearchIndex',
    
    # Exceptions
    'SearchServiceException',
    'InvalidSearchQueryException',
    'UnsupportedSearchScopeException',
    'SearchIndexException',
]