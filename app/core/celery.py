# app/core/celery.py
from celery import Celery
from app.core.config import settings
from celery.schedules import crontab

# ВАЖНО: объект называется celery_app
celery_app = Celery(
    "mafia_tasks",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.game_tasks",
        "app.tasks.voice_tasks",
        "app.tasks.economy_tasks",
        "app.tasks.withdrawal_processor",
        "app.tasks.cleanup",
        "app.tasks.price_updater",
    ],
)

def init_celery():
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        worker_proc_alive_timeout=30,
        worker_send_task_events=True,
        broker_connection_retry_on_startup=True,
        task_track_started=True,
    )

async def check_connection() -> bool:
    try:
        with celery_app.connection_or_acquire() as conn:
            conn.heartbeat_check()
            return True
    except Exception:
        return False

celery_app.conf.beat_schedule = {
    "process-withdrawals": {
        "task": "app.tasks.withdrawal_processor.process_pending_withdrawals",
        "schedule": crontab(minute="*/5"),
    },
    "update-token-price": {
        "task": "app.tasks.price_updater.update_token_price",
        "schedule": crontab(minute="*/15"),
    },
    "cleanup-old-games": {
        "task": "app.tasks.cleanup.cleanup_old_games_task",
        "schedule": crontab(hour=3, minute=0),
    },
}
