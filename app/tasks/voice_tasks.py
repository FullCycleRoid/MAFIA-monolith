# app/tasks/voice_tasks.py
import asyncio
from app.core.celery import celery_app
from app.domains.voice.events import handle_phase_change

@celery_app.task
def process_phase_change(event: dict):
    asyncio.run(handle_phase_change(event))
