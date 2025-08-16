from fastapi import WebSocket
from typing import Dict, List

from starlette.websockets import WebSocketDisconnect

from app.core.event_bus import event_bus


class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    async def handle_connection(self, game_id: str, websocket: WebSocket):
        await self.connect(game_id, websocket)
        try:
            while True:
                data = await websocket.receive_text()
                await event_bus.publish(f"game:{game_id}:message", data)
        except WebSocketDisconnect:
            self.disconnect(game_id, websocket)

    async def connect(self, game_id: str, websocket: WebSocket):
        await websocket.accept()
        if game_id not in self.connections:
            self.connections[game_id] = []
        self.connections[game_id].append(websocket)

    def disconnect(self, game_id: str, websocket: WebSocket):
        if game_id in self.connections:
            self.connections[game_id].remove(websocket)

    async def broadcast(self, game_id: str, message: dict):
        if game_id in self.connections:
            for connection in self.connections[game_id]:
                await connection.send_json(message)


websocket_manager = WebSocketManager()
