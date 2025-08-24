# app/domains/game/models.py
from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.mixins import TimestampMixin
from app.shared.models.base import Base


class Game(Base, TimestampMixin):
    __tablename__ = "game_games"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="lobby")
    settings: Mapped[dict] = mapped_column(JSON, nullable=True)
    phase: Mapped[str] = mapped_column(String, default="lobby")
    day_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    winner_team: Mapped[str] = mapped_column(String, nullable=True)  # mafia, citizens
    main_winner_team: Mapped[str] = mapped_column(String, nullable=True)  # mafia, citizens


class Player(Base, TimestampMixin):
    __tablename__ = "game_players"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String, default="citizen")
    alive: Mapped[bool] = mapped_column(Boolean, default=True)
    death_reason: Mapped[str] = mapped_column(String, nullable=True)
    death_day: Mapped[int] = mapped_column(Integer, nullable=True)
    kicked_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)  # kills, heals, etc


class Action(Base, TimestampMixin):
    __tablename__ = "game_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(String, index=True)
    player_id: Mapped[str] = mapped_column(String, index=True)
    action_type: Mapped[str] = mapped_column(String)
    target_id: Mapped[str] = mapped_column(String, nullable=True)
    phase: Mapped[str] = mapped_column(String)
    day: Mapped[int] = mapped_column(Integer)
    result: Mapped[str] = mapped_column(String, nullable=True)


class GameStats(Base, TimestampMixin):
    __tablename__ = "game_stats"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    total_players: Mapped[int] = mapped_column(Integer)
    mafia_count: Mapped[int] = mapped_column(Integer)
    mvp_player_id: Mapped[str] = mapped_column(String, nullable=True)
    most_active_player_id: Mapped[str] = mapped_column(String, nullable=True)
    stats: Mapped[dict] = mapped_column(JSON)  # Детальная статистика
