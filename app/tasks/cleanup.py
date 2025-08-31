from asgiref.sync import async_to_sync
from app.core.celery import celery_app
from app.domains.game.repository import cleanup_old_games

@celery_app.task
def cleanup_old_games_task(days: int = 30):
    async_to_sync(cleanup_old_games)(days)
