# app/domains/moderation/repository.py
from datetime import datetime
from typing import Dict, List

from sqlalchemy import and_, or_, select

from app.core.database import get_db
from app.domains.moderation.models import BanRecord, ModeratorActionRecord


async def save_ban(ban_data: Dict) -> BanRecord:
    """Сохранение бана в БД"""
    async with get_db() as db:
        ban = BanRecord(
            id=ban_data["ban_id"],
            user_id=ban_data["user_id"],
            type=ban_data["type"],
            reason=ban_data["reason"],
            issued_by=ban_data["issued_by"],
            issued_at=ban_data["issued_at"],
            expires_at=ban_data.get("expires_at"),
            evidence=ban_data.get("evidence"),
        )
        db.add(ban)
        await db.commit()
        return ban


async def get_active_bans(user_id: str) -> List[BanRecord]:
    """Получение активных банов пользователя"""
    async with get_db() as db:
        now = datetime.utcnow()
        result = await db.execute(
            select(BanRecord).filter(
                and_(
                    BanRecord.user_id == user_id,
                    or_(BanRecord.expires_at.is_(None), BanRecord.expires_at > now),
                )
            )
        )
        return result.scalars().all()


async def save_moderator_action(action: "ModeratorAction"):
    """Сохранение действия модератора для аудита"""
    async with get_db() as db:
        record = ModeratorActionRecord(
            id=action.action_id,
            moderator_id=action.moderator_id,
            action_type=action.action_type,
            target_user=action.target_user,
            timestamp=action.timestamp,
            details=action.details,
        )
        db.add(record)
        await db.commit()
