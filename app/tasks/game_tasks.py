from app.core.celery import celery_app
from app.domains.game import service

@celery_app.task
def advance_phase(game_id: str):
    service.advance_phase(game_id)
    