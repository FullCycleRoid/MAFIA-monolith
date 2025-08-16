# app / domains / social / models.py
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.models.base import Base
from app.shared.database.mixins import TimestampMixin


class SocialInteractionRecord(Base, TimestampMixin):
    __tablename__ = "social_interactions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    from_user: Mapped[str] = mapped_column(String, index=True)
    to_user: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)  # like, gift, report, etc
    game_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime)
    data: Mapped[dict] = mapped_column(JSON)


class UserStats(Base, TimestampMixin):
    __tablename__ = "social_user_stats"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    likes_received: Mapped[int] = mapped_column(Integer, default=0)
    likes_given: Mapped[int] = mapped_column(Integer, default=0)
    gifts_received: Mapped[int] = mapped_column(Integer, default=0)
    gifts_sent: Mapped[int] = mapped_column(Integer, default=0)
    reports_received: Mapped[int] = mapped_column(Integer, default=0)
    reports_sent: Mapped[int] = mapped_column(Integer, default=0)
    friends_count: Mapped[int] = mapped_column(Integer, default=0)
    linguistic_ratings: Mapped[dict] = mapped_column(JSON, default={})


class Friendship(Base, TimestampMixin):
    __tablename__ = "social_friendships"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    friend_id: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String)  # pending, accepted, blocked
    initiated_by: Mapped[str] = mapped_column(String)
