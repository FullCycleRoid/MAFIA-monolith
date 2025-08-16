from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.models.base import Base
from app.shared.database.mixins import TimestampMixin

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