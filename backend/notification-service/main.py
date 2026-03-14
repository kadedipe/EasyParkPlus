"""
Main entry point for the Notification Service.
Handles service initialization, consumer management, and graceful shutdown.
"""

import asyncio
import signal
import sys
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .core.config import settings
from .core.exceptions import NotificationServiceError
from .consumers import (
    EmailConsumer,
    SMSConsumer,
    PushConsumer,
    AuditConsumer,
    BookingConsumer,
    PaymentConsumer,
    UserConsumer
)
from .providers.email import initialize_email_providers, get_email_provider_manager
from .providers.sms import initialize_sms_providers, get_sms_provider_manager
from .providers.push import initialize_push_providers, get_push_provider_manager
from .templates import get_template_manager
from .utils.logging_utils import setup_logging, get_logger, RequestLogger
from .utils.metrics import MetricsCollector
from .api import router as api_router
from .health import health_router


# Setup logging
setup_logging(
    app_name="notification-service",
    log_level=settings.LOG_LEVEL,
    json_format=settings.JSON_LOGS
)
logger = get_logger(__name__)


class NotificationService:
    """
    Main notification service class managing all consumers and components.
    """
    
    def __init__(self):
        """Initialize the notification service."""
        self.consumers: List = []
        self.metrics = MetricsCollector("notification_service")
        self.is_running = False
        self.should_exit = asyncio.Event()
        self.logger = logger
        
        # Initialize FastAPI app
        self.app = self.create_app()
        
        # Register signal handlers
        self._register_signal_handlers()
    
    def create_app(self) -> FastAPI:
        """
        Create and configure FastAPI application.
        
        Returns:
            FastAPI: Configured FastAPI app
        """
        app = FastAPI(
            title="Notification Service",
            description="Handles all notifications (email, SMS, push) for the Parking Management System",
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
        
        # Add error handling middleware
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request.headers.get("X-Request-ID")
                }
            )
        
        # Include routers
        app.include_router(api_router, prefix="/api/v1")
        app.include_router(health_router, prefix="/health")
        
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
        self.logger.info("Starting Notification Service...")
        
        try:
            # Initialize providers
            self.logger.info("Initializing providers...")
            initialize_email_providers()
            initialize_sms_providers()
            initialize_push_providers()
            
            # Initialize template manager
            self.logger.info("Initializing template manager...")
            get_template_manager()
            
            # Create consumers based on configuration
            self.consumers = await self._create_consumers()
            
            # Start all consumers
            self.logger.info(f"Starting {len(self.consumers)} consumers...")
            for consumer in self.consumers:
                asyncio.create_task(consumer.start())
            
            self.is_running = True
            self.logger.info("Notification Service started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Notification Service: {e}", exc_info=True)
            raise
    
    async def shutdown(self):
        """Gracefully shutdown all components."""
        self.logger.info("Shutting down Notification Service...")
        
        # Signal all consumers to stop
        self.should_exit.set()
        
        # Stop all consumers
        for consumer in self.consumers:
            try:
                await consumer.stop()
                self.logger.info(f"Stopped consumer: {consumer.__class__.__name__}")
            except Exception as e:
                self.logger.error(f"Error stopping consumer {consumer.__class__.__name__}: {e}")
        
        self.is_running = False
        self.logger.info("Notification Service shutdown complete")
    
    async def _create_consumers(self) -> List:
        """
        Create consumer instances based on configuration.
        
        Returns:
            List: List of consumer instances
        """
        consumers = []
        
        # Email consumer
        if settings.ENABLE_EMAIL:
            consumers.append(EmailConsumer())
            self.logger.info("Email consumer enabled")
        
        # SMS consumer
        if settings.ENABLE_SMS:
            consumers.append(SMSConsumer())
            self.logger.info("SMS consumer enabled")
        
        # Push consumer
        if settings.ENABLE_PUSH:
            consumers.append(PushConsumer())
            self.logger.info("Push consumer enabled")
        
        # Audit consumer
        if settings.ENABLE_AUDIT:
            consumers.append(AuditConsumer())
            self.logger.info("Audit consumer enabled")
        
        # Booking consumer
        if settings.ENABLE_BOOKING_NOTIFICATIONS:
            consumers.append(BookingConsumer())
            self.logger.info("Booking consumer enabled")
        
        # Payment consumer
        if settings.ENABLE_PAYMENT_NOTIFICATIONS:
            consumers.append(PaymentConsumer())
            self.logger.info("Payment consumer enabled")
        
        # User consumer
        if settings.ENABLE_USER_NOTIFICATIONS:
            consumers.append(UserConsumer())
            self.logger.info("User consumer enabled")
        
        return consumers
    
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
    
    async def health_check(self) -> dict:
        """
        Perform health check of all components.
        
        Returns:
            dict: Health status
        """
        health_status = {
            "status": "healthy",
            "service": "notification-service",
            "version": "1.0.0",
            "components": {},
            "metrics": self.metrics.get_stats()
        }
        
        # Check consumers
        for consumer in self.consumers:
            try:
                status = await consumer.get_queue_status()
                health_status["components"][consumer.__class__.__name__] = {
                    "status": "running",
                    "queue": status
                }
            except Exception as e:
                health_status["components"][consumer.__class__.__name__] = {
                    "status": "error",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        
        # Check providers
        email_manager = get_email_provider_manager()
        if email_manager:
            health_status["components"]["email_providers"] = {
                "healthy": await email_manager.get_healthy_providers()
            }
        
        sms_manager = get_sms_provider_manager()
        if sms_manager:
            health_status["components"]["sms_providers"] = {
                "healthy": await sms_manager.get_healthy_providers()
            }
        
        push_manager = get_push_provider_manager()
        if push_manager:
            health_status["components"]["push_providers"] = {
                "healthy": await push_manager.get_healthy_providers()
            }
        
        return health_status
    
    def run(self):
        """Run the FastAPI application."""
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
            workers=settings.WORKERS
        )


# Create global service instance
service = NotificationService()
app = service.app


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Notification Service",
        "version": "1.0.0",
        "status": "running",
        "consumers": [c.__class__.__name__ for c in service.consumers]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return await service.health_check()


@app.get("/metrics")
async def metrics():
    """Metrics endpoint."""
    return {
        "service": "notification-service",
        "metrics": service.metrics.get_stats(),
        "providers": {
            "email": get_email_provider_manager().get_stats() if get_email_provider_manager() else [],
            "sms": get_sms_provider_manager().get_stats() if get_sms_provider_manager() else [],
            "push": get_push_provider_manager().get_stats() if get_push_provider_manager() else []
        }
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
            "email": settings.ENABLE_EMAIL,
            "sms": settings.ENABLE_SMS,
            "push": settings.ENABLE_PUSH,
            "audit": settings.ENABLE_AUDIT,
            "booking_notifications": settings.ENABLE_BOOKING_NOTIFICATIONS,
            "payment_notifications": settings.ENABLE_PAYMENT_NOTIFICATIONS,
            "user_notifications": settings.ENABLE_USER_NOTIFICATIONS
        },
        "rabbitmq": {
            "host": settings.RABBITMQ_HOST,
            "port": settings.RABBITMQ_PORT,
            "vhost": settings.RABBITMQ_VHOST
        },
        "templates": get_template_manager().list_templates()
    }


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