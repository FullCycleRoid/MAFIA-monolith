from decimal import Decimal

from app.core.celery import celery_app
from app.core.config import settings
from app.domains.economy.ton_service import ton_service
from app.domains.economy.repository import (
    get_pending_withdrawals,
    update_withdrawal_status,
)


@celery_app.task(bind=True, max_retries=3)
def process_pending_withdrawals(self):
    """Process pending withdrawal requests"""
    import asyncio

    async def process():
        withdrawals = await get_pending_withdrawals()

        for withdrawal in withdrawals:
            try:
                tx_hash = await ton_service.transfer_jettons(
                    from_mnemonic=settings.SERVICE_WALLET_MNEMONIC,
                    to_address=withdrawal.ton_address,
                    amount=Decimal(withdrawal.amount),
                    memo=f"Withdrawal {withdrawal.id}",
                )

                await update_withdrawal_status(
                    withdrawal.id, "completed", tx_hash=tx_hash
                )

            except Exception as e:
                await update_withdrawal_status(withdrawal.id, "failed", error=str(e))

                # Retry
                raise self.retry(exc=e, countdown=60)

    asyncio.run(process())
