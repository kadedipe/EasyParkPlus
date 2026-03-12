"""
Prometheus metrics collection middleware.
"""

import time
from typing import Dict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.core import CollectorRegistry

from ....utils.logger import logger


# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60)
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Active HTTP requests'
)

REQUEST_SIZE = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    buckets=(100, 1000, 10000, 100000, 1000000)
)

RESPONSE_SIZE = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    buckets=(100, 1000, 10000, 100000, 1000000)
)

ERROR_COUNT = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['method', 'endpoint', 'error_type']
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting Prometheus metrics.
    """
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics", "/health"]
    
    async def dispatch(self, request: Request, call_next):
        """
        Collect metrics for the request.
        """
        # Skip metrics for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        method = request.method
        endpoint = request.url.path
        
        # Track active requests
        ACTIVE_REQUESTS.inc()
        
        # Measure request size
        content_length = request.headers.get("content-length")
        if content_length:
            REQUEST_SIZE.labels(method=method, endpoint=endpoint).observe(int(content_length))
        
        # Track request duration
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
            
            # Record metrics
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            
            # Measure response size
            content_length = response.headers.get("content-length")
            if content_length:
                RESPONSE_SIZE.labels(method=method, endpoint=endpoint).observe(int(content_length))
            
            # Track errors
            if status >= 400:
                error_type = "client" if status < 500 else "server"
                ERROR_COUNT.labels(method=method, endpoint=endpoint, error_type=error_type).inc()
            
            return response
            
        except Exception as e:
            # Track exception as error
            ERROR_COUNT.labels(
                method=method,
                endpoint=endpoint,
                error_type="exception"
            ).inc()
            raise
            
        finally:
            # Record duration
            duration = time.time() - start_time
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            
            # Decrement active requests
            ACTIVE_REQUESTS.dec()
    
    def _should_exclude(self, path: str) -> bool:
        """
        Check if path should be excluded from metrics.
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False


class BusinessMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting business-specific metrics.
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Business metrics
        self.reservation_counter = Counter(
            'reservations_total',
            'Total reservations',
            ['status']
        )
        
        self.user_counter = Counter(
            'users_total',
            'Total users',
            ['role']
        )
        
        self.revenue_counter = Counter(
            'revenue_total',
            'Total revenue',
            ['currency']
        )
        
        self.parking_occupancy = Gauge(
            'parking_occupancy',
            'Parking spot occupancy',
            ['spot_type']
        )
        
        self.payment_success = Counter(
            'payments_successful_total',
            'Successful payments'
        )
        
        self.payment_failed = Counter(
            'payments_failed_total',
            'Failed payments'
        )
    
    async def dispatch(self, request: Request, call_next):
        """
        Collect business metrics from requests/responses.
        """
        response = await call_next(request)
        
        # Track reservation creations
        if request.method == "POST" and "/reservations" in request.url.path:
            if response.status_code == 201:
                self.reservation_counter.labels(status="created").inc()
        
        # Track user registrations
        if request.method == "POST" and "/auth/register" in request.url.path:
            if response.status_code == 201:
                self.user_counter.labels(role="user").inc()
        
        # Track payments
        if request.method == "POST" and "/payments" in request.url.path:
            if response.status_code == 201:
                self.payment_success.inc()
            else:
                self.payment_failed.inc()
        
        return response


async def metrics_endpoint(request: Request):
    """
    Endpoint for exposing Prometheus metrics.
    """
    from prometheus_client import generate_latest, REGISTRY
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain"
    )