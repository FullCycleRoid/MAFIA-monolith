from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.models.base import Base
from app.shared.database.mixins import TimestampMixin


class Wallet(Base, TimestampMixin):
    __tablename__ = "economy_wallets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)


class Transaction(Base, TimestampMixin):
    __tablename__ = "economy_transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String)
    