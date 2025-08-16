from sqlalchemy import select
from app.core.database import get_db
from .models import Player


async def get_players(game_id: str, role: str = None):
    async with get_db() as db:
        query = select(Player).filter(Player.game_id == game_id)
        if role:
            query = query.filter(Player.role == role)
        result = await db.execute(query)
        return result.scalars().all()
