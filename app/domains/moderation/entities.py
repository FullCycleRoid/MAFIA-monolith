from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class BanType(str, Enum):
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    SHADOW = "shadow"  # Игрок не знает о бане
    VOICE_ONLY = "voice_only"  # Только голосовой чат
    RANKED_ONLY = "ranked_only"  # Только рейтинговые игры


class BanReason(str, Enum):
    TOXIC_BEHAVIOR = "toxic_behavior"
    HATE_SPEECH = "hate_speech"
    CHEATING = "cheating"
    AFK_ABUSE = "afk_abuse"
    POOR_LANGUAGE = "poor_language"  # Плохое знание языка
    SPAM = "spam"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    ACCOUNT_SHARING = "account_sharing"
    BOOSTING = "boosting"
    BUG_ABUSE = "bug_abuse"


class RestrictionType(str, Enum):
    MUTE_VOICE = "mute_voice"
    MUTE_TEXT = "mute_text"
    NO_GIFTS = "no_gifts"
    NO_RANKED = "no_ranked"
    NO_REWARDS = "no_rewards"
    SLOW_MODE = "slow_mode"  # Может говорить раз в N секунд


@dataclass
class Ban:
    ban_id: str
    user_id: str
    type: BanType
    reason: BanReason
    issued_by: str  # admin_id или "system"
    issued_at: datetime
    expires_at: Optional[datetime]
    evidence: Optional[str]
    appeal_status: str = "none"  # none, pending, approved, rejected
    notes: Optional[str] = None


@dataclass
class Restriction:
    restriction_id: str
    user_id: str
    type: RestrictionType
    expires_at: datetime
    reason: str
    value: Optional[int] = None  # Для slow_mode - секунды между сообщениями


@dataclass
class ModeratorAction:
    action_id: str
    moderator_id: str
    action_type: str  # ban, unban, restrict, warn, etc.
    target_user: str
    timestamp: datetime
    details: Dict


@dataclass
class Warning:
    warning_id: str
    user_id: str
    reason: str
    severity: int  # 1-3, где 3 - самое серьезное
    issued_at: datetime
