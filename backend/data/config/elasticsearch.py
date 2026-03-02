"""Elasticsearch configuration and client management for the parking management system.

This module provides Elasticsearch connection management, indexing utilities,
search functionality, and specialized clients for different data types
(reservations, users, logs, etc.).
"""

import os
import json
import logging
from typing import Any, Optional, Union, Dict, List, Generator, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import wraps
import hashlib
from enum import Enum

from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import (
    ElasticsearchException,
    ConnectionError,
    NotFoundError,
    RequestError,
    AuthorizationException
)
from elasticsearch_dsl import (
    Document, Integer, Text, Date, Float, Boolean, Keyword,
    Search, Q, Index, connections
)

from . import config, get_current_environment, is_testing, is_development

# Set up logging
logger = logging.getLogger(__name__)


# ============================================================================
# Elasticsearch Configuration
# ============================================================================

class ElasticsearchConfig:
    """Elasticsearch connection configuration."""
    
    def __init__(self, **kwargs):
        """Initialize Elasticsearch configuration with defaults."""
        # Connection settings
        self.hosts = kwargs.get('hosts', ['localhost:9200'])
        self.cloud_id = kwargs.get('cloud_id', os.getenv('ELASTIC_CLOUD_ID'))
        self.api_key = kwargs.get('api_key', os.getenv('ELASTIC_API_KEY'))
        self.username = kwargs.get('username', os.getenv('ELASTIC_USERNAME', 'elastic'))
        self.password = kwargs.get('password', os.getenv('ELASTIC_PASSWORD', ''))
        
        # SSL/TLS settings
        self.use_ssl = kwargs.get('use_ssl', True)
        self.verify_certs = kwargs.get('verify_certs', True)
        self.ca_certs = kwargs.get('ca_certs')
        self.client_cert = kwargs.get('client_cert')
        self.client_key = kwargs.get('client_key')
        
        # Connection pool settings
        self.maxsize = kwargs.get('maxsize', 10)
        self.retry_on_timeout = kwargs.get('retry_on_timeout', True)
        self.timeout = kwargs.get('timeout', 30)
        self.max_retries = kwargs.get('max_retries', 3)
        self.retry_backoff = kwargs.get('retry_backoff', 2)
        
        # Index settings
        self.number_of_shards = kwargs.get('number_of_shards', 1)
        self.number_of_replicas = kwargs.get('number_of_replicas', 1)
        self.refresh_interval = kwargs.get('refresh_interval', '1s')
        
        # Sniffing
        self.sniff_on_start = kwargs.get('sniff_on_start', False)
        self.sniff_on_connection_fail = kwargs.get('sniff_on_connection_fail', False)
        self.sniffer_timeout = kwargs.get('sniffer_timeout', 60)
        
        # Index naming
        self.index_prefix = kwargs.get('index_prefix', 'parking')
        self.index_date_format = kwargs.get('index_date_format', '%Y.%m.%d')
        
        # Application-specific settings
        self.enable_search = kwargs.get('enable_search', True)
        self.enable_logging = kwargs.get('enable_logging', True)
        self.log_index = kwargs.get('log_index', f"{self.index_prefix}-logs")
        self.max_result_window = kwargs.get('max_result_window', 10000)
        self.track_total_hits = kwargs.get('track_total_hits', True)
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for Elasticsearch client."""
        params = {
            'timeout': self.timeout,
            'maxsize': self.maxsize,
            'retry_on_timeout': self.retry_on_timeout,
            'max_retries': self.max_retries,
            'retry_backoff': self.retry_backoff,
            'sniff_on_start': self.sniff_on_start,
            'sniff_on_connection_fail': self.sniff_on_connection_fail,
            'sniffer_timeout': self.sniffer_timeout,
        }
        
        # Hosts
        if self.cloud_id:
            params['cloud_id'] = self.cloud_id
        else:
            params['hosts'] = self.hosts
        
        # Authentication
        if self.api_key:
            params['api_key'] = self.api_key
        elif self.username and self.password:
            params['http_auth'] = (self.username, self.password)
        
        # SSL/TLS
        if self.use_ssl:
            params['use_ssl'] = True
            params['verify_certs'] = self.verify_certs
            if self.ca_certs:
                params['ca_certs'] = self.ca_certs
            if self.client_cert:
                params['client_cert'] = self.client_cert
            if self.client_key:
                params['client_key'] = self.client_key
        
        return params
    
    def get_index_name(self, base_name: str, date_suffix: bool = False) -> str:
        """Get full index name with optional date suffix."""
        name = f"{self.index_prefix}-{base_name}"
        if date_suffix:
            name += f"-{datetime.now().strftime(self.index_date_format)}"
        return name.lower()


# ============================================================================
# Connection Management
# ============================================================================

class ElasticsearchConnectionPool:
    """Singleton manager for Elasticsearch connections."""
    
    _instances: Dict[str, Elasticsearch] = {}
    _configs: Dict[str, ElasticsearchConfig] = {}
    
    @classmethod
    def get_client(cls, name: str = "default", config: Optional[ElasticsearchConfig] = None) -> Elasticsearch:
        """Get or create an Elasticsearch client."""
        if name not in cls._instances:
            if config is None:
                config = ElasticsearchConfig()
            
            cls._configs[name] = config
            cls._instances[name] = Elasticsearch(**config.get_connection_params())
            
            # Test connection
            try:
                cls._instances[name].info()
                logger.info(f"Elasticsearch client '{name}' connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect Elasticsearch client '{name}': {e}")
                if not is_testing():
                    raise
            
            # Configure elasticsearch-dsl
            connections.add_connection(name, cls._instances[name])
        
        return cls._instances[name]
    
    @classmethod
    def get_config(cls, name: str = "default") -> ElasticsearchConfig:
        """Get configuration for a named client."""
        return cls._configs.get(name, ElasticsearchConfig())
    
    @classmethod
    def close_all(cls):
        """Close all Elasticsearch connections."""
        for name, client in cls._instances.items():
            try:
                client.close()
                logger.info(f"Closed Elasticsearch client '{name}'")
            except Exception as e:
                logger.error(f"Error closing Elasticsearch client '{name}': {e}")
        
        cls._instances.clear()
        cls._configs.clear()


# ============================================================================
# Elasticsearch DSL Document Models
# ============================================================================

class ReservationDocument(Document):
    """Elasticsearch document model for reservations."""
    
    # Basic fields
    reservation_id = Integer(required=True)
    user_id = Integer(required=True)
    spot_id = Integer(required=True)
    vehicle_id = Integer(required=True)
    confirmation_code = Keyword()
    
    # Reservation details
    reservation_type = Keyword()
    status = Keyword()
    start_time = Date()
    end_time = Date()
    total_amount = Float()
    payment_status = Keyword()
    
    # Timestamps
    created_at = Date()
    confirmed_at = Date()
    checked_in_at = Date()
    checked_out_at = Date()
    cancelled_at = Date()
    
    # User details (denormalized)
    user_email = Text()
    user_name = Text()
    
    # Spot details (denormalized)
    spot_number = Keyword()
    spot_type = Keyword()
    
    # Vehicle details (denormalized)
    license_plate = Keyword()
    vehicle_type = Keyword()
    is_ev = Boolean()
    
    # Metadata
    tags = Keyword(multi=True)
    notes = Text()
    metadata = Text()  # JSON string
    
    class Index:
        name = "parking-reservations"
        settings = {
            "number_of_shards": 2,
            "number_of_replicas": 1,
            "analysis": {
                "analyzer": {
                    "custom_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "stop", "snowball"]
                    }
                }
            }
        }
    
    class Meta:
        doc_type = "reservation"


class UserDocument(Document):
    """Elasticsearch document model for users."""
    
    user_id = Integer(required=True)
    email = Keyword()
    full_name = Text()
    phone = Keyword()
    
    # User statistics
    total_reservations = Integer()
    total_spent = Float()
    average_rating = Float()
    
    # Preferences
    preferred_spot_type = Keyword()
    preferred_payment_method = Keyword()
    
    # Activity
    last_login = Date()
    last_reservation = Date()
    created_at = Date()
    
    # Flags
    is_active = Boolean()
    is_verified = Boolean()
    is_vip = Boolean()
    
    # Tags
    tags = Keyword(multi=True)
    
    class Index:
        name = "parking-users"
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 1
        }


class ParkingSpotDocument(Document):
    """Elasticsearch document model for parking spots."""
    
    spot_id = Integer(required=True)
    spot_number = Keyword()
    spot_type = Keyword()
    hourly_rate = Float()
    
    # Location
    level = Integer()
    section = Keyword()
    row = Keyword()
    coordinates = Text()  # JSON string with lat/lon
    
    # Features
    has_charger = Boolean()
    charger_type = Keyword()
    is_covered = Boolean()
    is_handicap = Boolean()
    is_near_elevator = Boolean()
    
    # Statistics
    total_reservations = Integer()
    occupancy_rate = Float()
    average_duration = Float()
    total_revenue = Float()
    
    # Status
    is_active = Boolean()
    is_maintenance = Boolean()
    last_maintenance = Date()
    next_maintenance = Date()
    
    class Index:
        name = "parking-spots"
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 1
        }


class AuditLogDocument(Document):
    """Elasticsearch document model for audit logs."""
    
    timestamp = Date(required=True)
    level = Keyword()  # INFO, WARNING, ERROR
    logger = Keyword()
    module = Keyword()
    function = Keyword()
    
    # Message
    message = Text()
    exception = Text()
    stack_trace = Text()
    
    # Context
    user_id = Integer()
    reservation_id = Integer()
    request_id = Keyword()
    ip_address = Keyword()
    user_agent = Text()
    
    # Performance
    duration_ms = Float()
    
    # Metadata
    environment = Keyword()
    version = Keyword()
    tags = Keyword(multi=True)
    
    class Index:
        name = "parking-logs"
        settings = {
            "number_of_shards": 2,
            "number_of_replicas": 1
        }
    
    class Meta:
        doc_type = "log"


class SearchAnalyticsDocument(Document):
    """Elasticsearch document model for search analytics."""
    
    timestamp = Date(required=True)
    query = Text()
    filters = Text()  # JSON string
    user_id = Integer()
    
    # Results
    total_hits = Integer()
    result_ids = Keyword(multi=True)
    click_position = Integer()
    clicked_id = Keyword()
    
    # Performance
    took_ms = Integer()
    
    # Context
    session_id = Keyword()
    ip_address = Keyword()
    
    class Index:
        name = "parking-search-analytics"
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 1
        }


# ============================================================================
# Index Management
# ============================================================================

class IndexManager:
    """Manage Elasticsearch indices."""
    
    def __init__(self, client_name: str = "default"):
        """Initialize index manager."""
        self.client = ElasticsearchConnectionPool.get_client(client_name)
        self.config = ElasticsearchConnectionPool.get_config(client_name)
        self.connection = connections.get_connection(client_name)
    
    def create_index(self, document_class, force: bool = False) -> bool:
        """Create an index for a document class."""
        try:
            index_name = document_class.Index.name
            index = Index(index_name, using=self.connection)
            
            if index.exists() and force:
                index.delete()
                logger.info(f"Deleted existing index: {index_name}")
            
            if not index.exists():
                # Create index with settings and mappings
                index.document(document_class)
                index.create()
                
                # Put mappings
                document_class.init(using=self.connection)
                
                logger.info(f"Created index: {index_name}")
                return True
            else:
                logger.info(f"Index already exists: {index_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False
    
    def delete_index(self, index_name: str) -> bool:
        """Delete an index."""
        try:
            self.client.indices.delete(index=index_name, ignore_unavailable=True)
            logger.info(f"Deleted index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {e}")
            return False
    
    def index_exists(self, index_name: str) -> bool:
        """Check if index exists."""
        try:
            return self.client.indices.exists(index=index_name)
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False
    
    def refresh_index(self, index_name: str) -> bool:
        """Refresh an index."""
        try:
            self.client.indices.refresh(index=index_name)
            logger.info(f"Refreshed index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh index {index_name}: {e}")
            return False
    
    def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get statistics for an index."""
        try:
            stats = self.client.indices.stats(index=index_name)
            return stats.get('indices', {}).get(index_name, {})
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}
    
    def get_mapping(self, index_name: str) -> Dict[str, Any]:
        """Get mapping for an index."""
        try:
            mapping = self.client.indices.get_mapping(index=index_name)
            return mapping.get(index_name, {}).get('mappings', {})
        except Exception as e:
            logger.error(f"Failed to get mapping: {e}")
            return {}
    
    def update_mapping(self, index_name: str, document_class) -> bool:
        """Update mapping for an index."""
        try:
            # Get current mapping
            mapping = document_class._doc_type.mapping.to_dict()
            self.client.indices.put_mapping(index=index_name, body=mapping)
            logger.info(f"Updated mapping for index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update mapping: {e}")
            return False
    
    def reindex(self, source_index: str, target_index: str) -> bool:
        """Reindex from source to target."""
        try:
            body = {
                "source": {"index": source_index},
                "dest": {"index": target_index}
            }
            result = self.client.reindex(body=body, wait_for_completion=True)
            logger.info(f"Reindexed {result.get('total', 0)} documents")
            return True
        except Exception as e:
            logger.error(f"Failed to reindex: {e}")
            return False
    
    def list_indices(self, pattern: Optional[str] = None) -> List[str]:
        """List all indices matching pattern."""
        try:
            if pattern:
                return list(self.client.indices.get_alias(index=pattern).keys())
            else:
                return list(self.client.indices.get_alias().keys())
        except Exception as e:
            logger.error(f"Failed to list indices: {e}")
            return []
    
    def optimize_index(self, index_name: str) -> bool:
        """Optimize an index (force merge)."""
        try:
            self.client.indices.forcemerge(index=index_name, max_num_segments=1)
            logger.info(f"Optimized index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to optimize index: {e}")
            return False


