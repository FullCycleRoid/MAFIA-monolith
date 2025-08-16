# app/domains/economy/repository.py
import uuid
from typing import Optional, Dict
from sqlalchemy import select, update
from app.core.database import get_db
from app.domains.economy.models import Wallet, Transaction


async def get_wallet(user_id: str) -> Optional[Wallet]:
    """Получение кошелька пользователя"""
    async with get_db() as db:
        result = await db.execute(
            select(Wallet).filter(Wallet.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def save_wallet(wallet_data: Dict) -> Wallet:
    """Создание нового кошелька"""
    async with get_db() as db:
        wallet = Wallet(
            id=str(uuid.uuid4()),
            user_id=wallet_data['user_id'],
            address=wallet_data.get('address', ''),
            encrypted_key=wallet_data.get('encrypted_key', ''),
            balance_cache=wallet_data.get('balance_cache', 0)
        )
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        return wallet


async def update_balance(user_id: str, new_balance: int) -> bool:
    """Обновление баланса кошелька"""
    async with get_db() as db:
        result = await db.execute(
            update(Wallet)
            .where(Wallet.user_id == user_id)
            .values(balance_cache=new_balance)
        )
        await db.commit()
        return result.rowcount > 0


async def save_transaction(transaction_data: Dict) -> Transaction:
    """Сохранение транзакции"""
    async with get_db() as db:
        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=transaction_data['user_id'],
            amount=transaction_data['amount'],
            type=transaction_data['type'],
            reason=transaction_data['reason']
        )
        db.add(transaction)
        await db.commit()
        return transaction


async def save_blockchain_tx(user_id: str, tx_hash: str, amount: int):
    """Сохранение хэша блокчейн транзакции"""
    async with get_db() as db:
        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            amount=amount,
            type="blockchain",
            reason=f"tx:{tx_hash}"
        )
        db.add(transaction)
        await db.commit()
