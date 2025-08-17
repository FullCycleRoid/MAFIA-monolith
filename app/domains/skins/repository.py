# app/domains/skins/repository.py
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select

from app.core.database import get_db
from app.domains.skins.models import SkinCatalog, UserSkin


async def add_skin_to_user(user_id: str, skin_id: str):
    """Добавление скина пользователю"""
    async with get_db() as db:
        user_skin = UserSkin(
            id=str(uuid.uuid4()),
            user_id=user_id,
            skin_id=skin_id,
            purchased_at=datetime.utcnow(),
        )
        db.add(user_skin)
        await db.commit()


async def get_user_skins(user_id: str) -> List[str]:
    """Получение списка скинов пользователя"""
    async with get_db() as db:
        result = await db.execute(
            select(UserSkin.skin_id).filter(UserSkin.user_id == user_id)
        )
        return result.scalars().all()


async def get_skin_info(skin_id: str) -> Optional[SkinCatalog]:
    """Получение информации о скине"""
    async with get_db() as db:
        result = await db.execute(select(SkinCatalog).filter(SkinCatalog.id == skin_id))
        return result.scalar_one_or_none()
