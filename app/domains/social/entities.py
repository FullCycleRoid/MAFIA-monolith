from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict


class InteractionType(str, Enum):
    LIKE = "like"
    GIFT = "gift"
    LINGUISTIC_RATE = "linguistic_rate"
    REPORT = "report"
    MUTE = "mute"
    FRIEND_REQUEST = "friend_request"


class GiftType(str, Enum):
    ROSE = "rose"  # 10 MAFIA
    CHAMPAGNE = "champagne"  # 50 MAFIA
    DIAMOND = "diamond"  # 100 MAFIA
    CROWN = "crown"  # 500 MAFIA
    EXCLUSIVE = "exclusive"  # 1000+ MAFIA


@dataclass
class Gift:
    gift_id: str
    type: GiftType
    price_mafia: int
    icon_url: str
    animation_url: Optional[str]
    is_limited: bool = False
    available_until: Optional[datetime] = None


@dataclass
class SocialInteraction:
    interaction_id: str
    from_user: str
    to_user: str
    type: InteractionType
    game_id: Optional[str]
    timestamp: datetime
    data: Dict  # Дополнительные данные (gift_type, rating, report_reason и т.д.)


@dataclass
class UserSocialStats:
    user_id: str
    likes_received: int = 0
    likes_given: int = 0
    gifts_received: int = 0
    gifts_sent: int = 0
    reports_received: int = 0
    reports_sent: int = 0
    friends_count: int = 0
    linguistic_ratings: Dict[str, float] = None

    def __post_init__(self):
        if self.linguistic_ratings is None:
            self.linguistic_ratings = {}

