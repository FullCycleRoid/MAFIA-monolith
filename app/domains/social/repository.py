# app/domains/social/repository.py
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, select

from app.core.database import get_db
from app.domains.social.models import SocialInteractionRecord, UserStats


async def save_interaction(interaction_data: Dict) -> SocialInteractionRecord:
    """Сохранение социального взаимодействия"""
    async with get_db() as db:
        interaction = SocialInteractionRecord(
            id=interaction_data["interaction_id"],
            from_user=interaction_data["from_user"],
            to_user=interaction_data["to_user"],
            type=interaction_data["type"],
            game_id=interaction_data.get("game_id"),
            timestamp=interaction_data["timestamp"],
            data=interaction_data.get("data", {}),
        )
        db.add(interaction)
        await db.commit()
        return interaction


async def get_user_stats(user_id: str) -> Optional[UserStats]:
    """Получение социальной статистики пользователя"""
    async with get_db() as db:
        result = await db.execute(
            select(UserStats).filter(UserStats.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def update_user_stats(user_id: str, field: str, increment: int = 1):
    """Обновление статистики пользователя"""
    async with get_db() as db:
        stats = await get_user_stats(user_id)
        if not stats:
            stats = UserStats(user_id=user_id)
            db.add(stats)

        current_value = getattr(stats, field, 0)
        setattr(stats, field, current_value + increment)

        await db.commit()


async def get_recent_reports(
    user_id: str, hours: int = 24
) -> List[SocialInteractionRecord]:
    """Получение недавних жалоб на пользователя"""
    async with get_db() as db:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(SocialInteractionRecord).filter(
                and_(
                    SocialInteractionRecord.to_user == user_id,
                    SocialInteractionRecord.type == "report",
                    SocialInteractionRecord.timestamp > cutoff_time,
                )
            )
        )
        return result.scalars().all()
