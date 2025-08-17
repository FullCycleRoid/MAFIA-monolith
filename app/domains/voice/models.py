from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.mixins import TimestampMixin
from app.shared.models.base import Base


class VoiceRoom(Base, TimestampMixin):
    __tablename__ = "voice_rooms"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(String, index=True)


class Participant(Base, TimestampMixin):
    __tablename__ = "voice_participants"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    room_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    muted: Mapped[bool] = mapped_column(Boolean, default=False)
