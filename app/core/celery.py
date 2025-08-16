from celery import Celery
from .config import settings

celery_app = Celery(
    "mafia_tasks",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.game_tasks",
        "app.tasks.voice_tasks",
        "app.tasks.economy_tasks"
    ]
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
