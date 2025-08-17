from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set


class MatchmakingMode(str, Enum):
    QUICK = "quick"  # Быстрая игра
    RANKED = "ranked"  # Рейтинговая
    FRIENDS = "friends"  # С друзьями
    LINGUISTIC = "linguistic"  # Лингвистическая (для изучения языков)


@dataclass
class LobbySettings:
    lobby_id: str
    game_mode: MatchmakingMode
    language: str
    min_rating: int
    max_rating: int
    allow_spectators: bool = True
    voice_quality: str = "standard"  # standard, high, premium
    custom_rules: Dict = field(default_factory=dict)

    # Игровые настройки
    day_duration: int = 180  # секунд
    night_duration: int = 60
    voting_duration: int = 60
    enable_prostitute: bool = True
    enable_detective: bool = True
    mafia_can_kill_mafia: bool = False


@dataclass
class PlayerProfile:
    user_id: str
    telegram_id: int
    username: str
    rating: int = 1000
    country: str = "US"
    native_language: str = "en"
    spoken_languages: List[str] = field(default_factory=list)
    purchased_languages: List[str] = field(default_factory=list)  # Купленные языки
    games_played: int = 0
    win_rate: float = 0.0
    linguistic_rating: Dict[str, float] = field(
        default_factory=dict
    )  # Оценка по языкам
    is_premium: bool = False
    skin_id: Optional[str] = None
    banned_until: Optional[datetime] = None
    muted_players: Set[str] = field(default_factory=set)


@dataclass
class QueuePlayer:
    profile: PlayerProfile
    mode: MatchmakingMode
    preferred_languages: List[str]
    join_time: datetime
    invite_code: Optional[str] = None
    party_id: Optional[str] = None  # Для игры с друзьями


@dataclass
class MatchmakingCriteria:
    min_players: int = 6
    max_players: int = 12
    rating_tolerance: int = 200  # +/- разброс рейтинга
    max_wait_time: int = 120  # секунд
    language_priority: bool = True
    country_priority: bool = False


@dataclass
class FormingLobby:
    lobby_id: str
    mode: MatchmakingMode
    players: List[QueuePlayer]
    language: str
    created_at: datetime
    is_private: bool = False
    ready_players: Set[str] = field(default_factory=set)

    def is_ready(self) -> bool:
        """Все ли игроки готовы"""
        return len(self.ready_players) == len(self.players)

    def mark_ready(self, user_id: str):
        """Отметить игрока готовым"""
        self.ready_players.add(user_id)
