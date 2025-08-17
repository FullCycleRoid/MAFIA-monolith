from app.domains.game import service as game_service
from app.shared.schemas.events import GamePhaseChanged, VoiceMutePlayer

from .room_manager import room_manager


async def create_room(game_id: str):
    room_id = await room_manager.create_room(game_id)
    return {"room_id": room_id}


async def get_room(room_id: str):
    return {"room_id": room_id}


async def make_voice_commands_from_phase(
    event: GamePhaseChanged,
) -> list[VoiceMutePlayer]:
    room_id = room_manager.get_room_id(event.game_id)
    if not room_id:
        return []

    if event.phase == "day":
        return [VoiceMutePlayer(room_id=room_id, player_id="*", mute=False)]
    elif event.phase == "night":
        commands = [VoiceMutePlayer(room_id=room_id, player_id="*", mute=True)]
        mafia_players = await game_service.get_players(event.game_id, role="mafia")
        for player in mafia_players:
            commands.append(
                VoiceMutePlayer(room_id=room_id, player_id=player.user_id, mute=False)
            )
        return commands
    return []
