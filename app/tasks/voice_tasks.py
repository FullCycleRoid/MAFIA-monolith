from asgiref.sync import async_to_sync
from app.core.celery import celery_app
from app.domains.voice.events import handle_phase_change

@celery_app.task
def process_phase_change(event: dict):
    async_to_sync(handle_phase_change)(event)
