from decimal import Decimal
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, validator

from app.shared.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Request/Response Models
class CreateWalletResponse(BaseModel):
    ton_address: str
    jetton_wallet: str
    balance_offchain: int
    balance_onchain: float


class BalanceResponse(BaseModel):
    offchain: int
    onchain: float
    total: float
    ton_balance: float


class WithdrawRequest(BaseModel):
    amount: int = Field(gt=0)

    @validator("amount")
    def validate_amount(cls, v):
        from app.core.config import settings

        if v < settings.MIN_WITHDRAWAL_AMOUNT:
            raise ValueError(
                f"Minimum withdrawal is {settings.MIN_WITHDRAWAL_AMOUNT} MAFIA"
            )
        if v > settings.MAX_WITHDRAWAL_AMOUNT:
            raise ValueError(
                f"Maximum withdrawal is {settings.MAX_WITHDRAWAL_AMOUNT} MAFIA"
            )
        return v


class PurchaseRequest(BaseModel):
    item_type: str  # skin, language, premium, boost
    item_id: str
    price: int = Field(gt=0)


class SendGiftRequest(BaseModel):
    to_user: str
    amount: int = Field(gt=0, le=10000)
    message: Optional[str] = None


class TransferRequest(BaseModel):
    to_address: str
    amount: int = Field(gt=0)
    memo: Optional[str] = None
