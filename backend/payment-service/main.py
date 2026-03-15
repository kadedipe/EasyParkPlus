"""
Main entry point for the Payment Service.
Handles service initialization, API routes, and graceful shutdown.
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .core.config import settings
from .core.exceptions import PaymentServiceError
from .api import router as api_router
from .webhooks import webhook_router, webhook_api_router
from .webhooks.processor import get_webhook_processor
from .gateways import (
    get_stripe_gateway,
    get_paypal_gateway,
    get_razorpay_gateway
)
from .services.payment_service import payment_service
from .services.subscription_service import subscription_service
from .services.invoice_service import invoice_service
from .services.dispute_service import dispute_service
from .db.database import DatabaseManager
from .utils.logging_utils import setup_logging, get_logger, RequestLogger
from .utils.metrics import MetricsCollector
from .utils.cache import CacheManager
from .utils.queue import QueueManager

# Setup logging
setup_logging(
    app_name="payment-service",
    log_level=settings.LOG_LEVEL,
    json_format=settings.JSON_LOGS
)
logger = get_logger(__name__)


class PaymentService:
    """
    Main payment service class managing all components.
    """
    
    def __init__(self):
        """Initialize the payment service."""
        self.metrics = MetricsCollector("payment_service")
        self.is_running = False
        self.should_exit = asyncio.Event()
        self.logger = logger
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.cache_manager = CacheManager()
        self.queue_manager = QueueManager()
        
        # Background tasks
        self.background_tasks = set()
        
        # Create FastAPI app
        self.app = self.create_app()
        
        # Register signal handlers
        self._register_signal_handlers()
        
        self.logger.info("Payment Service initialized")
    
    def create_app(self) -> FastAPI:
        """
        Create and configure FastAPI application.
        
        Returns:
            FastAPI: Configured FastAPI app
        """
        app = FastAPI(
            title="Payment Service",
            description="Handles all payment operations for the Parking Management System",
            version="1.0.0",
            docs_url="/api/docs" if settings.ENABLE_DOCS else None,
            redoc_url="/api/redoc" if settings.ENABLE_DOCS else None,
            openapi_url="/api/openapi.json" if settings.ENABLE_DOCS else None,
            lifespan=self.lifespan
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add request logging middleware
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            request_logger = RequestLogger(logger)
            request_id = request.headers.get("X-Request-ID", self._generate_request_id())
            
            with request_logger.log_request_response(
                method=request.method,
                path=request.url.path,
                request_id=request_id
            ):
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                return response
        
        # Add metrics middleware
        @app.middleware("http")
        async def track_metrics(request: Request, call_next):
            import time
            start_time = time.time()
            
            response = await call_next(request)
            
            duration = time.time() - start_time
            self.metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
        
        # Add error handling middleware
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            self.metrics.record_error()
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request.headers.get("X-Request-ID"),
                    "message": str(exc) if settings.DEBUG else None
                }
            )
        
        # Include routers
        app.include_router(api_router, prefix="/api/v1")
        app.include_router(webhook_router, prefix="/webhooks")  # External webhooks
        app.include_router(webhook_api_router, prefix="/api/v1/webhooks")  # Internal webhook management
        
        return app
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """
        Lifespan context manager for startup and shutdown events.
        """
        # Startup
        await self.startup()
        yield
        # Shutdown
        await self.shutdown()
    
    async def startup(self):
        """Initialize all components on startup."""
        self.logger.info("Starting Payment Service...")
        
        try:
            # Initialize database
            self.logger.info("Initializing database...")
            await self.db_manager.initialize()
            
            # Initialize cache
            self.logger.info("Initializing cache...")
            await self.cache_manager.initialize()
            
            # Initialize queue
            self.logger.info("Initializing message queue...")
            await self.queue_manager.initialize()
            
            # Initialize payment gateways
            self.logger.info("Initializing payment gateways...")
            await self._initialize_gateways()
            
            # Initialize webhook processor
            self.logger.info("Initializing webhook processor...")
            self.webhook_processor = await get_webhook_processor()
            
            # Initialize services
            self.logger.info("Initializing services...")
            await payment_service.initialize(self.db_manager, self.cache_manager, self.queue_manager)
            await subscription_service.initialize(self.db_manager, self.cache_manager, self.queue_manager)
            await invoice_service.initialize(self.db_manager, self.queue_manager)
            await dispute_service.initialize(self.db_manager, self.queue_manager)
            
            # Start background tasks
            self.logger.info("Starting background tasks...")
            await self._start_background_tasks()
            
            self.is_running = True
            self.logger.info("Payment Service started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Payment Service: {e}", exc_info=True)
            raise
    
    async def shutdown(self):
        """Gracefully shutdown all components."""
        self.logger.info("Shutting down Payment Service...")
        
        # Signal all tasks to stop
        self.should_exit.set()
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Shutdown services
        self.logger.info("Shutting down services...")
        await payment_service.shutdown()
        await subscription_service.shutdown()
        await invoice_service.shutdown()
        await dispute_service.shutdown()
        
        # Shutdown queue
        self.logger.info("Shutting down message queue...")
        await self.queue_manager.shutdown()
        
        # Shutdown cache
        self.logger.info("Shutting down cache...")
        await self.cache_manager.shutdown()
        
        # Shutdown database
        self.logger.info("Shutting down database...")
        await self.db_manager.shutdown()
        
        self.is_running = False
        self.logger.info("Payment Service shutdown complete")
    
    async def _initialize_gateways(self):
        """Initialize payment gateways."""
        # Initialize Stripe
        if settings.ENABLE_STRIPE:
            stripe_gateway = get_stripe_gateway()
            await stripe_gateway.initialize()
            self.logger.info("Stripe gateway initialized")
        
        # Initialize PayPal
        if settings.ENABLE_PAYPAL:
            paypal_gateway = get_paypal_gateway()
            await paypal_gateway.initialize()
            self.logger.info("PayPal gateway initialized")
        
        # Initialize Razorpay
        if settings.ENABLE_RAZORPAY:
            razorpay_gateway = get_razorpay_gateway()
            await razorpay_gateway.initialize()
            self.logger.info("Razorpay gateway initialized")
    
    async def _start_background_tasks(self):
        """Start background tasks."""
        # Webhook processing task
        task = asyncio.create_task(
            self._run_webhook_processor(),
            name="webhook_processor"
        )
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Subscription renewal task
        task = asyncio.create_task(
            self._run_subscription_renewal(),
            name="subscription_renewal"
        )
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Invoice generation task
        task = asyncio.create_task(
            self._run_invoice_generation(),
            name="invoice_generation"
        )
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Dispute monitoring task
        task = asyncio.create_task(
            self._run_dispute_monitoring(),
            name="dispute_monitoring"
        )
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Metrics aggregation task
        task = asyncio.create_task(
            self._run_metrics_aggregation(),
            name="metrics_aggregation"
        )
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
    
    async def _run_webhook_processor(self):
        """Run webhook processor continuously."""
        self.logger.info("Starting webhook processor task")
        
        while not self.should_exit.is_set():
            try:
                await self.webhook_processor.process_queue(
                    batch_size=settings.WEBHOOK_BATCH_SIZE
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Webhook processor error: {e}")
                await asyncio.sleep(5)
        
        self.logger.info("Webhook processor task stopped")
    
    async def _run_subscription_renewal(self):
        """Run subscription renewal check."""
        self.logger.info("Starting subscription renewal task")
        
        while not self.should_exit.is_set():
            try:
                # Check for subscriptions needing renewal every hour
                await asyncio.sleep(3600)
                
                if self.should_exit.is_set():
                    break
                
                await subscription_service.process_renewals()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Subscription renewal error: {e}")
        
        self.logger.info("Subscription renewal task stopped")
    
    async def _run_invoice_generation(self):
        """Run invoice generation for pending charges."""
        self.logger.info("Starting invoice generation task")
        
        while not self.should_exit.is_set():
            try:
                # Generate invoices every 6 hours
                await asyncio.sleep(21600)
                
                if self.should_exit.is_set():
                    break
                
                await invoice_service.generate_pending_invoices()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Invoice generation error: {e}")
        
        self.logger.info("Invoice generation task stopped")
    
    async def _run_dispute_monitoring(self):
        """Run dispute monitoring."""
        self.logger.info("Starting dispute monitoring task")
        
        while not self.should_exit.is_set():
            try:
                # Check for new disputes every 30 minutes
                await asyncio.sleep(1800)
                
                if self.should_exit.is_set():
                    break
                
                await dispute_service.check_for_new_disputes()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Dispute monitoring error: {e}")
        
        self.logger.info("Dispute monitoring task stopped")
    
    async def _run_metrics_aggregation(self):
        """Run metrics aggregation."""
        self.logger.info("Starting metrics aggregation task")
        
        while not self.should_exit.is_set():
            try:
                # Aggregate metrics every minute
                await asyncio.sleep(60)
                
                if self.should_exit.is_set():
                    break
                
                await self._aggregate_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics aggregation error: {e}")
        
        self.logger.info("Metrics aggregation task stopped")
    
    async def _aggregate_metrics(self):
        """Aggregate service metrics."""
        # Get gateway statistics
        gateways_stats = {}
        
        if settings.ENABLE_STRIPE:
            stripe_gateway = get_stripe_gateway()
            gateways_stats["stripe"] = await stripe_gateway.get_stats()
        
        if settings.ENABLE_PAYPAL:
            paypal_gateway = get_paypal_gateway()
            gateways_stats["paypal"] = await paypal_gateway.get_stats()
        
        if settings.ENABLE_RAZORPAY:
            razorpay_gateway = get_razorpay_gateway()
            gateways_stats["razorpay"] = await razorpay_gateway.get_stats()
        
        # Record metrics
        self.metrics.record_gateway_stats(gateways_stats)
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle_exit_signal)
    
    def _handle_exit_signal(self, signum, frame):
        """Handle exit signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.shutdown())
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        import uuid
        return str(uuid.uuid4())
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of all components.
        
        Returns:
            Dict[str, Any]: Health status
        """
        health_status = {
            "status": "healthy",
            "service": "payment-service",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
            "metrics": self.metrics.get_stats()
        }
        
        # Check database
        try:
            db_healthy = await self.db_manager.health_check()
            health_status["components"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "type": "postgresql"
            }
            if not db_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check cache
        try:
            cache_healthy = await self.cache_manager.health_check()
            health_status["components"]["cache"] = {
                "status": "healthy" if cache_healthy else "unhealthy",
                "type": "redis"
            }
            if not cache_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["cache"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check queue
        try:
            queue_healthy = await self.queue_manager.health_check()
            health_status["components"]["queue"] = {
                "status": "healthy" if queue_healthy else "unhealthy",
                "type": "rabbitmq"
            }
            if not queue_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["queue"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check gateways
        gateways_status = {}
        
        if settings.ENABLE_STRIPE:
            stripe_gateway = get_stripe_gateway()
            gateways_status["stripe"] = await stripe_gateway.check_health()
        
        if settings.ENABLE_PAYPAL:
            paypal_gateway = get_paypal_gateway()
            gateways_status["paypal"] = await paypal_gateway.check_health()
        
        if settings.ENABLE_RAZORPAY:
            razorpay_gateway = get_razorpay_gateway()
            gateways_status["razorpay"] = await razorpay_gateway.check_health()
        
        health_status["components"]["gateways"] = gateways_status
        
        # Check if any gateway is unhealthy
        if any(v.get("status") == "unhealthy" for v in gateways_status.values() if v):
            health_status["status"] = "degraded"
        
        return health_status
    
    def run(self):
        """Run the FastAPI application."""
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
            workers=settings.WORKERS,
            ssl_keyfile=settings.SSL_KEY_FILE if settings.ENABLE_SSL else None,
            ssl_certfile=settings.SSL_CERT_FILE if settings.ENABLE_SSL else None
        )


# Create global service instance
service = PaymentService()
app = service.app


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Payment Service",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "features": {
            "stripe": settings.ENABLE_STRIPE,
            "paypal": settings.ENABLE_PAYPAL,
            "razorpay": settings.ENABLE_RAZORPAY,
            "subscriptions": settings.ENABLE_SUBSCRIPTIONS,
            "invoicing": settings.ENABLE_INVOICING,
            "webhooks": True
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return await service.health_check()


@app.get("/health/live")
async def liveness():
    """Liveness probe for Kubernetes."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready")
