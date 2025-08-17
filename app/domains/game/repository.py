from datetime import datetime
from typing import List

from sqlalchemy import and_, select

from app.core.database import get_db

from .models import Player


async def get_players(game_id: str, role: str = None):
    async with get_db() as db:
        query = select(Player).filter(Player.game_id == game_id)
        if role:
            query = query.filter(Player.role == role)
        result = await db.execute(query)
        return result.scalars().all()


# app/domains/game/repository.py (дополнения)
async def create_game_from_lobby(
    players: List["PlayerProfile"], settings: "LobbySettings"
) -> str:
    """Создание игры из лобби"""
    import uuid

    from app.domains.game.models import Game, Player

    game_id = str(uuid.uuid4())

    async with get_db() as db:
        # Создаем игру
        game = Game(id=game_id, status="starting", settings=settings.__dict__)
        db.add(game)

        # Добавляем игроков
        for profile in players:
            player = Player(
                id=str(uuid.uuid4()),
                game_id=game_id,
                user_id=profile.user_id,
                role="unassigned",
                alive=True,
            )
            db.add(player)

        await db.commit()

    return game_id


async def kick_player(user_id: str):
    """Исключение игрока из активных игр"""
    from app.domains.game.models import Player

    async with get_db() as db:
        # Находим активные игры игрока
        result = await db.execute(
            select(Player).filter(and_(Player.user_id == user_id, Player.alive == True))
        )
        active_players = result.scalars().all()

        # Помечаем как неактивного
        for player in active_players:
            player.alive = False
            player.kicked_at = datetime.utcnow()

        await db.commit()
