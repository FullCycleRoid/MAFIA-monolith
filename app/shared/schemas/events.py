from typing import Literal, Optional

from pydantic import BaseModel


class GamePhaseChanged(BaseModel):
    event: Literal["game:phase_changed"] = "game:phase_changed"
    game_id: str
    phase: str


class GamePlayerAction(BaseModel):
    event: Literal["game:player_action"] = "game:player_action"
    game_id: str
    player_id: str
    action_type: str
    target_id: Optional[str] = None


class VoiceMutePlayer(BaseModel):
    event: Literal["voice:mute_player"] = "voice:mute_player"
    room_id: str
    player_id: str
    mute: bool


class EconomyTokensAwarded(BaseModel):
    event: Literal["economy:tokens_awarded"] = "economy:tokens_awarded"
    user_id: str
    amount: int
    reason: Optional[str] = None
