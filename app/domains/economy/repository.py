# app/domains/economy/repository.py
"""
Updated repository with TON support and bug fixes
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, desc, func, select, update

from app.core.database import get_db
from app.domains.economy.models import PendingWithdrawal, Transaction, Wallet
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


async def get_wallet(user_id: str) -> Optional[Wallet]:
    """Get user's wallet"""
    async with get_db() as db:
        try:
            result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting wallet for user {user_id}: {e}")
            return None


async def save_wallet(wallet_data: Dict) -> Wallet:
    """Create new wallet"""
    async with get_db() as db:
        try:
            wallet = Wallet(
                id=str(uuid.uuid4()),
                user_id=wallet_data["user_id"],
                ton_address=wallet_data["ton_address"],
                jetton_wallet=wallet_data["jetton_wallet"],
                encrypted_mnemonic=wallet_data["encrypted_mnemonic"],
                balance_offchain=wallet_data.get("balance_offchain", 0),
                balance_onchain=wallet_data.get("balance_onchain", 0.0),
            )
            db.add(wallet)
            await db.commit()
            await db.refresh(wallet)
            return wallet
        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving wallet: {e}")
            raise


async def update_offchain_balance(user_id: str, new_balance: int) -> bool:
    """Update user's off-chain balance"""
    async with get_db() as db:
        try:
            result = await db.execute(
                update(Wallet)
                .where(Wallet.user_id == user_id)
                .values(balance_offchain=new_balance, updated_at=datetime.utcnow())
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating balance: {e}")
            return False


async def update_last_claim(user_id: str, claim_time: datetime) -> bool:
    """Update last claim time and streak"""
    async with get_db() as db:
        try:
            wallet = await get_wallet(user_id)
            if not wallet:
                return False

            # Calculate streak
            streak = wallet.streak_days
            if wallet.last_claim_at:
                time_diff = claim_time - wallet.last_claim_at
                if time_diff.days == 1:
                    streak += 1
                elif time_diff.days > 1:
                    streak = 1
            else:
                streak = 1

            result = await db.execute(
                update(Wallet)
                .where(Wallet.user_id == user_id)
                .values(
                    last_claim_at=claim_time,
                    streak_days=streak,
                    updated_at=datetime.utcnow(),
                )
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating claim: {e}")
            return False


async def save_transaction(transaction_data: Dict) -> Transaction:
    """Save transaction record"""
    async with get_db() as db:
        try:
            transaction = Transaction(
                id=str(uuid.uuid4()),
                user_id=transaction_data["user_id"],
                amount=transaction_data["amount"],
                type=transaction_data["type"],
                reason=transaction_data["reason"],
                is_onchain=transaction_data.get("is_onchain", False),
                tx_hash=transaction_data.get("tx_hash"),
                tx_metadata=transaction_data.get("metadata", {}),  # Changed from 'metadata' to 'tx_metadata'
            )
            db.add(transaction)

            # Update wallet statistics
            wallet = await get_wallet(transaction_data["user_id"])
            if wallet:
                if transaction_data["amount"] > 0:
                    wallet.total_earned += transaction_data["amount"]
                else:
                    wallet.total_spent += abs(transaction_data["amount"])

            await db.commit()
            return transaction
        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving transaction: {e}")
            raise


async def get_user_transactions(user_id: str, limit: int = 50) -> List[Dict]:
    """Get user's recent transactions"""
    async with get_db() as db:
        try:
            result = await db.execute(
                select(Transaction)
                .filter(Transaction.user_id == user_id)
                .order_by(desc(Transaction.created_at))
                .limit(limit)
            )
            transactions = result.scalars().all()

            return [
                {
                    "id": tx.id,
                    "amount": tx.amount,
                    "type": tx.type,
                    "reason": tx.reason,
                    "is_onchain": tx.is_onchain,
                    "tx_hash": tx.tx_hash,
                    "timestamp": tx.created_at.isoformat(),
                    "status": tx.status,
                }
                for tx in transactions
            ]
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []


async def create_pending_withdrawal(user_id: str, amount: int, ton_address: str) -> str:
    """Create pending withdrawal request"""
    async with get_db() as db:
        try:
            withdrawal_id = str(uuid.uuid4())
            withdrawal = PendingWithdrawal(
                id=withdrawal_id,
                user_id=user_id,
                amount=amount,
                ton_address=ton_address,
                status="pending",
            )
            db.add(withdrawal)
            await db.commit()
            return withdrawal_id
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating withdrawal: {e}")
            raise


async def get_pending_withdrawals() -> List[PendingWithdrawal]:
    """Get all pending withdrawals for processing"""
    async with get_db() as db:
        try:
            result = await db.execute(
                select(PendingWithdrawal)
                .filter(
                    and_(
                        PendingWithdrawal.status == "pending",
                        PendingWithdrawal.retry_count < 3,
                    )
                )
                .order_by(PendingWithdrawal.created_at)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting pending withdrawals: {e}")
            return []


async def update_withdrawal_status(
    withdrawal_id: str,
    status: str,
    tx_hash: Optional[str] = None,
    error: Optional[str] = None,
) -> bool:
    """Update withdrawal status"""
    async with get_db() as db:
        try:
            update_data = {"status": status, "updated_at": datetime.utcnow()}

            if tx_hash:
                update_data["tx_hash"] = tx_hash
            if error:
                update_data["error_message"] = error

            result = await db.execute(
                update(PendingWithdrawal)
                .where(PendingWithdrawal.id == withdrawal_id)
                .values(**update_data)
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating withdrawal: {e}")
            return False


async def get_leaderboard(period: str = "all", limit: int = 100) -> List[Dict]:
    """Get token leaderboard"""
    async with get_db() as db:
        try:
            # Base query
            query = (
                select(
                    Wallet.user_id,
                    Wallet.balance_offchain,
                    Wallet.total_earned,
                    func.count(Transaction.id).label("tx_count"),
                )
                .outerjoin(Transaction, Wallet.user_id == Transaction.user_id)
                .group_by(Wallet.user_id, Wallet.balance_offchain, Wallet.total_earned)
            )

            # Apply period filter
            if period == "daily":
                cutoff = datetime.utcnow() - timedelta(days=1)
                query = query.filter(Transaction.created_at >= cutoff)
            elif period == "weekly":
                cutoff = datetime.utcnow() - timedelta(days=7)
                query = query.filter(Transaction.created_at >= cutoff)
            elif period == "monthly":
                cutoff = datetime.utcnow() - timedelta(days=30)
                query = query.filter(Transaction.created_at >= cutoff)

            # Order and limit
            query = query.order_by(desc(Wallet.total_earned)).limit(limit)

            result = await db.execute(query)
            rows = result.all()

            # Get user details
            from app.domains.auth.repository import get_user_by_id

            leaderboard = []

            for idx, row in enumerate(rows, 1):
                user = await get_user_by_id(row.user_id)
                if user:
                    leaderboard.append(
                        {
                            "rank": idx,
                            "user_id": row.user_id,
                            "username": user.username or f"User_{user.telegram_id}",
                            "balance": row.balance_offchain,
                            "total_earned": row.total_earned,
                            "transactions": row.tx_count,
                        }
                    )

            return leaderboard
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []

async def set_premium_status(user_id: str, is_premium: bool) -> bool:
    """Set user's premium status"""
    from app.domains.auth.models import User

    async with get_db() as db:
        try:
            result = await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(is_premium=is_premium, updated_at=datetime.utcnow())
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            await db.rollback()
            logger.error(f"Error setting premium status: {e}")
            return False