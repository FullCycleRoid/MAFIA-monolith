from app.core import event_bus
from app.shared.schemas.events import GamePhaseChanged

from . import service
from .room_manager import room_manager


async def handle_phase_change(event_data: dict):
    event = GamePhaseChanged(**event_data)
    commands = await service.make_voice_commands_from_phase(event)

    # Батчинг команд (10+ команд в одном запросе)
    batch_size = 10
    for i in range(0, len(commands), batch_size):
        batch = commands[i : i + batch_size]
        await room_manager.apply_commands(batch)


def register_event_handlers():
    event_bus.event_bus.subscribe("game:phase_changed", handle_phase_change)
