# app/core/websocket_manager.py
"""
Enhanced WebSocket Manager with reconnection, heartbeat, and message queue
"""
import asyncio
import json
from typing import Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.event_bus import event_bus
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


class MessagePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class QueuedMessage:
    """Message in queue"""
    message: dict
    priority: MessagePriority
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3


class ConnectionInfo:
    """Information about a WebSocket connection"""

    def __init__(self, websocket: WebSocket, user_id: str, game_id: Optional[str] = None):
        self.websocket = websocket
        self.user_id = user_id
        self.game_id = game_id
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.last_pong = datetime.utcnow()
        self.message_queue: List[QueuedMessage] = []
        self.is_alive = True
        self.reconnect_token: Optional[str] = None

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_pong = datetime.utcnow()
        self.is_alive = True


class WebSocketManager:
    """Enhanced WebSocket manager with reliability features"""

    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, List[WebSocket]] = {}
        self.connection_info: Dict[WebSocket, ConnectionInfo] = {}
        self.reconnect_tokens: Dict[str, ConnectionInfo] = {}
        self.message_buffer: Dict[str, List[QueuedMessage]] = defaultdict(list)

        # Configuration
        self.ping_interval = 30
        self.pong_timeout = 10
        self.reconnect_timeout = 60
        self.max_message_size = 65536
        self.max_queue_size = 100

        # <-- НОВОЕ: больше НЕ стартуем фоновые задачи в __init__
        self._tasks: list[asyncio.Task] = []
        self._started: bool = False

    async def start(self):
        """Start background maintenance tasks (must be called inside a running event loop)"""
        if self._started:
            return
        loop = asyncio.get_running_loop()
        self._tasks = [
            loop.create_task(self._heartbeat_loop(), name="ws-heartbeat"),
            loop.create_task(self._cleanup_loop(), name="ws-cleanup"),
            loop.create_task(self._process_queues_loop(), name="ws-queues"),
        ]
        self._started = True
        logger.info("WebSocketManager background tasks started")

    async def stop(self):
        """Stop background tasks gracefully"""
        if not self._started:
            return
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._started = False
        logger.info("WebSocketManager background tasks stopped")

    async def connect(
            self,
            websocket: WebSocket,
            user_id: str,
            game_id: Optional[str] = None,
            reconnect_token: Optional[str] = None
    ) -> Dict:
        """Connect client with optional reconnection"""
        try:
            await websocket.accept()

            # Check for reconnection
            old_messages = []
            if reconnect_token and reconnect_token in self.reconnect_tokens:
                old_info = self.reconnect_tokens[reconnect_token]
                old_messages = old_info.message_queue
                del self.reconnect_tokens[reconnect_token]
                logger.info(f"User {user_id} reconnected with {len(old_messages)} queued messages")

            # Create connection info
            info = ConnectionInfo(websocket, user_id, game_id)
            info.message_queue = old_messages

            # Generate new reconnect token
            import uuid
            info.reconnect_token = str(uuid.uuid4())

            # Store connection
            self.connection_info[websocket] = info

            # Add to game connections
            if game_id:
                if game_id not in self.connections:
                    self.connections[game_id] = []
                self.connections[game_id].append(websocket)

            # Add to user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

            # Send connection confirmation
            await self._send_direct(websocket, {
                "type": "connected",
                "reconnect_token": info.reconnect_token,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Send any buffered messages
            if user_id in self.message_buffer:
                for msg in self.message_buffer[user_id]:
                    await self._send_direct(websocket, msg.message)
                self.message_buffer[user_id].clear()

            # Send queued messages from reconnection
            for msg in old_messages:
                await self._send_direct(websocket, msg.message)

            logger.info(f"WebSocket connected: user={user_id}, game={game_id}")

            return {
                "status": "connected",
                "reconnect_token": info.reconnect_token
            }

        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    def disconnect(self, websocket: WebSocket, allow_reconnect: bool = True):
        """Disconnect client with optional reconnection support"""
        info = self.connection_info.get(websocket)
        if not info:
            return

        # Store for potential reconnection
        if allow_reconnect and info.reconnect_token and self._started:
            try:
                asyncio.get_running_loop().create_task(
                    self._schedule_reconnect_cleanup(info.reconnect_token)
                )
            except RuntimeError:
                # нет активного лупа — значит мы не в ASGI-рантайме; просто пропускаем
                pass

        # Remove from game connections
        if info.game_id and info.game_id in self.connections:
            if websocket in self.connections[info.game_id]:
                self.connections[info.game_id].remove(websocket)
            if not self.connections[info.game_id]:
                del self.connections[info.game_id]

        # Remove from user connections
        if info.user_id and info.user_id in self.user_connections:
            if websocket in self.user_connections[info.user_id]:
                self.user_connections[info.user_id].remove(websocket)
            if not self.user_connections[info.user_id]:
                del self.user_connections[info.user_id]

        # Clean up connection info
        del self.connection_info[websocket]

        logger.info(f"WebSocket disconnected: user={info.user_id}, game={info.game_id}")

    async def broadcast(
            self,
            game_id: str,
            message: dict,
            exclude: Optional[Set[str]] = None,
            priority: MessagePriority = MessagePriority.NORMAL
    ):
        """Broadcast message to all clients in a game"""
        if game_id not in self.connections:
            return

        disconnected = []
        tasks = []

        for connection in self.connections[game_id]:
            info = self.connection_info.get(connection)
            if info and (not exclude or info.user_id not in exclude):
                if connection.client_state == WebSocketState.CONNECTED:
                    tasks.append(self._send_with_retry(connection, message, priority))
                else:
                    disconnected.append(connection)

        # Send messages concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Broadcast error: {result}")
                    disconnected.append(self.connections[game_id][i])

        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

    async def send_to_user(
            self,
            user_id: str,
            message: dict,
            priority: MessagePriority = MessagePriority.NORMAL
    ):
        """Send message to specific user"""
        if user_id not in self.user_connections:
            # Buffer message for when user connects
            if len(self.message_buffer[user_id]) < self.max_queue_size:
                self.message_buffer[user_id].append(
                    QueuedMessage(message, priority, datetime.utcnow())
                )
            return

        disconnected = []
        sent = False

        for connection in self.user_connections[user_id]:
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await self._send_with_retry(connection, message, priority)
                    sent = True
                    break  # Send to first available connection
                except Exception as e:
                    logger.error(f"Send to user error: {e}")
                    disconnected.append(connection)
            else:
                disconnected.append(connection)

        # If not sent, buffer the message
        if not sent and len(self.message_buffer[user_id]) < self.max_queue_size:
            self.message_buffer[user_id].append(
                QueuedMessage(message, priority, datetime.utcnow())
            )

        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

    async def handle_message(self, websocket: WebSocket, message: str):
        """Handle incoming message from client"""
        try:
            # Check message size
            if len(message) > self.max_message_size:
                await self._send_direct(websocket, {
                    "type": "error",
                    "error": "Message too large"
                })
                return

            data = json.loads(message)
            info = self.connection_info.get(websocket)

            if not info:
                return

            # Handle special message types
            if data.get("type") == "ping":
                await self._handle_ping(websocket)
                return
            elif data.get("type") == "pong":
                info.update_activity()
                return

            # Add metadata to message
            data["user_id"] = info.user_id
            data["game_id"] = info.game_id
            data["timestamp"] = datetime.utcnow().isoformat()

            # Publish to event bus
            event_type = data.get("type", "message")
            await event_bus.publish(f"websocket:{event_type}", data)

        except json.JSONDecodeError:
            await self._send_direct(websocket, {
                "type": "error",
                "error": "Invalid JSON"
            })
        except Exception as e:
            logger.error(f"Message handling error: {e}")

    async def _send_direct(self, websocket: WebSocket, message: dict) -> bool:
        """Send message directly to websocket"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
                return True
        except Exception as e:
            logger.debug(f"Direct send failed: {e}")
        return False

    async def _send_with_retry(
            self,
            websocket: WebSocket,
            message: dict,
            priority: MessagePriority
    ) -> bool:
        """Send message with retry logic"""
        info = self.connection_info.get(websocket)
        if not info:
            return False

        # Try direct send first
        if await self._send_direct(websocket, message):
            return True

        # Queue for retry if high priority
        if priority >= MessagePriority.HIGH:
            if len(info.message_queue) < self.max_queue_size:
                info.message_queue.append(
                    QueuedMessage(message, priority, datetime.utcnow())
                )

        return False

    async def _handle_ping(self, websocket: WebSocket):
        """Handle ping message"""
        info = self.connection_info.get(websocket)
        if info:
            info.last_ping = datetime.utcnow()
            await self._send_direct(websocket, {"type": "pong"})

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to all connections"""
        while True:
            try:
                await asyncio.sleep(self.ping_interval)

                for websocket, info in list(self.connection_info.items()):
                    if websocket.client_state == WebSocketState.CONNECTED:
                        # Check if connection is stale
                        if (datetime.utcnow() - info.last_pong).total_seconds() > self.pong_timeout * 2:
                            logger.warning(f"Connection stale for user {info.user_id}")
                            self.disconnect(websocket)
                            continue

                        # Send ping
                        await self._send_direct(websocket, {"type": "ping"})
                        info.last_ping = datetime.utcnow()

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _cleanup_loop(self):
        """Clean up old connections and buffers"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute

                now = datetime.utcnow()

                # Clean old reconnect tokens
                old_tokens = []
                for token, info in self.reconnect_tokens.items():
                    if (now - info.connected_at).total_seconds() > self.reconnect_timeout:
                        old_tokens.append(token)

                for token in old_tokens:
                    del self.reconnect_tokens[token]

                # Clean old message buffers
                for user_id in list(self.message_buffer.keys()):
                    # Remove messages older than 5 minutes
                    self.message_buffer[user_id] = [
                        msg for msg in self.message_buffer[user_id]
                        if (now - msg.timestamp).total_seconds() < 300
                    ]

                    # Remove empty buffers
                    if not self.message_buffer[user_id]:
                        del self.message_buffer[user_id]

                # Check for zombie connections
                for websocket in list(self.connection_info.keys()):
                    if websocket.client_state != WebSocketState.CONNECTED:
                        self.disconnect(websocket)

            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _process_queues_loop(self):
        """Process message queues for all connections"""
        while True:
            try:
                await asyncio.sleep(1)  # Process every second

                for websocket, info in list(self.connection_info.items()):
                    if not info.message_queue:
                        continue

                    if websocket.client_state != WebSocketState.CONNECTED:
                        continue

                    # Sort by priority and timestamp
                    info.message_queue.sort(
                        key=lambda x: (-x.priority.value, x.timestamp)
                    )

                    # Try to send queued messages
                    sent = []
                    for msg in info.message_queue[:10]:  # Process up to 10 messages
                        if await self._send_direct(websocket, msg.message):
                            sent.append(msg)
                        else:
                            msg.retry_count += 1
                            if msg.retry_count >= msg.max_retries:
                                sent.append(msg)  # Give up after max retries

                    # Remove sent messages
                    for msg in sent:
                        info.message_queue.remove(msg)

            except Exception as e:
                logger.error(f"Queue processing error: {e}")

    async def _schedule_reconnect_cleanup(self, token: str):
        """Schedule cleanup of reconnect token after timeout"""
        await asyncio.sleep(self.reconnect_timeout)
        if token in self.reconnect_tokens:
            del self.reconnect_tokens[token]

    def get_connection_stats(self) -> Dict:
        """Get statistics about current connections"""
        return {
            "total_connections": len(self.connection_info),
            "game_connections": sum(len(conns) for conns in self.connections.values()),
            "user_connections": sum(len(conns) for conns in self.user_connections.values()),
            "reconnect_tokens": len(self.reconnect_tokens),
            "buffered_messages": sum(len(msgs) for msgs in self.message_buffer.values()),
            "active_games": len(self.connections),
            "active_users": len(self.user_connections)
        }

    async def close_all(self):
        """Close all connections gracefully"""
        for websocket in list(self.connection_info.keys()):
            try:
                await websocket.close()
            except:
                pass
            self.disconnect(websocket, allow_reconnect=False)


# Global instance
websocket_manager = WebSocketManager()