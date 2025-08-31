from typing import Optional
from fastapi import APIRouter, WebSocket
from app.shared.utils.security import decode_token
from app.core.websocket_manager import websocket_manager

ws_router = APIRouter()

@ws_router.websocket("/{game_id}/ws")
async def websocket_game_endpoint(websocket: WebSocket, game_id: str):
    token = websocket.query_params.get("token")
    reconnect_token: Optional[str] = websocket.query_params.get("reconnect_token")
    if not token:
        await websocket.close(code=4401)
        return
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=4401)
        return
    user_id = str(payload["sub"])
    await websocket_manager.connect(websocket, user_id=user_id, game_id=game_id, reconnect_token=reconnect_token)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket_manager.handle_message(websocket, data)
    except Exception:
        websocket_manager.disconnect(websocket)
