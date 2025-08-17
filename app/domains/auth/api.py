from fastapi import APIRouter, HTTPException

from ...core.config import settings
from .schemas import TelegramAuthData
from .service import authenticate_telegram_user
from .telegram_auth import verify_telegram_auth

router = APIRouter()


@router.post("/telegram")
async def telegram_auth(auth_data: TelegramAuthData):
    """
    Аутентификация через Telegram WebApp
    """
    # Валидация данных Telegram
    if not verify_telegram_auth(auth_data.dict(), settings.TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")

    return await authenticate_telegram_user(auth_data.dict())
