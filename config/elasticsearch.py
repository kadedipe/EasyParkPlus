"""Elasticsearch configuration and client management."""

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from typing import List, Dict, Any, Optional
import logging

from . import config

logger = logging.getLogger(__name__)


class ElasticsearchConfig:
    """Elasticsearch connection configuration."""
    
    def __init__(self):
        self.client = None
        self._setup_connection()
    
    def _setup_connection(self):
        """Setup Elasticsearch connection."""
        connection_params = {
            'hosts': config.ELASTICSEARCH_HOSTS,
            'timeout': 30,
            'max_retries': 3,
            'retry_on_timeout': True
        }
        
        if config.ELASTICSEARCH_USER and config.ELASTICSEARCH_PASSWORD:
            connection_params['http_auth'] = (
                config.ELASTICSEARCH_USER,
                config.ELASTICSEARCH_PASSWORD
            )
        
        connection_params['verify_certs'] = config.ELASTICSEARCH_VERIFY_CERTS
        
        self.client = Elasticsearch(**connection_params)
        
        # Test connection
        try:
            if self.client.ping():
                logger.info(f"Elasticsearch connected to {config.ELASTICSEARCH_HOSTS}")
            else:
                logger.error("Elasticsearch connection failed")
                if not config.TESTING:
                    raise ConnectionError("Elasticsearch connection failed")
        except Exception as e:
            logger.error(f"Elasticsearch connection error: {e}")
            if not config.TESTING:
                raise
    
    def get_client(self) -> Elasticsearch:
        """Get Elasticsearch client."""
        return self.client
    
    def close(self):
        """Close Elasticsearch connection."""
        if self.client:
            self.client.close()
            logger.info("Elasticsearch connection closed")


# Search indices configuration
INDICES = {
    'reservations': {
        'settings': {
            'number_of_shards': 2,
            'number_of_replicas': 1,
            'analysis': {
                'analyzer': {
                    'custom_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': ['lowercase', 'stop', 'snowball']
                    }
                }
            }
        },
        'mappings': {
            'properties': {
                'id': {'type': 'integer'},
                'user_id': {'type': 'integer'},
                'spot_id': {'type': 'integer'},
                'confirmation_code': {'type': 'keyword'},
                'status': {'type': 'keyword'},
                'start_time': {'type': 'date'},
                'end_time': {'type': 'date'},
                'total_amount': {'type': 'float'},
                'user_email': {'type': 'text'},
                'user_name': {'type': 'text'},
                'spot_number': {'type': 'keyword'},
                'license_plate': {'type': 'keyword'},
                'created_at': {'type': 'date'}
            }
        }
    },
    'users': {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 1
        },
        'mappings': {
            'properties': {
                'id': {'type': 'integer'},
                'email': {'type': 'keyword'},
                'full_name': {'type': 'text'},
                'phone': {'type': 'keyword'},
                'role': {'type': 'keyword'},
                'status': {'type': 'keyword'},
                'created_at': {'type': 'date'}
            }
        }
    },
    'logs': {
        'settings': {
            'number_of_shards': 3,
            'number_of_replicas': 1
        },
        'mappings': {
            'properties': {
                'timestamp': {'type': 'date'},
                'level': {'type': 'keyword'},
                'logger': {'type': 'keyword'},
                'message': {'type': 'text'},
                'user_id': {'type': 'integer'},
                'request_id': {'type': 'keyword'},
                'ip_address': {'type': 'ip'},
                'duration_ms': {'type': 'float'}
            }
        }
    }
}


# Global Elasticsearch instance
es_config = ElasticsearchConfig()
es_client = es_config.get_client()