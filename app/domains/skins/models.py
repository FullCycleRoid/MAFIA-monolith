# app/domains/skins/models.py
from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.mixins import TimestampMixin
from app.shared.models.base import Base


class SkinCatalog(Base, TimestampMixin):
    __tablename__ = "skins_catalog"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    price_mafia: Mapped[int] = mapped_column(Integer)
    image_url: Mapped[str] = mapped_column(String)
    preview_url: Mapped[str] = mapped_column(String)
    rarity: Mapped[str] = mapped_column(String)  # common, rare, epic, legendary
    is_limited: Mapped[bool] = mapped_column(Boolean, default=False)
    available_until: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    requirements: Mapped[dict] = mapped_column(JSON, nullable=True)


class UserSkin(Base, TimestampMixin):
    __tablename__ = "user_skins"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    skin_id: Mapped[str] = mapped_column(String, index=True)
    purchased_at: Mapped[DateTime] = mapped_column(DateTime)
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)
