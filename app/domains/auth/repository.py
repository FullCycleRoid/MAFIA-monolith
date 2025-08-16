import uuid

from sqlalchemy import select
from app.core.database import get_db
from .models import User

async def get_user_by_telegram_id(telegram_id: int):
    async with get_db() as db:
        result = await db.execute(select(User).filter(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

async def create_user(user_data: dict):
    async with get_db() as db:
        new_user = User(
            id=str(uuid.uuid4()),
            telegram_id=user_data["telegram_id"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            username=user_data["username"],
            language_code=user_data["language_code"],
            is_bot=user_data["is_bot"],
            allows_write_to_pm=user_data["allows_write_to_pm"]
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
