from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


async def get_game_db():
    async with get_db() as db:
        yield db
