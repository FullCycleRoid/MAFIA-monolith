# app/domains/game/websocket.py
import json
from typing import Optional
from app.core.event_bus import event_bus

async def handle_websocket_message(game_id: str, message: str, user_id: Optional[str] = None):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return

    # нормализуем полезную нагрузку
    data.setdefault("game_id", game_id)
    if user_id:
        data.setdefault("user_id", user_id)

    # теперь корректно публикуем (это coroutine)
    await event_bus.publish(f"game:{game_id}:message", data)
