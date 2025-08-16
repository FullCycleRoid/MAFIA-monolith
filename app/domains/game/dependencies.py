from fastapi import Depends
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

async def get_game_db():
    async with get_db() as db:
        yield db