from typing import Optional

from pydantic import BaseModel


class SendGiftRequest(BaseModel):
    to_user: str
    gift_type: str
    game_id: Optional[str] = None


class RateLinguisticRequest(BaseModel):
    rated_user: str
    language: str
    score: int  # 1-5
    game_id: str


class ReportPlayerRequest(BaseModel):
    reported_user: str
    reason: str
    game_id: str
    evidence: Optional[str] = None
