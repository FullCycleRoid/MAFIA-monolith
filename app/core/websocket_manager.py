import json
from typing import Dict, List, Optional

from fastapi import WebSocket

from app.core.event_bus import event_bus


class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, List[WebSocket]] = {}  # user_id -> websockets
        self.connection_metadata: Dict[WebSocket, Dict] = {}  # websocket -> metadata

    async def connect(
        self,
        websocket: WebSocket,
        game_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Подключение клиента"""
        await websocket.accept()

        # Сохраняем метаданные соединения
        self.connection_metadata[websocket] = {"game_id": game_id, "user_id": user_id}

        # Добавляем в игровые соединения
        if game_id:
            if game_id not in self.connections:
                self.connections[game_id] = []
            self.connections[game_id].append(websocket)

        # Добавляем в пользовательские соединения
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Отключение клиента"""
        metadata = self.connection_metadata.get(websocket, {})

        # Удаляем из игровых соединений
        game_id = metadata.get("game_id")
        if game_id and game_id in self.connections:
            if websocket in self.connections[game_id]:
                self.connections[game_id].remove(websocket)
            if not self.connections[game_id]:
                del self.connections[game_id]

        # Удаляем из пользовательских соединений
        user_id = metadata.get("user_id")
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # Удаляем метаданные
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

    async def broadcast(self, game_id: str, message: dict):
        """Отправка сообщения всем в игре"""
        if game_id in self.connections:
            disconnected = []
            for connection in self.connections[game_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)

            # Удаляем отключенные соединения
            for conn in disconnected:
                self.disconnect(conn)

    async def send_to_user(self, user_id: str, message: dict):
        """Отправка сообщения конкретному пользователю"""
        if user_id in self.user_connections:
            disconnected = []
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)

            # Удаляем отключенные соединения
            for conn in disconnected:
                self.disconnect(conn)

    async def handle_message(self, websocket: WebSocket, message: str):
        """Обработка входящего сообщения"""
        try:
            data = json.loads(message)
            metadata = self.connection_metadata.get(websocket, {})

            # Добавляем метаданные к сообщению
            data["user_id"] = metadata.get("user_id")
            data["game_id"] = metadata.get("game_id")

            # Публикуем событие в шину
            event_type = data.get("type", "message")
            await event_bus.publish(f"websocket:{event_type}", data)

        except json.JSONDecodeError:
            pass


# Глобальный экземпляр
websocket_manager = WebSocketManager()
