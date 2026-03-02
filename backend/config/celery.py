"""Celery configuration for task queue management."""

from celery import Celery
from celery.schedules import crontab
import logging

from . import config

logger = logging.getLogger(__name__)


def make_celery(app_name: str = __name__) -> Celery:
    """Create Celery instance."""
    celery = Celery(
        app_name,
        broker=config.CELERY_BROKER_URL,
        backend=config.CELERY_RESULT_BACKEND,
        include=['app.tasks']
    )
    
    # Configure Celery
    celery.conf.update(
        task_serializer=config.CELERY_TASK_SERIALIZER,
        result_serializer=config.CELERY_RESULT_SERIALIZER,
        accept_content=config.CELERY_ACCEPT_CONTENT,
        timezone=config.CELERY_TIMEZONE,
        enable_utc=config.CELERY_ENABLE_UTC,
        task_track_started=config.CELERY_TASK_TRACK_STARTED,
        task_time_limit=config.CELERY_TASK_TIME_LIMIT,
        task_soft_time_limit=config.CELERY_TASK_SOFT_TIME_LIMIT,
        worker_max_tasks_per_child=1000,
        worker_prefetch_multiplier=1,
        result_expires=3600,
    )
    
    # Configure beat schedule
    celery.conf.beat_schedule = {
        'cleanup-expired-reservations': {
            'task': 'app.tasks.cleanup_expired_reservations',
            'schedule': crontab(minute='*/15'),  # Every 15 minutes
        },
        'send-reservation-reminders': {
            'task': 'app.tasks.send_reservation_reminders',
            'schedule': crontab(minute='*/30'),  # Every 30 minutes
        },
        'update-spot-availability': {
            'task': 'app.tasks.update_spot_availability',
            'schedule': crontab(minute='*/5'),  # Every 5 minutes
        },
        'generate-daily-reports': {
            'task': 'app.tasks.generate_daily_reports',
            'schedule': crontab(hour=0, minute=5),  # Daily at 12:05 AM
        },
        'cleanup-audit-logs': {
            'task': 'app.tasks.cleanup_audit_logs',
            'schedule': crontab(hour=1, minute=0),  # Daily at 1:00 AM
        },
        'sync-elasticsearch': {
            'task': 'app.tasks.sync_elasticsearch',
            'schedule': crontab(minute='*/10'),  # Every 10 minutes
        },
        'backup-database': {
            'task': 'app.tasks.backup_database',
            'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM
        },
    }
    
    if config.TESTING:
        celery.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
    
    logger.info(f"Celery configured with broker={config.CELERY_BROKER_URL}")
    return celery


# Global Celery instance
celery = make_celery()