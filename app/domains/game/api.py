from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from . import service
from app.core import event_bus
from app.shared.schemas.events import GamePlayerAction

router = APIRouter()

@router.post("/create")
async def create_game():
    return await service.create_game()

@router.post("/{game_id}/advance_phase")
async def advance_phase(game_id: str):
    return await service.advance_phase(game_id)

@router.post("/actions/vote")
async def vote_action(action: dict):
    event = GamePlayerAction(**action)
    event_bus.event_bus.publish("game:player_action", event.dict())
    return {"status": "ok"}

async def handle_websocket(websocket: WebSocket, game_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Обработка сообщений через шину событий
            event_bus.event_bus.publish(f"game:{game_id}:ws", data)
            await websocket.send_text(data)
    except WebSocketDisconnect:
        return
