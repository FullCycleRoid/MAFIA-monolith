from asgiref.sync import async_to_sync
from app.core.celery import celery_app
from app.domains.economy import service

@celery_app.task
def award_tokens(game_id: str):
    async_to_sync(service.award_tokens)(game_id)
