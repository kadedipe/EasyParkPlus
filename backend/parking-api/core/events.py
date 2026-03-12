"""
Application event handlers for startup and shutdown.
Manages lifecycle events, background tasks, and service initialization.
"""

import asyncio
import signal
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .security import generate_secure_random_string
from ..db.session import engine, AsyncSessionLocal
from ..db.init_db import init_db, create_initial_data
from ..services.redis import redis_client
from ..services.cache import cache_manager
from ..services.queue import queue_manager
from ..services.scheduler import scheduler
from ..services.metrics import metrics_collector
from ..services.health import health_checker
from ..services.email import email_service
from ..services.websocket import websocket_manager
from ..services.audit import audit_logger
from ..utils.logger import logger
from ..utils.exceptions import ServiceInitializationError


# Background tasks container
background_tasks: List[asyncio.Task] = []


async def startup_handler() -> None:
    """
    Main startup handler for the application.
    Initializes all services and connections.
    """
    logger.info("=" * 60)
    logger.info("🚀 STARTING PARKING MANAGEMENT API")
    logger.info("=" * 60)
    
    start_time = datetime.utcnow()
    
    # Log configuration
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"API Version: {settings.VERSION}")
    
    try:
        # Initialize services in order
        await initialize_database()
        await initialize_redis()
        await initialize_cache()
        await initialize_queue()
        await initialize_scheduler()
        await initialize_metrics()
        await initialize_websocket()
        await initialize_email()
        
        # Start background tasks
        await start_background_tasks()
        
        # Calculate startup time
        startup_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"✅ API started successfully in {startup_time:.2f}s")
        logger.info(f"📊 Active services: Database, Redis, Cache, Queue, Scheduler, Metrics")
        logger.info(f"🌐 Listening on: http://{settings.HOST}:{settings.PORT}")
        logger.info(f"📚 Documentation: http://{settings.HOST}:{settings.PORT}/docs")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("❌ Failed to start application")
        logger.error(f"Error: {str(e)}")
        logger.exception("Startup error details:")
        await shutdown_handler()
        sys.exit(1)


