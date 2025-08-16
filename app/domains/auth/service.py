from jose import JWTError, jwt
from datetime import timedelta
from fastapi import HTTPException
from .repository import get_user_by_telegram_id, create_user
from app.core.config import settings
from app.shared.utils.security import create_access_token


async def authenticate_telegram_user(telegram_data: dict) -> dict:
    """
    Аутентификация пользователя Telegram
    Возвращает JWT токен при успешной аутентификации
    """
    telegram_id = int(telegram_data.get('id'))
    user = await get_user_by_telegram_id(telegram_id)

    if not user:
        # Создание нового пользователя
        user_data = {
            "telegram_id": telegram_id,
            "first_name": telegram_data.get('first_name', ''),
            "last_name": telegram_data.get('last_name'),
            "username": telegram_data.get('username'),
            "language_code": telegram_data.get('language_code', 'en'),
            "is_bot": telegram_data.get('is_bot', False),
            "allows_write_to_pm": telegram_data.get('allows_write_to_pm', False)
        }
        user = await create_user(user_data)

    # Создание JWT токена
    access_token = create_access_token(
        data={"sub": str(user.telegram_id)},
        expires_delta=timedelta(days=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}


async def validate_token(token: str) -> dict:
    """Валидация JWT токена и получение пользователя"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        telegram_id: str = payload.get("sub")
        if not telegram_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await get_user_by_telegram_id(int(telegram_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")