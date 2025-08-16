import json
from app.core import event_bus

async def handle_websocket_message(game_id: str, message: str):
    try:
        data = json.loads(message)
        # Публикация события в шину
        event_bus.event_bus.publish(f"game:{game_id}:message", data)
    except json.JSONDecodeError:
        pass
