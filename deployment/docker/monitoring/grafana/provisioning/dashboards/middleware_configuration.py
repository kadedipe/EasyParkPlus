# Python/FastAPI example
from prometheus_client import Histogram, Counter, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
import time

REQUEST_TIME = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
)

REQUESTS = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        endpoint = request.url.path
        method = request.method
        status = response.status_code
        
        REQUEST_TIME.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).observe(duration)
        
        REQUESTS.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        return response