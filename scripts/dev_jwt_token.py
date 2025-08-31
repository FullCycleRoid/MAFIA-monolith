# scripts/dev_issue_token.py
import asyncio
from datetime import timedelta
from app.shared.utils.security import create_access_token

async def main():
    telegram_id = 123456789  # любой тестовый ID
    token = create_access_token({"sub": str(telegram_id)}, timedelta(days=30))
    print(token)

asyncio.run(main())