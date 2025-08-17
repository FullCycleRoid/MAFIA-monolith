# app/domains/auth/models.py
from sqlalchemy import (JSON, BigInteger, Boolean, DateTime, Float, Integer,
                        String)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.mixins import TimestampMixin
from app.shared.models.base import Base


class User(Base, TimestampMixin):
    __tablename__ = "auth_users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    language_code: Mapped[str] = mapped_column(String, default="en")
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    allows_write_to_pm: Mapped[bool] = mapped_column(Boolean, default=False)

    # Новые поля для матчмейкинга и социальных функций
    rating: Mapped[int] = mapped_column(Integer, default=1000)
    country: Mapped[str] = mapped_column(String, default="US")
    spoken_languages: Mapped[list] = mapped_column(JSON, default=list)
    purchased_languages: Mapped[list] = mapped_column(JSON, default=list)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    games_won: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    linguistic_rating: Mapped[dict] = mapped_column(JSON, default=dict)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    skin_id: Mapped[str] = mapped_column(String, nullable=True)
    banned_until: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    muted_players: Mapped[list] = mapped_column(JSON, default=list)
    referrer_id: Mapped[str] = mapped_column(String, nullable=True)
    referral_code: Mapped[str] = mapped_column(String, unique=True, nullable=True)
