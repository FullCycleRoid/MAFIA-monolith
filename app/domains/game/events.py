# app/domains/game/events.py
from app.core import event_bus
from app.core.websocket_manager import websocket_manager

async def _on_chat_message(data: dict):
    game_id = data.get("game_id")
    user_id = data.get("user_id")
    text = data.get("text")
    if not game_id or not user_id or not text:
        return
    await websocket_manager.broadcast(game_id, {
        "event": "chat",
        "from": user_id,
        "text": text,
    })

async def _on_emoji(data: dict):
    game_id = data.get("game_id")
    user_id = data.get("user_id")
    emoji = data.get("emoji")
    if not game_id or not user_id or not emoji:
        return
    await websocket_manager.broadcast(game_id, {
        "event": "emoji",
        "from": user_id,
        "emoji": emoji,
    })

def register_event_handlers():
    event_bus.event_bus.subscribe("websocket:chat", _on_chat_message)
    event_bus.event_bus.subscribe("websocket:emoji", _on_emoji)
