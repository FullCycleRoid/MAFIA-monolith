from app.core import event_bus

from . import repository
from .logic import GameLogic, PhaseManager

game_logic = GameLogic()
phase_manager = PhaseManager(game_logic)


async def create_game():
    return await phase_manager.start_game()


async def advance_phase(game_id: str):
    event = phase_manager.advance(game_id)
    event_bus.event_bus.publish("game:phase_changed", event.dict())
    return event


async def get_players(game_id: str, role: str = None):
    return await repository.get_players(game_id, role)
