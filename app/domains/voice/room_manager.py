import asyncio

import httpx

from app.core.config import settings
from app.shared.schemas.events import VoiceMutePlayer
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


class RoomManager:
    def __init__(self):
        self.rooms = {}  # game_id: room_id

    async def create_room(self, game_id: str) -> str:
        if game_id in self.rooms:
            return self.rooms[game_id]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.MEDIASOUP_URL}/room", json={"game_id": game_id}
                )
                response.raise_for_status()
                room_id = response.json()["room_id"]
                self.rooms[game_id] = room_id
                return room_id
        except Exception as e:
            logger.error(f"Room creation failed: {e}")
            raise

    async def apply_command(self, command: VoiceMutePlayer):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.MEDIASOUP_URL}/command", json=command.dict()
                )
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Command failed: {command} - {e}")

    # app/domains/voice/room_manager.py
    async def apply_commands(self, commands: list[VoiceMutePlayer]):
        try:
            async with httpx.AsyncClient(
                timeout=5.0, limits=httpx.Limits(max_connections=50)
            ) as client:
                # Группировка команд по комнатам
                commands_by_room = {}
                for cmd in commands:
                    if cmd.room_id not in commands_by_room:
                        commands_by_room[cmd.room_id] = []
                    commands_by_room[cmd.room_id].append(cmd.dict())

                # Параллельная отправка команд
                tasks = []
                for room_id, room_commands in commands_by_room.items():
                    tasks.append(
                        client.post(
                            f"{settings.MEDIASOUP_URL}/batch-command",
                            json={"room_id": room_id, "commands": room_commands},
                        )
                    )

                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for response in responses:
                    if isinstance(response, Exception):
                        logger.error(f"Command failed: {str(response)}")
                    elif response.status_code != 200:
                        logger.error(f"Command failed: {response.text}")
        except Exception as e:
            logger.error(f"Batch command failed: {e}")

    def get_room_id(self, game_id: str) -> str | None:
        return self.rooms.get(game_id)


room_manager = RoomManager()
