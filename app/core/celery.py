from celery import Celery

from .config import settings

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
    # Конфигурация Celery
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


from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "process-withdrawals": {
        "task": "app.tasks.withdrawal_processor.process_pending_withdrawals",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "update-token-price": {
        "task": "app.tasks.price_updater.update_token_price",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "cleanup-old-games": {
        "task": "app.tasks.cleanup.cleanup_old_games_task",
        "schedule": crontab(hour=3, minute=0),
    },
}
