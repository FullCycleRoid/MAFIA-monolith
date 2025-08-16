from app.domains.game import service as game_service

async def get_mafia_players(game_id: str) -> list[str]:
    players = await game_service.get_players(game_id, role="mafia")
    return [p.user_id for p in players]