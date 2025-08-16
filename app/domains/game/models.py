from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.models.base import Base
from app.shared.database.mixins import TimestampMixin


class Game(Base, TimestampMixin):
    __tablename__ = "game_games"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="lobby")


class Player(Base, TimestampMixin):
    __tablename__ = "game_players"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String, default="citizen")
    alive: Mapped[bool] = mapped_column(Boolean, default=True)


class Action(Base, TimestampMixin):
    __tablename__ = "game_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(String, index=True)
    player_id: Mapped[str] = mapped_column(String, index=True)
    action_type: Mapped[str] = mapped_column(String)
    target_id: Mapped[str] = mapped_column(String, nullable=True)
    