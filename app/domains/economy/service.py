# app/domains/economy/service.py
"""
Updated Economy Service with TON Jetton integration
Manages in-game economy and blockchain operations
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from app.domains.economy.ton_service import ton_service
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


class EconomyService:
    """Main economy service handling both off-chain and on-chain operations"""

    def __init__(self):
        self.ton = ton_service
        self.exchange_rate = Decimal("0.001")  # 1 MAFIA = $0.001 USD
        self.min_withdrawal = 100  # Minimum tokens for on-chain withdrawal
        self.rewards_config = {
            "welcome_bonus": 100,
            "referral_reward": 50,
            "referred_bonus": 25,
            "game_base_reward": 10,
            "win_bonus": 20,
            "mvp_bonus": 15,
            "linguistic_bonus": 5,
            "daily_claim": 10,
        }

    async def initialize(self):
        """Initialize economy service and TON connection"""
        await self.ton.initialize()
        logger.info("Economy service initialized")

    async def create_wallet(self, user_id: str) -> Dict:
        """Create both off-chain account and TON wallet for user"""
        try:
            # Create TON wallet
            ton_wallet = await self.ton.create_user_wallet(user_id)

            # Save wallet info to database
            from app.domains.economy.repository import save_wallet

            wallet_data = {
                "user_id": user_id,
                "ton_address": ton_wallet["address"],
                "jetton_wallet": ton_wallet["jetton_wallet"],
                "encrypted_mnemonic": ton_wallet["encrypted_mnemonic"],
                "balance_offchain": self.rewards_config["welcome_bonus"],
                "balance_onchain": 0,
                "created_at": datetime.utcnow(),
            }

            await save_wallet(wallet_data)

            # Log welcome bonus transaction
            await self._log_transaction(
                user_id=user_id,
                amount=self.rewards_config["welcome_bonus"],
                tx_type="credit",
                reason="welcome_bonus",
                is_onchain=False,
            )

            return {
                "ton_address": ton_wallet["address"],
                "jetton_wallet": ton_wallet["jetton_wallet"],
                "balance_offchain": self.rewards_config["welcome_bonus"],
                "balance_onchain": 0,
            }

        except Exception as e:
            logger.error(f"Failed to create wallet for user {user_id}: {e}")
            raise

    async def get_balance(self, user_id: str) -> Dict:
        """Get both off-chain and on-chain balances"""
        from app.domains.economy.repository import get_wallet

        wallet = await get_wallet(user_id)
        if not wallet:
            return {"error": "Wallet not found"}

        # Get on-chain balance from TON
        onchain_balance = await self.ton.get_jetton_balance(wallet.ton_address)

        return {
            "offchain": wallet.balance_offchain,
            "onchain": float(onchain_balance),
            "total": wallet.balance_offchain + float(onchain_balance),
            "ton_balance": float(await self.ton.get_ton_balance(wallet.ton_address)),
        }

    async def add_tokens(self, user_id: str, amount: int, reason: str) -> bool:
        """Add tokens to user's off-chain balance"""
        from app.domains.economy.repository import (get_wallet,
                                                    update_offchain_balance)

        wallet = await get_wallet(user_id)
        if not wallet:
            # Auto-create wallet for new users
            await self.create_wallet(user_id)
            wallet = await get_wallet(user_id)

        new_balance = wallet.balance_offchain + amount
        await update_offchain_balance(user_id, new_balance)

        await self._log_transaction(
            user_id=user_id,
            amount=amount,
            tx_type="credit",
            reason=reason,
            is_onchain=False,
        )

        # Check if auto-withdrawal should trigger
        if new_balance >= 1000:
            await self._consider_auto_withdrawal(user_id, new_balance)

        return True

    async def spend_tokens(self, user_id: str, amount: int, reason: str) -> bool:
        """Spend tokens from user's balance (prioritize off-chain)"""
        from app.domains.economy.repository import (get_wallet,
                                                    update_offchain_balance)

        wallet = await get_wallet(user_id)
        if not wallet:
            return False

        # Check total available balance
        onchain_balance = await self.ton.get_jetton_balance(wallet.ton_address)
        total_available = wallet.balance_offchain + float(onchain_balance)

        if total_available < amount:
            return False

        # Prioritize spending from off-chain balance
        if wallet.balance_offchain >= amount:
            new_balance = wallet.balance_offchain - amount
            await update_offchain_balance(user_id, new_balance)
        else:
            # Need to use on-chain tokens
            # This would require user to sign transaction
            # For now, return False if insufficient off-chain balance
            return False

        await self._log_transaction(
            user_id=user_id,
            amount=-amount,
            tx_type="debit",
            reason=reason,
            is_onchain=False,
        )

        return True

    async def withdraw_to_chain(self, user_id: str, amount: int) -> Optional[str]:
        """Withdraw tokens from off-chain to on-chain wallet"""
        if amount < self.min_withdrawal:
            raise ValueError(f"Minimum withdrawal is {self.min_withdrawal} MAFIA")

        from app.domains.economy.repository import (get_wallet,
                                                    update_offchain_balance)

        wallet = await get_wallet(user_id)
        if not wallet or wallet.balance_offchain < amount:
            return None

        try:
            # Deduct from off-chain balance first
            new_balance = wallet.balance_offchain - amount
            await update_offchain_balance(user_id, new_balance)

            # Send on-chain transaction
            tx_hash = await self.ton.mint_jettons(
                to_address=wallet.ton_address, amount=Decimal(amount)
            )

            # Log both transactions
            await self._log_transaction(
                user_id=user_id,
                amount=-amount,
                tx_type="withdrawal",
                reason="withdraw_to_chain",
                is_onchain=False,
            )

            await self._log_transaction(
                user_id=user_id,
                amount=amount,
                tx_type="mint",
                reason=f"tx:{tx_hash}",
                is_onchain=True,
                tx_hash=tx_hash,
            )

            return tx_hash

        except Exception as e:
            # Rollback off-chain balance
            await update_offchain_balance(user_id, wallet.balance_offchain)
            logger.error(f"Withdrawal failed for user {user_id}: {e}")
            raise

    async def process_referral_reward(self, referrer_id: str, referred_id: str):
        """Process referral rewards"""
        await self.add_tokens(
            referrer_id,
            self.rewards_config["referral_reward"],
            f"referral_{referred_id}",
        )

        await self.add_tokens(
            referred_id,
            self.rewards_config["referred_bonus"],
            f"referred_by_{referrer_id}",
        )

    async def calculate_game_rewards(
        self, game_id: str, game_results: Dict
    ) -> Dict[str, int]:
        """Calculate rewards for game participants"""
        rewards = {}

        for player_id, stats in game_results.items():
            reward = self.rewards_config["game_base_reward"]

            if stats.get("won"):
                reward += self.rewards_config["win_bonus"]

            if stats.get("is_mvp"):
                reward += self.rewards_config["mvp_bonus"]

            if stats.get("linguistic_rating", 0) >= 4.0:
                reward += self.rewards_config["linguistic_bonus"]

            # Penalties
            if stats.get("was_afk"):
                reward = max(0, reward - 5)

            if stats.get("reported_count", 0) > 2:
                reward = max(0, reward // 2)

            rewards[player_id] = reward

        return rewards

    async def distribute_game_rewards(self, game_id: str, rewards: Dict[str, int]):
        """Distribute calculated rewards to players"""
        for player_id, amount in rewards.items():
            await self.add_tokens(player_id, amount, f"game_reward_{game_id}")

    async def purchase_item(
        self, user_id: str, item_type: str, item_id: str, price: int
    ) -> bool:
        """Generic purchase handler"""
        if not await self.spend_tokens(
            user_id, price, f"{item_type}_purchase_{item_id}"
        ):
            return False

        # Handle specific item types
        if item_type == "skin":
            from app.domains.skins.repository import add_skin_to_user

            await add_skin_to_user(user_id, item_id)

        elif item_type == "language":
            from app.domains.auth.repository import add_purchased_language

            await add_purchased_language(user_id, item_id)

        elif item_type == "premium":
            from app.domains.auth.repository import set_premium_status

            await set_premium_status(user_id, True)

        return True

    async def send_gift_tokens(
        self, from_user: str, to_user: str, amount: int, fee_percent: int = 10
    ) -> bool:
        """Send tokens as gift with platform fee"""
        fee = max(1, amount * fee_percent // 100)
        total_cost = amount + fee

        if not await self.spend_tokens(from_user, total_cost, f"gift_to_{to_user}"):
            return False

        await self.add_tokens(to_user, amount, f"gift_from_{from_user}")

        # Platform fee goes to treasury
        await self._log_transaction(
            user_id="treasury",
            amount=fee,
            tx_type="fee",
            reason=f"gift_fee_{from_user}_to_{to_user}",
            is_onchain=False,
        )

        return True

    async def claim_daily_reward(self, user_id: str) -> bool:
        """Claim daily login reward"""
        from app.domains.economy.repository import (get_wallet,
                                                    update_last_claim)

        wallet = await get_wallet(user_id)
        if not wallet:
            return False

        # Check if already claimed today
        if wallet.last_claim_at:
            time_since_claim = datetime.utcnow() - wallet.last_claim_at
            if time_since_claim.total_seconds() < 86400:  # 24 hours
                return False

        await self.add_tokens(
            user_id, self.rewards_config["daily_claim"], "daily_claim"
        )

        await update_last_claim(user_id, datetime.utcnow())
        return True

    async def get_transaction_history(self, user_id: str, limit: int = 50) -> list:
        """Get user's transaction history"""
        from app.domains.economy.repository import get_user_transactions

        return await get_user_transactions(user_id, limit)

    async def _consider_auto_withdrawal(self, user_id: str, balance: int):
        """Consider automatic withdrawal to chain for large balances"""
        if balance >= 5000:  # Auto-withdraw at 5000 tokens
            try:
                withdrawal_amount = balance - 100  # Keep 100 for fees
                await self.withdraw_to_chain(user_id, withdrawal_amount)
                logger.info(
                    f"Auto-withdrawal of {withdrawal_amount} MAFIA for user {user_id}"
                )
            except Exception as e:
                logger.error(f"Auto-withdrawal failed: {e}")

    async def _log_transaction(
        self,
        user_id: str,
        amount: int,
        tx_type: str,
        reason: str,
        is_onchain: bool = False,
        tx_hash: Optional[str] = None,
    ):
        """Log transaction to database"""
        from app.domains.economy.repository import save_transaction

        await save_transaction(
            {
                "user_id": user_id,
                "amount": amount,
                "type": tx_type,
                "reason": reason,
                "is_onchain": is_onchain,
                "tx_hash": tx_hash,
                "timestamp": datetime.utcnow(),
            }
        )

    async def get_leaderboard(self, period: str = "all", limit: int = 100) -> list:
        """Get token leaderboard"""
        from app.domains.economy.repository import get_leaderboard

        return await get_leaderboard(period, limit)

    async def verify_payment(self, tx_hash: str) -> Dict:
        """Verify external payment transaction"""
        return await self.ton.verify_transaction(tx_hash)


# Global instance
economy_service = EconomyService()
