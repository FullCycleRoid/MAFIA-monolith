from sqlalchemy import String, Integer, JSON,  DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.models.base import Base
from app.shared.database.mixins import TimestampMixin


class Wallet(Base, TimestampMixin):
    __tablename__ = "economy_wallets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    address: Mapped[str] = mapped_column(String, nullable=True)
    encrypted_key: Mapped[str] = mapped_column(String, nullable=True)
    balance_cache: Mapped[int] = mapped_column(Integer, default=0)

    # Дополнительные поля
    total_earned: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[int] = mapped_column(Integer, default=0)
    last_claim_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)


class Transaction(Base, TimestampMixin):
    __tablename__ = "economy_transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String)  # credit, debit, blockchain
    reason: Mapped[str] = mapped_column(String)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=True)
