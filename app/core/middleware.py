from datetime import datetime

from fastapi import HTTPException
from jose import jwt, JWTError
from starlette.requests import Request

from app.core.config import settings


async def auth_middleware(request: Request, call_next):
    # Разрешить публичные эндпоинты
    public_paths = ["/health", "/api/auth/telegram"]
    if request.url.path in public_paths:
        return await call_next(request)

    # Проверка аутентификации
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALG],
            options={"require_exp": True}
        )
        # Проверка срока действия
        if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
            raise HTTPException(status_code=401, detail="Token expired")

        request.state.user = payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return await call_next(request)


# app/main.py
async def locale_middleware(request: Request, call_next):
    response = await call_next(request)

    # Установка языка из JWT
    if hasattr(request.state, "user") and request.state.user.get("locale"):
        response.headers["Content-Language"] = request.state.user["locale"]

    return response

