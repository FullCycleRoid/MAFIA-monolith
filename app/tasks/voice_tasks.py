from app.core.celery import celery_app
from app.domains.voice import service

@celery_app.task
def process_phase_change(event: dict):
    service.handle_phase_change(event)
    