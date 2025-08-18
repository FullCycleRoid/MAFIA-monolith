# app/domains/economy/models.py
"""
Updated database models for TON-based economy
"""
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.mixins import TimestampMixin
from app.shared.models.base import Base


class Wallet(Base, TimestampMixin):
    __tablename__ = "economy_wallets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True)

    # TON blockchain fields
    ton_address: Mapped[str] = mapped_column(String, unique=True)
    jetton_wallet: Mapped[str] = mapped_column(String, unique=True)
    encrypted_mnemonic: Mapped[str] = mapped_column(Text)

    # Balance tracking
    balance_offchain: Mapped[int] = mapped_column(Integer, default=0)
    balance_onchain: Mapped[float] = mapped_column(Float, default=0.0)

    # Statistics
    total_earned: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[int] = mapped_column(Integer, default=0)
    total_withdrawn: Mapped[int] = mapped_column(Integer, default=0)

    # Claim tracking
    last_claim_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)

    # Security
    withdrawal_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    require_2fa: Mapped[bool] = mapped_column(Boolean, default=False)


class Transaction(Base, TimestampMixin):
    __tablename__ = "economy_transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)

    # Transaction details
    amount: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String)  # credit, debit, withdrawal, mint, etc
    reason: Mapped[str] = mapped_column(String)

    # Blockchain integration
    is_onchain: Mapped[bool] = mapped_column(Boolean, default=False)
    tx_hash: Mapped[str] = mapped_column(String, nullable=True, index=True)
    block_number: Mapped[int] = mapped_column(Integer, nullable=True)
    confirmations: Mapped[int] = mapped_column(Integer, default=0)

    # Additional metadata - renamed from 'metadata' to avoid SQLAlchemy reserved word
    tx_metadata: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="completed")


class PendingWithdrawal(Base, TimestampMixin):
    __tablename__ = "economy_pending_withdrawals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    ton_address: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    tx_hash: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


class TokenPrice(Base, TimestampMixin):
    __tablename__ = "economy_token_prices"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    price_usd: Mapped[float] = mapped_column(Float)
    price_ton: Mapped[float] = mapped_column(Float)
    volume_24h: Mapped[float] = mapped_column(Float)
    market_cap: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[DateTime] = mapped_column(DateTime)
