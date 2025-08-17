from app.core.celery import celery_app
from app.domains.economy import service


@celery_app.task
def award_tokens(game_id: str):
    # Логика начисления токенов
    print(f"Awarding tokens for game: {game_id}")
