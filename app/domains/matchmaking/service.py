# app/domains/matchmaking/service.py
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from app.domains.matchmaking.entities import (
    FormingLobby,
    LobbySettings,
    MatchmakingCriteria,
    MatchmakingMode,
    QueuePlayer,
)


class MatchmakingQueue:
    def __init__(self):
        self.queues: Dict[MatchmakingMode, List[QueuePlayer]] = {
            mode: [] for mode in MatchmakingMode
        }
        self.player_to_queue: Dict[str, MatchmakingMode] = {}
        self.forming_lobbies: List[FormingLobby] = []

    async def add_player(self, player: QueuePlayer) -> str:
        """Добавление игрока в очередь"""
        # Проверка бана
        if (
            player.profile.banned_until
            and player.profile.banned_until > datetime.utcnow()
        ):
            raise ValueError(f"Player banned until {player.profile.banned_until}")

        # Удаляем из предыдущей очереди если есть
        if player.profile.user_id in self.player_to_queue:
            await self.remove_player(player.profile.user_id)

        # Добавляем в новую очередь
        mode_queue = self.queues[player.mode]
        mode_queue.append(player)
        self.player_to_queue[player.profile.user_id] = player.mode

        # Пытаемся сформировать матч
        lobby = await self._try_form_match(player.mode)
        if lobby:
            return lobby.lobby_id

        return "queued"

    async def remove_player(self, user_id: str) -> bool:
        """Удаление игрока из очереди"""
        if user_id not in self.player_to_queue:
            return False

        mode = self.player_to_queue[user_id]
        self.queues[mode] = [
            p for p in self.queues[mode] if p.profile.user_id != user_id
        ]
        del self.player_to_queue[user_id]
        return True

    async def _try_form_match(self, mode: MatchmakingMode) -> Optional["FormingLobby"]:
        """Попытка сформировать матч"""
        queue = self.queues[mode]

        if mode == MatchmakingMode.FRIENDS:
            return await self._form_friends_match(queue)

        criteria = MatchmakingCriteria()

        # Группируем по языкам
        language_groups = self._group_by_languages(queue)

        for lang, players in language_groups.items():
            if len(players) >= criteria.min_players:
                # Проверяем рейтинг
                compatible_players = self._filter_by_rating(
                    players, criteria.rating_tolerance
                )

                if len(compatible_players) >= criteria.min_players:
                    # Формируем лобби
                    selected = compatible_players[
                        : min(criteria.max_players, len(compatible_players))
                    ]

                    lobby = FormingLobby(
                        lobby_id=self._generate_lobby_id(),
                        mode=mode,
                        players=selected,
                        language=lang,
                        created_at=datetime.utcnow(),
                    )

                    # Удаляем игроков из очереди
                    for player in selected:
                        await self.remove_player(player.profile.user_id)

                    self.forming_lobbies.append(lobby)
                    return lobby

        # Расширяем критерии если долго ждут
        await self._expand_criteria_for_waiting_players(queue, criteria)

        return None

    def _group_by_languages(
        self, players: List[QueuePlayer]
    ) -> Dict[str, List[QueuePlayer]]:
        """Группировка игроков по языкам"""
        groups = defaultdict(list)

        for player in players:
            # Все языки которыми владеет игрок
            all_languages = set([player.profile.native_language])
            all_languages.update(player.profile.spoken_languages)
            all_languages.update(player.profile.purchased_languages)

            # Добавляем в группы по приоритетным языкам
            for lang in player.preferred_languages:
                if lang in all_languages:
                    groups[lang].append(player)
                    break  # Добавляем только в одну группу
            else:
                # Если нет предпочтений, добавляем по родному языку
                groups[player.profile.native_language].append(player)

        return groups

    def _filter_by_rating(
        self, players: List[QueuePlayer], tolerance: int
    ) -> List[QueuePlayer]:
        """Фильтрация по рейтингу"""
        if not players:
            return []

        # Находим медианный рейтинг
        ratings = [p.profile.rating for p in players]
        median_rating = sorted(ratings)[len(ratings) // 2]

        # Фильтруем по допустимому разбросу
        compatible = [
            p for p in players if abs(p.profile.rating - median_rating) <= tolerance
        ]

        return compatible

    async def _form_friends_match(
        self, queue: List[QueuePlayer]
    ) -> Optional["FormingLobby"]:
        """Формирование матча с друзьями"""
        # Группируем по party_id
        parties = defaultdict(list)
        for player in queue:
            if player.party_id:
                parties[player.party_id].append(player)

        # Проверяем готовые группы
        for party_id, players in parties.items():
            if len(players) >= 6:  # Минимум для игры
                lobby = FormingLobby(
                    lobby_id=self._generate_lobby_id(),
                    mode=MatchmakingMode.FRIENDS,
                    players=players[:12],  # Максимум 12
                    language=players[0].preferred_languages[0],
                    created_at=datetime.utcnow(),
                    is_private=True,
                )

                for player in players[:12]:
                    await self.remove_player(player.profile.user_id)

                return lobby

        return None

    async def _expand_criteria_for_waiting_players(
        self, queue: List[QueuePlayer], criteria: MatchmakingCriteria
    ):
        """Расширение критериев для долго ожидающих"""
        now = datetime.utcnow()

        for player in queue:
            wait_time = (now - player.join_time).total_seconds()

            # После 30 секунд расширяем рейтинг
            if wait_time > 30:
                criteria.rating_tolerance = min(500, criteria.rating_tolerance + 100)

            # После 60 секунд игнорируем языковые предпочтения
            if wait_time > 60:
                criteria.language_priority = False

            # После 90 секунд уменьшаем минимум игроков
            if wait_time > 90:
                criteria.min_players = max(4, criteria.min_players - 2)

    def _generate_lobby_id(self) -> str:
        import uuid

        return f"lobby_{uuid.uuid4().hex[:8]}"


class LobbyService:
    def __init__(self, matchmaking_queue: MatchmakingQueue):
        self.queue = matchmaking_queue
        self.active_lobbies: Dict[str, FormingLobby] = {}
        self.lobby_settings: Dict[str, LobbySettings] = {}

    async def create_lobby(self, lobby: FormingLobby) -> Dict:
        """Создание лобби из сформированного матча"""
        self.active_lobbies[lobby.lobby_id] = lobby

        # Настройки по умолчанию
        self.lobby_settings[lobby.lobby_id] = LobbySettings(
            lobby_id=lobby.lobby_id,
            game_mode=lobby.mode,
            language=lobby.language,
            min_rating=min(p.profile.rating for p in lobby.players),
            max_rating=max(p.profile.rating for p in lobby.players),
            allow_spectators=not lobby.is_private,
            voice_quality="high"
            if any(p.profile.is_premium for p in lobby.players)
            else "standard",
        )

        return {
            "lobby_id": lobby.lobby_id,
            "players": [p.profile.user_id for p in lobby.players],
            "settings": self.lobby_settings[lobby.lobby_id].__dict__,
        }

    async def player_ready(self, lobby_id: str, user_id: str) -> bool:
        """Игрок готов начать"""
        if lobby_id not in self.active_lobbies:
            return False

        lobby = self.active_lobbies[lobby_id]
        lobby.mark_ready(user_id)

        if lobby.is_ready():
            # Запускаем игру
            await self._start_game(lobby_id)
            return True

        return False

    async def _start_game(self, lobby_id: str):
        """Запуск игры"""
        lobby = self.active_lobbies[lobby_id]
        settings = self.lobby_settings[lobby_id]

        # Создаем игру через game service
        from app.domains.game import service as game_service

        game_id = await game_service.create_game_from_lobby(
            players=[p.profile for p in lobby.players], settings=settings
        )

        # Создаем голосовую комнату
        from app.domains.voice import service as voice_service

        room_id = await voice_service.create_room(game_id)

        # Уведомляем игроков
        await self._notify_game_started(lobby_id, game_id, room_id)

        # Удаляем лобби
        del self.active_lobbies[lobby_id]
        del self.lobby_settings[lobby_id]

    async def _notify_game_started(self, lobby_id: str, game_id: str, room_id: str):
        """Уведомление о начале игры"""
        from app.core import websocket_manager

        lobby = self.active_lobbies[lobby_id]
        for player in lobby.players:
            await websocket_manager.send_to_user(
                player.profile.user_id,
                {
                    "event": "game_started",
                    "game_id": game_id,
                    "room_id": room_id,
                    "lobby_id": lobby_id,
                },
            )


# Глобальные экземпляры
matchmaking_queue = MatchmakingQueue()
lobby_service = LobbyService(matchmaking_queue)
