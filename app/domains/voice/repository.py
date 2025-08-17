# app/domains/voice/repository.py
from sqlalchemy import select, update

from app.core.database import get_db


async def disconnect_user(user_id: str):
    """Отключение пользователя от голосовых комнат"""
    from app.domains.voice.models import Participant

    async with get_db() as db:
        # Находим активные участия
        result = await db.execute(
            select(Participant).filter(Participant.user_id == user_id)
        )
        participants = result.scalars().all()

        # Удаляем из комнат
        for participant in participants:
            db.delete(participant)

        await db.commit()


async def mute_user_globally(user_id: str, muted: bool):
    """Глобальный мьют пользователя во всех комнатах"""
    from app.domains.voice.models import Participant

    async with get_db() as db:
        result = await db.execute(
            update(Participant)
            .where(Participant.user_id == user_id)
            .values(muted=muted)
        )
        await db.commit()
        return result.rowcount > 0
