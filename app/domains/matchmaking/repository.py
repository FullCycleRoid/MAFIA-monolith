# app/domains/matchmaking/repository.py
from typing import Optional

from sqlalchemy import select

from app.core.database import get_db
from app.domains.matchmaking.entities import PlayerProfile


async def get_user_profile(user_id: str) -> Optional[PlayerProfile]:
    """Получение профиля игрока для матчмейкинга"""
    from app.domains.auth.models import User

    async with get_db() as db:
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Создаем PlayerProfile из данных пользователя
        return PlayerProfile(
            user_id=user.id,
            telegram_id=user.telegram_id,
            username=user.username or f"user_{user.telegram_id}",
            rating=getattr(user, "rating", 1000),
            country=getattr(user, "country", "US"),
            native_language=user.language_code,
            spoken_languages=getattr(user, "spoken_languages", []),
            purchased_languages=getattr(user, "purchased_languages", []),
            games_played=getattr(user, "games_played", 0),
            win_rate=getattr(user, "win_rate", 0.0),
            linguistic_rating=getattr(user, "linguistic_rating", {}),
            is_premium=getattr(user, "is_premium", False),
            skin_id=getattr(user, "skin_id", None),
            banned_until=getattr(user, "banned_until", None),
            muted_players=set(getattr(user, "muted_players", [])),
        )
