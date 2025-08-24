# app/tasks/cleanup.py
import asyncio
from app.core.celery import celery_app
from app.domains.game.repository import cleanup_old_games

@celery_app.task
def cleanup_old_games_task(days: int = 30):
    asyncio.run(cleanup_old_games(days))
