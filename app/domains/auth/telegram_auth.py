# app/domains/auth/telegram_auth.py
import hashlib
import hmac
from datetime import datetime


def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    # Проверка срока действия данных (не старше 1 дня)
    auth_date = data.get("auth_date")
    if "auth_date" not in data or datetime.now().timestamp() - int(auth_date) > 86400:
        return False

    # Проверка хеша
    check_hash = data.pop("hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_hash, check_hash)