# ============================================================================
# Search Service
# ============================================================================

class SearchService:
    """Elasticsearch search service."""
    
    def __init__(self, client_name: str = "default"):
        """Initialize search service."""
        self.client = ElasticsearchConnectionPool.get_client(client_name)
        self.config = ElasticsearchConnectionPool.get_config(client_name)
        self.connection = connections.get_connection(client_name)
    
    def search(self, index: str, query: Union[str, Dict, Q], **kwargs) -> Dict[str, Any]:
        """Execute a search query."""
        try:
            # Build search
            s = Search(using=self.connection, index=index)
            
            if isinstance(query, str):
                s = s.query("multi_match", query=query, fields=["*"])
            elif isinstance(query, dict):
                s = s.update_from_dict(query)
            elif isinstance(query, Q):
                s = s.query(query)
            
            # Apply pagination
            from_ = kwargs.get('from_', 0)
            size = kwargs.get('size', 10)
            s = s[from_:from_ + size]
            
            # Apply sorting
            sort = kwargs.get('sort')
            if sort:
                s = s.sort(*sort)
            
            # Apply source filtering
            source = kwargs.get('_source')
            if source:
                s = s.source(source)
            
            # Track total hits
            s = s.extra(track_total_hits=self.config.track_total_hits)
            
            # Execute search
            response = s.execute()
            
            # Format response
            return {
                'total': response.hits.total.value,
                'max_score': response.hits.max_score,
                'hits': [
                    {
                        'id': hit.meta.id,
                        'score': hit.meta.score,
                        'source': hit.to_dict()
                    }
                    for hit in response
                ],
                'aggregations': response.aggregations.to_dict() if response.aggregations else {},
                'took': response.took
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                'total': 0,
                'hits': [],
                'error': str(e)
            }
    
    def count(self, index: str, query: Optional[Dict] = None) -> int:
        """Count documents matching query."""
        try:
            if query:
                result = self.client.count(index=index, body={"query": query})
            else:
                result = self.client.count(index=index)
            return result.get('count', 0)
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return 0
    
    def suggest(self, index: str, field: str, text: str, size: int = 5) -> List[str]:
        """Get suggestions for a field."""
        try:
            s = Search(using=self.connection, index=index)
            s = s.suggest('suggestions', text, completion={"field": field})
            response = s.execute()
            
            suggestions = []
            for option in response.suggest.suggestions[0].options:
                suggestions.append(option.text)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Suggest failed: {e}")
            return []
    
    def autocomplete(self, index: str, field: str, prefix: str, size: int = 5) -> List[str]:
        """Autocomplete for a field."""
        try:
            query = {
                "match_phrase_prefix": {
                    field: {
                        "query": prefix,
                        "max_expansions": 10
                    }
                }
            }
            
            s = Search(using=self.connection, index=index).query(query)
            s = s[:size]
            s = s.source(fields=[field])
            
            response = s.execute()
            
            suggestions = set()
            for hit in response:
                value = getattr(hit, field, None)
                if value and str(value).startswith(prefix):
                    suggestions.add(str(value))
            
            return list(suggestions)[:size]
            
        except Exception as e:
            logger.error(f"Autocomplete failed: {e}")
            return []
    
    def search_by_filters(self, index: str, filters: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Search with filters."""
        try:
            # Build boolean query
            must_clauses = []
            filter_clauses = []
            
            for field, value in filters.items():
                if isinstance(value, (list, tuple)):
                    # Terms query
                    filter_clauses.append({"terms": {field: value}})
                elif isinstance(value, dict):
                    # Range query
                    range_clause = {"range": {field: value}}
                    filter_clauses.append(range_clause)
                else:
                    # Term query
                    filter_clauses.append({"term": {field: value}})
            
            # Build query
            query = {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses
                }
            }
            
            return self.search(index, query, **kwargs)
            
        except Exception as e:
            logger.error(f"Filter search failed: {e}")
            return {'total': 0, 'hits': [], 'error': str(e)}
    
    def search_by_geo(self, index: str, lat: float, lon: float, distance: str, **kwargs) -> Dict[str, Any]:
        """Search by geo location."""
        try:
            query = {
                "bool": {
                    "filter": {
                        "geo_distance": {
                            "distance": distance,
                            "coordinates": {"lat": lat, "lon": lon}
                        }
                    }
                }
            }
            
            return self.search(index, query, **kwargs)
            
        except Exception as e:
            logger.error(f"Geo search failed: {e}")
            return {'total': 0, 'hits': [], 'error': str(e)}
    
    def get_aggregations(self, index: str, aggs: Dict[str, Any], query: Optional[Dict] = None) -> Dict[str, Any]:
        """Get aggregations only."""
        try:
            body = {"aggs": aggs}
            if query:
                body["query"] = query
            
            result = self.client.search(index=index, body=body, size=0)
            return result.get('aggregations', {})
            
        except Exception as e:
            logger.error(f"Aggregations failed: {e}")
            return {}
    
    def get_daily_stats(self, index: str, field: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily statistics for a field."""
        try:
            end = datetime.now()
            start = end - timedelta(days=days)
            
            query = {
                "range": {
                    "timestamp": {
                        "gte": start.isoformat(),
                        "lte": end.isoformat()
                    }
                }
            }
            
            aggs = {
                "daily": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "day"
                    },
                    "aggs": {
                        "avg_value": {"avg": {"field": field}},
                        "min_value": {"min": {"field": field}},
                        "max_value": {"max": {"field": field}},
                        "count": {"value_count": {"field": field}}
                    }
                }
            }
            
            result = self.get_aggregations(index, aggs, query)
            
            stats = []
            for bucket in result.get('daily', {}).get('buckets', []):
                stats.append({
                    'date': bucket['key_as_string'],
                    'avg': bucket['avg_value']['value'],
                    'min': bucket['min_value']['value'],
                    'max': bucket['max_value']['value'],
                    'count': bucket['count']['value']
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Daily stats failed: {e}")
            return []


# ============================================================================
# Indexing Service
# ============================================================================

class IndexingService:
    """Elasticsearch indexing service."""
    
    def __init__(self, client_name: str = "default"):
        """Initialize indexing service."""
        self.client = ElasticsearchConnectionPool.get_client(client_name)
        self.config = ElasticsearchConnectionPool.get_config(client_name)
        self.index_manager = IndexManager(client_name)
    
    def index_document(self, index: str, document: Dict[str, Any], doc_id: Optional[str] = None) -> bool:
        """Index a single document."""
        try:
            if doc_id:
                self.client.index(index=index, id=doc_id, body=document)
            else:
                self.client.index(index=index, body=document)
            return True
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False
    
    def index_bulk(self, index: str, documents: List[Dict[str, Any]], id_field: Optional[str] = None) -> Tuple[int, int]:
        """Index multiple documents in bulk."""
        try:
            actions = []
            for doc in documents:
                action = {
                    "_index": index,
                    "_source": doc
                }
                if id_field and id_field in doc:
                    action["_id"] = str(doc[id_field])
                actions.append(action)
            
            success, failed = helpers.bulk(
                self.client,
                actions,
                stats_only=True,
                raise_on_error=False
            )
            
            logger.info(f"Bulk indexed: {success} successful, {failed} failed")
            return success, failed
            
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return 0, len(documents)
    
    def update_document(self, index: str, doc_id: str, update: Dict[str, Any]) -> bool:
        """Update a document."""
        try:
            self.client.update(index=index, id=doc_id, body={"doc": update})
            return True
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return False
    
    def delete_document(self, index: str, doc_id: str) -> bool:
        """Delete a document."""
        try:
            self.client.delete(index=index, id=doc_id, ignore_unavailable=True)
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def get_document(self, index: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        try:
            result = self.client.get(index=index, id=doc_id, ignore_unavailable=True)
            if result.get('found'):
                return result.get('_source')
            return None
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
    
    def bulk_update_by_query(self, index: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """Bulk update documents matching query."""
        try:
            body = {
                "query": query,
                "script": {
                    "source": "ctx._source.update(params.update)",
                    "params": {"update": update}
                }
            }
            
            result = self.client.update_by_query(index=index, body=body)
            return result.get('updated', 0)
            
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            return 0
    
    def bulk_delete_by_query(self, index: str, query: Dict[str, Any]) -> int:
        """Bulk delete documents matching query."""
        try:
            result = self.client.delete_by_query(index=index, body={"query": query})
            return result.get('deleted', 0)
        except Exception as e:
            logger.error(f"Bulk delete failed: {e}")
            return 0
    
    def scroll(self, index: str, query: Dict[str, Any], scroll_time: str = '2m') -> Generator[Dict[str, Any], None, None]:
        """Scroll through all documents matching query."""
        try:
            # Initial search
            result = self.client.search(
                index=index,
                body={"query": query},
                scroll=scroll_time,
                size=1000
            )
            
            scroll_id = result.get('_scroll_id')
            hits = result.get('hits', {}).get('hits', [])
            
            while hits:
                for hit in hits:
                    yield {
                        'id': hit['_id'],
                        'score': hit['_score'],
                        'source': hit['_source']
                    }
                
                # Get next batch
                result = self.client.scroll(scroll_id=scroll_id, scroll=scroll_time)
                scroll_id = result.get('_scroll_id')
                hits = result.get('hits', {}).get('hits', [])
            
            # Clear scroll
            self.client.clear_scroll(scroll_id=scroll_id)
            
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return


# ============================================================================
# Audit Logging
# ============================================================================

class ElasticsearchLogger:
    """Elasticsearch-based audit logger."""
    
    def __init__(self, index: str = "parking-logs", client_name: str = "default"):
        """Initialize Elasticsearch logger."""
        self.index = index
        self.indexing_service = IndexingService(client_name)
        self.enabled = ElasticsearchConnectionPool.get_config(client_name).enable_logging
    
    def log(self, level: str, message: str, **kwargs):
        """Log a message."""
        if not self.enabled:
            return
        
        doc = {
            'timestamp': datetime.now().isoformat(),
            'level': level.upper(),
            'message': message,
            **kwargs
        }
        
        try:
            self.indexing_service.index_document(self.index, doc)
        except Exception as e:
            # Fallback to standard logging
            logger.error(f"Failed to log to Elasticsearch: {e}")
    
    def info(self, message: str, **kwargs):
        """Log info level message."""
        self.log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error level message."""
        extra = kwargs.copy()
        if exception:
            extra['exception'] = str(exception)
            extra['stack_trace'] = self._get_stack_trace(exception)
        self.log('ERROR', message, **kwargs)
    
    def audit(self, action: str, user_id: Optional[int] = None, **kwargs):
        """Log audit event."""
        doc = {
            'timestamp': datetime.now().isoformat(),
            'level': 'AUDIT',
            'action': action,
            'user_id': user_id,
            **kwargs
        }
        
        try:
            self.indexing_service.index_document(self.index, doc)
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def _get_stack_trace(self, exception: Exception) -> str:
        """Get stack trace from exception."""
        import traceback
        return ''.join(traceback.format_tb(exception.__traceback__))


# ============================================================================
# Decorators and Utilities
# ============================================================================

def log_to_elasticsearch(level: str = 'INFO'):
    """Decorator to log function calls to Elasticsearch."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = ElasticsearchLogger()
            
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                logger.info(
                    f"Function {func.__name__} executed",
                    module=func.__module__,
                    function=func.__name__,
                    duration_ms=duration,
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                logger.error(
                    f"Function {func.__name__} failed: {str(e)}",
                    module=func.__module__,
                    function=func.__name__,
                    duration_ms=duration,
                    exception=e
                )
                
                raise
        
        return wrapper
    return decorator


def track_search():
    """Decorator to track search queries."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            service = SearchService()
            logger = ElasticsearchLogger(index="parking-search-analytics")
            
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                
                # Log search
                logger.audit(
                    action='search',
                    query=kwargs.get('query'),
                    filters=kwargs.get('filters'),
                    total_hits=result.get('total', 0),
                    took_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
                
                return result
                
            except Exception as e:
                logger.error(
                    "Search failed",
                    query=kwargs.get('query'),
                    error=str(e)
                )
                raise
        
        return wrapper
    return decorator


@contextmanager
def elasticsearch_logging_context(**kwargs):
    """Context manager for adding context to all logs."""
    logger = ElasticsearchLogger()
    # Store context in thread local
    # Implementation depends on your threading model
    yield


# ============================================================================
# Health Check and Monitoring
# ============================================================================

class ElasticsearchHealthCheck:
    """Elasticsearch health check utilities."""
    
    def __init__(self, client_name: str = "default"):
        """Initialize health check."""
        self.client = ElasticsearchConnectionPool.get_client(client_name)
        self.config = ElasticsearchConnectionPool.get_config(client_name)
        self.index_manager = IndexManager(client_name)
    
    def check_cluster_health(self) -> Dict[str, Any]:
        """Check cluster health."""
        try:
            health = self.client.cluster.health()
            return {
                'status': health.get('status'),
                'cluster_name': health.get('cluster_name'),
                'node_count': health.get('number_of_nodes'),
                'data_node_count': health.get('number_of_data_nodes'),
                'active_shards': health.get('active_shards'),
                'relocating_shards': health.get('relocating_shards'),
                'initializing_shards': health.get('initializing_shards'),
                'unassigned_shards': health.get('unassigned_shards'),
                'pending_tasks': health.get('number_of_pending_tasks'),
                'timed_out': health.get('timed_out')
            }
        except Exception as e:
            logger.error(f"Cluster health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}
    
    def check_node_stats(self) -> Dict[str, Any]:
        """Get node statistics."""
        try:
            stats = self.client.nodes.stats()
            nodes = stats.get('nodes', {})
            
            result = {}
            for node_id, node_data in nodes.items():
                result[node_id] = {
                    'name': node_data.get('name'),
                    'version': node_data.get('version'),
                    'indices': node_data.get('indices', {}).get('docs', {}).get('count', 0),
                    'size': node_data.get('indices', {}).get('store', {}).get('size_in_bytes', 0),
                    'memory': node_data.get('jvm', {}).get('mem', {}).get('heap_used_percent', 0),
                    'cpu': node_data.get('process', {}).get('cpu', {}).get('percent', 0),
                    'uptime': node_data.get('jvm', {}).get('uptime_in_millis', 0)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Node stats check failed: {e}")
            return {}
    
    def check_indices_health(self) -> Dict[str, Any]:
        """Check health of all indices."""
        try:
            indices = self.index_manager.list_indices()
            
            result = {}
            for index in indices:
                stats = self.index_manager.get_index_stats(index)
                result[index] = {
                    'exists': True,
                    'docs': stats.get('total', {}).get('docs', {}).get('count', 0),
                    'size': stats.get('total', {}).get('store', {}).get('size_in_bytes', 0)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Indices health check failed: {e}")
            return {}
    
    def check_connection(self) -> bool:
        """Check basic connection."""
        try:
            return self.client.ping()
        except Exception:
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        try:
            # Get cluster stats
            stats = self.client.cluster.stats()
            
            return {
                'indices_count': stats.get('indices', {}).get('count', 0),
                'shards_count': stats.get('indices', {}).get('shards', {}).get('total', 0),
                'documents_count': stats.get('indices', {}).get('docs', {}).get('count', 0),
                'total_size': stats.get('indices', {}).get('store', {}).get('size_in_bytes', 0),
                'nodes_count': stats.get('nodes', {}).get('count', {}).get('total', 0),
                'memory_available': stats.get('nodes', {}).get('os', {}).get('mem', {}).get('total_in_bytes', 0),
                'memory_used': stats.get('nodes', {}).get('os', {}).get('mem', {}).get('used_in_bytes', 0)
            }
            
        except Exception as e:
            logger.error(f"Performance metrics check failed: {e}")
            return {}


# ============================================================================
# Initialization and Cleanup
# ============================================================================

def init_elasticsearch():
    """Initialize Elasticsearch connections and indices."""
    logger.info("Initializing Elasticsearch connections...")
    
    # Create default client
    client = ElasticsearchConnectionPool.get_client()
    
    # Check connection
    try:
        info = client.info()
        logger.info(f"Connected to Elasticsearch {info.get('version', {}).get('number')}")
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        if not is_testing():
            raise
    
    # Create indices if they don't exist
    if not is_testing():
        index_manager = IndexManager()
        
        # Create indices for each document type
        indices = [
            (ReservationDocument, ReservationDocument.Index.name),
            (UserDocument, UserDocument.Index.name),
            (ParkingSpotDocument, ParkingSpotDocument.Index.name),
            (AuditLogDocument, AuditLogDocument.Index.name),
            (SearchAnalyticsDocument, SearchAnalyticsDocument.Index.name)
        ]
        
        for doc_class, index_name in indices:
            if not index_manager.index_exists(index_name):
                index_manager.create_index(doc_class)
                logger.info(f"Created index: {index_name}")
    
    logger.info("Elasticsearch initialization complete")


def close_elasticsearch():
    """Close all Elasticsearch connections."""
    logger.info("Closing Elasticsearch connections...")
    ElasticsearchConnectionPool.close_all()


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Configuration
    'ElasticsearchConfig',
    
    # Connection management
    'ElasticsearchConnectionPool',
    'init_elasticsearch',
    'close_elasticsearch',
    
    # Document models
    'ReservationDocument',
    'UserDocument',
    'ParkingSpotDocument',
    'AuditLogDocument',
    'SearchAnalyticsDocument',
    
    # Services
    'IndexManager',
    'SearchService',
    'IndexingService',
    'ElasticsearchLogger',
    
    # Health check
    'ElasticsearchHealthCheck',
    
    # Decorators
    'log_to_elasticsearch',
    'track_search',
    'elasticsearch_logging_context',
]

# Initialize on import (but not during testing)
if not is_testing():
    init_elasticsearch()