from app.core import event_bus
from . import service
from app.shared.schemas.events import GamePhaseChanged

async def handle_game_end(event_data: dict):
    event = GamePhaseChanged(**event_data)
    if event.phase == "ended":
        await service.award_tokens(event.game_id)

def register_event_handlers():
    event_bus.event_bus.subscribe("game:phase_changed", handle_game_end)
