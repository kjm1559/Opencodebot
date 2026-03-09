"""
Celery worker configuration.
"""
import os
import logging
from celery import Celery
from celery.schedules import crontab

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",  # noqa: UP031
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Load settings
from app.config import get_settings

settings = get_settings()

# Create Celery app
app = Celery(
    "stocknews",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100,
    
    # Rate limiting
    task_default_rate_limit="1/min",
    
    # Beat schedule
    beat_schedule={
        "collect-news-every-5-minutes": {
            "task": "app.tasks.collect_news_for_all_companies",
            "schedule": 300,  # 5 minutes
            "options": {
                "queue": "news_collection",
                "rate_limit": "1/m",  # Prevent overlapping runs
            },
        },
        "cleanup-old-articles-daily": {
            "task": "app.tasks.cleanup_old_articles",
            "schedule": crontab(hour=3, minute=0),  # 3 AM daily
            "options": {
                "queue": "maintenance",
            },
        },
    },
)

# Tasks are imported explicitly in tasks.py
# No autodiscovery needed

logger.info("Celery configuration loaded")
logger.info(f"Broker URL: {settings.celery_broker_url}")
logger.info(f"Result backend: {settings.celery_result_backend}")
