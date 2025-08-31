from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from asgiref.sync import async_to_sync
from sqlalchemy import insert

from app.core.celery import celery_app
from app.core.database import get_db
from app.core.config import settings
from app.domains.economy.models import TokenPrice

async def _update_price_async():
    price_usd = float(settings.MAFIA_PRICE_USD)
    ton_usd = float(settings.TON_PRICE_USD) if settings.TON_PRICE_USD else None
    price_ton = (price_usd / ton_usd) if ton_usd else 0.0
    volume_24h = 0.0
    market_cap = 0.0
    async with get_db() as db:
        stmt = insert(TokenPrice).values(
            id=str(uuid4()),
            price_usd=price_usd,
            price_ton=price_ton,
            volume_24h=volume_24h,
            market_cap=market_cap,
            timestamp=datetime.now(timezone.utc)
        )
        await db.execute(stmt)

@celery_app.task
def update_token_price():
    async_to_sync(_update_price_async)()