async def readiness():
    """Readiness probe for Kubernetes."""
    health_status = await service.health_check()
    if health_status["status"] == "healthy":
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": health_status}
        )


@app.get("/metrics")
async def metrics():
    """Metrics endpoint."""
    return {
        "service": "payment-service",
        "metrics": service.metrics.get_stats(),
        "gateways": {
            "stripe": (await get_stripe_gateway().get_stats()) if settings.ENABLE_STRIPE else None,
            "paypal": (await get_paypal_gateway().get_stats()) if settings.ENABLE_PAYPAL else None,
            "razorpay": (await get_razorpay_gateway().get_stats()) if settings.ENABLE_RAZORPAY else None
        },
        "queue": await service.queue_manager.get_stats(),
        "cache": await service.cache_manager.get_stats()
    }


@app.get("/config")
async def config():
    """Configuration endpoint (sanitized)."""
    # Return sanitized config (no secrets)
    return {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "host": settings.HOST,
        "port": settings.PORT,
        "workers": settings.WORKERS,
        "enabled_features": {
            "stripe": settings.ENABLE_STRIPE,
            "paypal": settings.ENABLE_PAYPAL,
            "razorpay": settings.ENABLE_RAZORPAY,
            "subscriptions": settings.ENABLE_SUBSCRIPTIONS,
            "invoicing": settings.ENABLE_INVOICING
        },
        "database": {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "name": settings.DB_NAME
        },
        "redis": {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT
        },
        "rabbitmq": {
            "host": settings.RABBITMQ_HOST,
            "port": settings.RABBITMQ_PORT,
            "vhost": settings.RABBITMQ_VHOST
        }
    }


@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to list all routes."""
    if not settings.DEBUG:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": list(route.methods) if hasattr(route, "methods") else None
        })
    
    return {"routes": routes}


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    # Already handled by lifespan
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    # Already handled by lifespan
    pass


def main():
    """Main entry point."""
    try:
        service.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()