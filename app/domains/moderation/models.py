# app/domains/moderation/models.py
from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.mixins import TimestampMixin
from app.shared.models.base import Base


class BanRecord(Base, TimestampMixin):
    __tablename__ = "moderation_bans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)  # temporary, permanent, shadow, etc
    reason: Mapped[str] = mapped_column(String)
    issued_by: Mapped[str] = mapped_column(String)
    issued_at: Mapped[DateTime] = mapped_column(DateTime)
    expires_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    evidence: Mapped[str] = mapped_column(Text, nullable=True)
    appeal_status: Mapped[str] = mapped_column(String, default="none")
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class RestrictionRecord(Base, TimestampMixin):
    __tablename__ = "moderation_restrictions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)
    expires_at: Mapped[DateTime] = mapped_column(DateTime)
    reason: Mapped[str] = mapped_column(String)
    value: Mapped[int] = mapped_column(Integer, nullable=True)


class ModeratorActionRecord(Base, TimestampMixin):
    __tablename__ = "moderation_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    moderator_id: Mapped[str] = mapped_column(String, index=True)
    action_type: Mapped[str] = mapped_column(String)
    target_user: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime)
    details: Mapped[dict] = mapped_column(JSON)


class WarningRecord(Base, TimestampMixin):
    __tablename__ = "moderation_warnings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    reason: Mapped[str] = mapped_column(String)
    severity: Mapped[int] = mapped_column(Integer)
    issued_at: Mapped[DateTime] = mapped_column(DateTime)
    issued_by: Mapped[str] = mapped_column(String)