async def shutdown_handler() -> None:
    """
    Main shutdown handler for the application.
    Gracefully shuts down all services and connections.
    """
    logger.info("=" * 60)
    logger.info("🛑 SHUTTING DOWN PARKING MANAGEMENT API")
    logger.info("=" * 60)
    
    shutdown_start = datetime.utcnow()
    
    # Cancel background tasks
    await cancel_background_tasks()
    
    # Shutdown services in reverse order
    shutdown_tasks = [
        shutdown_websocket(),
        shutdown_scheduler(),
        shutdown_queue(),
        shutdown_cache(),
        shutdown_redis(),
        shutdown_database(),
        shutdown_metrics(),
        shutdown_email()
    ]
    
    # Run shutdown tasks concurrently with timeout
    try:
        await asyncio.wait_for(
            asyncio.gather(*shutdown_tasks, return_exceptions=True),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        logger.warning("Some shutdown tasks timed out after 30 seconds")
    
    shutdown_time = (datetime.utcnow() - shutdown_start).total_seconds()
    
    logger.info("=" * 60)
    logger.info(f"✅ API shutdown completed in {shutdown_time:.2f}s")
    logger.info("=" * 60)


async def initialize_database() -> None:
    """
    Initialize database connection and run migrations.
    """
    logger.info("📦 Initializing database...")
    
    try:
        # Test database connection
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        
        # Create database tables if they don't exist
        await init_db()
        
        # Create initial data for development
        if settings.ENVIRONMENT == "development" and settings.CREATE_INITIAL_DATA:
            async with AsyncSessionLocal() as session:
                await create_initial_data(session)
        
        logger.info("✅ Database initialized successfully")
        
        # Log connection pool info
        logger.info(f"   Pool size: {settings.DB_POOL_SIZE}")
        logger.info(f"   Max overflow: {settings.DB_MAX_OVERFLOW}")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        if settings.ENVIRONMENT == "production":
            raise ServiceInitializationError(f"Database initialization failed: {str(e)}")
        logger.warning("⚠️ Continuing without database (development mode)")


async def initialize_redis() -> None:
    """
    Initialize Redis connection.
    """
    logger.info("📦 Initializing Redis...")
    
    if not settings.REDIS_URL:
        logger.warning("⚠️ Redis not configured - caching disabled")
        return
    
    try:
        if redis_client:
            await redis_client.ping()
            
            # Set Redis configuration
            await redis_client.config_set('maxmemory-policy', 'allkeys-lru')
            await redis_client.config_set('notify-keyspace-events', 'Ex')
            
            # Test basic operations
            test_key = f"test:{generate_secure_random_string(8)}"
            await redis_client.setex(test_key, 10, "test")
            test_value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            if test_value:
                logger.info("✅ Redis initialized successfully")
                logger.info(f"   Host: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
                logger.info(f"   DB: {settings.REDIS_DB}")
            else:
                logger.warning("⚠️ Redis test operation failed")
        else:
            logger.warning("⚠️ Redis client not available")
            
    except Exception as e:
        logger.error(f"❌ Redis initialization failed: {str(e)}")
        if settings.ENVIRONMENT == "production":
            raise ServiceInitializationError(f"Redis initialization failed: {str(e)}")
        logger.warning("⚠️ Continuing without Redis (development mode)")


async def initialize_cache() -> None:
    """
    Initialize cache manager.
    """
    logger.info("📦 Initializing cache manager...")
    
    try:
        if settings.CACHE_ENABLED:
            await cache_manager.initialize()
            
            # Clear any stale cache
            if settings.CLEAR_CACHE_ON_STARTUP:
                await cache_manager.clear_all()
                logger.info("   Cleared stale cache entries")
            
            logger.info(f"✅ Cache manager initialized (TTL: {settings.CACHE_TTL}s)")
        else:
            logger.info("⚠️ Cache disabled by configuration")
            
    except Exception as e:
        logger.error(f"❌ Cache initialization failed: {str(e)}")
        logger.warning("⚠️ Continuing without cache")


async def initialize_queue() -> None:
    """
    Initialize message queue.
    """
    logger.info("📦 Initializing queue manager...")
    
    try:
        if settings.QUEUE_ENABLED:
            await queue_manager.initialize()
            
            # Register queue handlers
            await register_queue_handlers()
            
            logger.info("✅ Queue manager initialized")
            logger.info(f"   Queues: {', '.join(queue_manager.get_queue_names())}")
        else:
            logger.info("⚠️ Queue disabled by configuration")
            
    except Exception as e:
        logger.error(f"❌ Queue initialization failed: {str(e)}")
        logger.warning("⚠️ Continuing without queue")


async def initialize_scheduler() -> None:
    """
    Initialize task scheduler.
    """
    logger.info("📦 Initializing scheduler...")
    
    try:
        if settings.SCHEDULER_ENABLED:
            await scheduler.initialize()
            
            # Register scheduled jobs
            await register_scheduled_jobs()
            
            # Start scheduler
            await scheduler.start()
            
            logger.info("✅ Scheduler initialized")
            logger.info(f"   Jobs: {len(scheduler.get_jobs())} scheduled")
        else:
            logger.info("⚠️ Scheduler disabled by configuration")
            
    except Exception as e:
        logger.error(f"❌ Scheduler initialization failed: {str(e)}")
        logger.warning("⚠️ Continuing without scheduler")


async def initialize_metrics() -> None:
    """
    Initialize metrics collector.
    """
    logger.info("📦 Initializing metrics collector...")
    
    try:
        if settings.METRICS_ENABLED:
            await metrics_collector.initialize()
            
            # Set default metrics
            await metrics_collector.set_gauge("app_startup_time", datetime.utcnow().timestamp())
            await metrics_collector.set_gauge("app_version", float(settings.VERSION))
            
            logger.info("✅ Metrics collector initialized")
            logger.info(f"   Endpoint: /metrics")
        else:
            logger.info("⚠️ Metrics disabled by configuration")
            
    except Exception as e:
        logger.error(f"❌ Metrics initialization failed: {str(e)}")
        logger.warning("⚠️ Continuing without metrics")


async def initialize_websocket() -> None:
    """
    Initialize WebSocket manager.
    """
    logger.info("📦 Initializing WebSocket manager...")
    
    try:
        if settings.WEBSOCKET_ENABLED:
            await websocket_manager.initialize()
            
            # Set up WebSocket event handlers
            await register_websocket_handlers()
            
            logger.info("✅ WebSocket manager initialized")
            logger.info(f"   Path: /ws")
        else:
            logger.info("⚠️ WebSocket disabled by configuration")
            
    except Exception as e:
        logger.error(f"❌ WebSocket initialization failed: {str(e)}")
        logger.warning("⚠️ Continuing without WebSocket")


async def initialize_email() -> None:
    """
    Initialize email service.
    """
    logger.info("📦 Initializing email service...")
    
    try:
        if settings.EMAIL_ENABLED:
            await email_service.initialize()
            
            # Test email configuration
            if settings.TEST_EMAIL_ON_STARTUP:
                await email_service.test_connection()
                logger.info("   Email connection test successful")
            
            logger.info("✅ Email service initialized")
            logger.info(f"   SMTP: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        else:
            logger.info("⚠️ Email service disabled by configuration")
            
    except Exception as e:
        logger.error(f"❌ Email service initialization failed: {str(e)}")
        logger.warning("⚠️ Continuing without email service")


async def register_queue_handlers() -> None:
    """
    Register message queue handlers.
    """
    # Email queue handlers
    await queue_manager.register_handler(
        "email",
        "send_welcome_email",
        email_service.send_welcome_email
    )
    await queue_manager.register_handler(
        "email",
        "send_password_reset",
        email_service.send_password_reset
    )
    await queue_manager.register_handler(
        "email",
        "send_reservation_confirmation",
        email_service.send_reservation_confirmation
    )
    
    # Notification queue handlers
    await queue_manager.register_handler(
        "notification",
        "send_push_notification",
        websocket_manager.send_notification
    )
    
    # Report generation handlers
    from ..services.reporting import generate_report
    await queue_manager.register_handler(
        "report",
        "generate_report",
        generate_report
    )
    
    logger.info("   Queue handlers registered: email, notification, report")


async def register_scheduled_jobs() -> None:
    """
    Register scheduled jobs.
    """
    # Clean up expired reservations (every hour)
    from ..crud import crud_reservation
    await scheduler.add_job(
        "cleanup_expired_reservations",
        crud_reservation.cleanup_expired,
        trigger="interval",
        hours=1,
        next_run_time=datetime.utcnow() + timedelta(minutes=5)
    )
    
    # Send reminder emails (every 15 minutes)
    from ..services.reminder import send_reservation_reminders
    await scheduler.add_job(
        "send_reminders",
        send_reservation_reminders,
        trigger="interval",
        minutes=15
    )
    
    # Generate daily reports (at 1 AM)
    from ..services.reporting import generate_daily_report
    await scheduler.add_job(
        "generate_daily_report",
        generate_daily_report,
        trigger="cron",
        hour=1,
        minute=0
    )
    
    # Clean up old audit logs (daily at 2 AM)
    from ..crud import crud_audit_log
    await scheduler.add_job(
        "cleanup_audit_logs",
        crud_audit_log.cleanup_old_logs,
        trigger="cron",
        hour=2,
        minute=0,
        kwargs={"days_to_keep": 90}
    )
    
    # Update parking spot status (every 5 minutes)
    from ..crud import crud_parking_spot
    await scheduler.add_job(
        "update_spot_status",
        crud_parking_spot.update_all_statuses,
        trigger="interval",
        minutes=5
    )
    
    # Sync with external systems (every hour)
    if settings.EXTERNAL_SYNC_ENABLED:
        from ..services.sync import sync_external_systems
        await scheduler.add_job(
            "external_sync",
            sync_external_systems,
            trigger="interval",
            hours=1
        )
    
    logger.info(f"   Scheduled jobs registered: {len(scheduler.get_jobs())}")


async def register_websocket_handlers() -> None:
    """
    Register WebSocket event handlers.
    """
    # Connection events
    websocket_manager.register_handler("connect", handle_websocket_connect)
    websocket_manager.register_handler("disconnect", handle_websocket_disconnect)
    
    # Message handlers
    websocket_manager.register_handler("message", handle_websocket_message)
    websocket_manager.register_handler("ping", handle_websocket_ping)
    websocket_manager.register_handler("subscribe", handle_websocket_subscribe)
    websocket_manager.register_handler("unsubscribe", handle_websocket_unsubscribe)
    
    logger.info("   WebSocket handlers registered")


async def handle_websocket_connect(client_id: str) -> None:
    """
    Handle WebSocket connection.
    """
    logger.debug(f"WebSocket client connected: {client_id}")
    await metrics_collector.increment_counter("websocket_connections_total")


async def handle_websocket_disconnect(client_id: str) -> None:
    """
    Handle WebSocket disconnection.
    """
    logger.debug(f"WebSocket client disconnected: {client_id}")


async def handle_websocket_message(client_id: str, message: Dict[str, Any]) -> None:
    """
    Handle WebSocket message.
    """
    logger.debug(f"WebSocket message from {client_id}: {message}")


async def handle_websocket_ping(client_id: str) -> None:
    """
    Handle WebSocket ping.
    """
    await websocket_manager.send_to_client(client_id, {"type": "pong"})


async def handle_websocket_subscribe(client_id: str, channel: str) -> None:
    """
    Handle WebSocket subscription.
    """
    await websocket_manager.subscribe(client_id, channel)
    logger.debug(f"Client {client_id} subscribed to {channel}")


async def handle_websocket_unsubscribe(client_id: str, channel: str) -> None:
    """
    Handle WebSocket unsubscription.
    """
    await websocket_manager.unsubscribe(client_id, channel)


async def start_background_tasks() -> None:
    """
    Start background tasks.
    """
    logger.info("🔄 Starting background tasks...")
    
    tasks = []
    
    # Health monitoring
    if settings.ENABLE_HEALTH_MONITORING:
        tasks.append(asyncio.create_task(
            health_monitoring_task(),
            name="health_monitor"
        ))
    
    # Cache cleanup
    if settings.ENABLE_CACHE_CLEANUP:
        tasks.append(asyncio.create_task(
            cache_cleanup_task(),
            name="cache_cleanup"
        ))
    
    # Metrics aggregation
    if settings.ENABLE_METRICS_AGGREGATION:
        tasks.append(asyncio.create_task(
            metrics_aggregation_task(),
            name="metrics_aggregator"
        ))
    
    # Session cleanup
    if settings.ENABLE_SESSION_CLEANUP:
        tasks.append(asyncio.create_task(
            session_cleanup_task(),
            name="session_cleanup"
        ))
    
    # Database maintenance
    if settings.ENABLE_DB_MAINTENANCE:
        tasks.append(asyncio.create_task(
            database_maintenance_task(),
            name="db_maintenance"
        ))
    
    # Store tasks for cleanup
    background_tasks.extend(tasks)
    
    if tasks:
        logger.info(f"✅ Started {len(tasks)} background tasks: {', '.join(t.get_name() for t in tasks)}")
    else:
        logger.info("ℹ️ No background tasks configured")


async def cancel_background_tasks() -> None:
    """
    Cancel all background tasks gracefully.
    """
    if not background_tasks:
        return
    
    logger.info(f"🔄 Cancelling {len(background_tasks)} background tasks...")
    
    cancelled_count = 0
    for task in background_tasks:
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=5.0)
                cancelled_count += 1
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error cancelling task {task.get_name()}: {str(e)}")
    
    background_tasks.clear()
    logger.info(f"✅ Cancelled {cancelled_count} background tasks")


async def health_monitoring_task() -> None:
    """
    Background task for health monitoring.
    """
    logger.info("   Health monitor task started")
    
    while True:
        try:
            # Perform health checks
            health_status = await health_checker.check_all()
            
            # Log if any service is unhealthy
            unhealthy_services = [
                service for service, status in health_status.items()
                if status != "healthy"
            ]
            
            if unhealthy_services:
                logger.warning(f"Unhealthy services detected: {', '.join(unhealthy_services)}")
                
                # Increment metric
                await metrics_collector.increment_counter(
                    "health_check_failures_total",
                    tags={"services": ",".join(unhealthy_services)}
                )
            
            # Update metrics
            await metrics_collector.set_gauge(
                "health_check_timestamp",
                datetime.utcnow().timestamp()
            )
            
            # Wait before next check
            await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
            
        except asyncio.CancelledError:
            logger.info("   Health monitor task cancelled")
            break
        except Exception as e:
            logger.error(f"Health monitoring error: {str(e)}")
            await asyncio.sleep(60)


async def cache_cleanup_task() -> None:
    """
    Background task for cache cleanup.
    """
    logger.info("   Cache cleanup task started")
    
    while True:
        try:
            # Clean expired cache entries
            cleaned_count = await cache_manager.cleanup_expired()
            
            if cleaned_count > 0:
                logger.debug(f"Cleaned {cleaned_count} expired cache entries")
            
            # Wait before next cleanup
            await asyncio.sleep(settings.CACHE_CLEANUP_INTERVAL)
            
        except asyncio.CancelledError:
            logger.info("   Cache cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Cache cleanup error: {str(e)}")
            await asyncio.sleep(300)


async def metrics_aggregation_task() -> None:
    """
    Background task for metrics aggregation.
    """
    logger.info("   Metrics aggregator task started")
    
    while True:
        try:
            # Aggregate metrics
            await metrics_collector.aggregate()
            
            # Push to external monitoring if configured
            if settings.PUSH_METRICS_TO_EXTERNAL:
                await metrics_collector.push_to_external()
            
            # Wait before next aggregation
            await asyncio.sleep(settings.METRICS_AGGREGATION_INTERVAL)
            
        except asyncio.CancelledError:
            logger.info("   Metrics aggregator task cancelled")
            break
        except Exception as e:
            logger.error(f"Metrics aggregation error: {str(e)}")
            await asyncio.sleep(60)


async def session_cleanup_task() -> None:
    """
    Background task for cleaning up expired sessions.
    """
    logger.info("   Session cleanup task started")
    
    while True:
        try:
            if redis_client:
                # Clean up expired sessions
                pattern = "session:*"
                cursor = 0
                deleted_count = 0
                
                while True:
                    cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
                    for key in keys:
                        ttl = await redis_client.ttl(key)
                        if ttl == -2:  # Key doesn't exist
                            continue
                        if ttl == -1:  # No expiration set
                            await redis_client.expire(key, 86400)  # Set 24h expiration
                    
                    if cursor == 0:
                        break
                
                logger.debug(f"Session cleanup completed")
            
            await asyncio.sleep(3600)  # Run every hour
            
        except asyncio.CancelledError:
            logger.info("   Session cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Session cleanup error: {str(e)}")
            await asyncio.sleep(300)


async def database_maintenance_task() -> None:
    """
    Background task for database maintenance.
    """
    logger.info("   Database maintenance task started")
    
    while True:
        try:
            async with AsyncSessionLocal() as session:
                # Run VACUUM ANALYZE on tables
                await session.execute("VACUUM ANALYZE")
                
                # Update statistics
                await session.execute("ANALYZE")
                
                logger.debug("Database maintenance completed")
            
            await asyncio.sleep(86400)  # Run daily
            
        except asyncio.CancelledError:
            logger.info("   Database maintenance task cancelled")
            break
        except Exception as e:
            logger.error(f"Database maintenance error: {str(e)}")
            await asyncio.sleep(3600)


async def shutdown_database() -> None:
    """
    Shutdown database connections.
    """
    logger.info("📦 Shutting down database...")
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing database connections: {str(e)}")


async def shutdown_redis() -> None:
    """
    Shutdown Redis connection.
    """
    logger.info("📦 Shutting down Redis...")
    try:
        if redis_client:
            await redis_client.close()
            logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing Redis connection: {str(e)}")


async def shutdown_cache() -> None:
    """
    Shutdown cache manager.
    """
    logger.info("📦 Shutting down cache manager...")
    try:
        await cache_manager.cleanup()
        logger.info("✅ Cache manager shut down")
    except Exception as e:
        logger.error(f"❌ Error shutting down cache: {str(e)}")


async def shutdown_queue() -> None:
    """
    Shutdown queue manager.
    """
    logger.info("📦 Shutting down queue manager...")
    try:
        if settings.QUEUE_ENABLED:
            await queue_manager.shutdown()
            logger.info("✅ Queue manager shut down")
    except Exception as e:
        logger.error(f"❌ Error shutting down queue: {str(e)}")


async def shutdown_scheduler() -> None:
    """
    Shutdown scheduler.
    """
    logger.info("📦 Shutting down scheduler...")
    try:
        if settings.SCHEDULER_ENABLED:
            await scheduler.shutdown()
            logger.info("✅ Scheduler shut down")
    except Exception as e:
        logger.error(f"❌ Error shutting down scheduler: {str(e)}")


async def shutdown_websocket() -> None:
    """
    Shutdown WebSocket manager.
    """
    logger.info("📦 Shutting down WebSocket manager...")
    try:
        if settings.WEBSOCKET_ENABLED:
            await websocket_manager.shutdown()
            logger.info("✅ WebSocket manager shut down")
    except Exception as e:
        logger.error(f"❌ Error shutting down WebSocket: {str(e)}")


async def shutdown_metrics() -> None:
    """
    Shutdown metrics collector.
    """
    logger.info("📦 Shutting down metrics collector...")
    try:
        if settings.METRICS_ENABLED:
            # Push final metrics
            await metrics_collector.push_final_metrics()
            await metrics_collector.cleanup()
            logger.info("✅ Metrics collector shut down")
    except Exception as e:
        logger.error(f"❌ Error shutting down metrics: {str(e)}")


async def shutdown_email() -> None:
    """
    Shutdown email service.
    """
    logger.info("📦 Shutting down email service...")
    try:
        if settings.EMAIL_ENABLED:
            await email_service.shutdown()
            logger.info("✅ Email service shut down")
    except Exception as e:
        logger.error(f"❌ Error shutting down email: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Alternative to separate startup/shutdown handlers.
    """
    # Startup
    await startup_handler()
    yield
    # Shutdown
    await shutdown_handler()


def setup_signal_handlers() -> None:
    """
    Setup signal handlers for graceful shutdown.
    """
    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        asyncio.create_task(shutdown_handler())
    
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)


# Export handlers
__all__ = [
    'startup_handler',
    'shutdown_handler',
    'lifespan',
    'setup_signal_handlers'
]