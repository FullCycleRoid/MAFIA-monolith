from datetime import datetime
from decimal import Decimal
from typing import Dict


class EconomyService:
    """Основной сервис экономики"""

    def __init__(self):
        self.token_contract = None  # Инициализируется при старте
        self.exchange_rate = Decimal("0.001")  # 1 MAFIA = $0.001
        self.rewards_pool_address = None

    async def create_wallet(self, user_id: str) -> Dict:
        """Создание кошелька для пользователя"""
        # Генерируем новый Ethereum кошелек
        account = Account.create()

        # Сохраняем в БД (зашифрованно)
        from app.domains.economy.repository import save_wallet
        wallet_data = {
            "user_id": user_id,
            "address": account.address,
            "encrypted_key": self._encrypt_key(account.key.hex()),
            "balance_cache": 0,
            "created_at": datetime.utcnow()
        }

        await save_wallet(wallet_data)

        # Начальный бонус новым пользователям
        await self.add_tokens(user_id, 100, "welcome_bonus")

        return {
            "address": account.address,
            "balance": 100
        }

    async def add_tokens(self, user_id: str, amount: int, reason: str) -> bool:
        """Начисление токенов"""
        from app.domains.economy.repository import get_wallet, update_balance

        wallet = await get_wallet(user_id)
        if not wallet:
            return False

        # Обновляем баланс в БД
        new_balance = wallet.balance_cache + amount
        await update_balance(user_id, new_balance)

        # Логируем транзакцию
        await self._log_transaction(
            user_id=user_id,
            amount=amount,
            type="credit",
            reason=reason
        )

        # Если накопилось достаточно, делаем on-chain транзакцию
        if new_balance >= 1000:  # Порог для вывода on-chain
            await self._process_on_chain_transfer(user_id, wallet.address, new_balance)

        return True

    async def spend_tokens(self, user_id: str, amount: int, reason: str) -> bool:
        """Списание токенов"""
        from app.domains.economy.repository import get_wallet, update_balance

        wallet = await get_wallet(user_id)
        if not wallet or wallet.balance_cache < amount:
            return False

        new_balance = wallet.balance_cache - amount
        await update_balance(user_id, new_balance)

        await self._log_transaction(
            user_id=user_id,
            amount=-amount,
            type="debit",
            reason=reason
        )

        return True

    async def process_referral_reward(self, referrer_id: str, referred_id: str):
        """Начисление реферальной награды"""
        # Реферер получает 50 MAFIA
        await self.add_tokens(referrer_id, 50, f"referral_{referred_id}")

        # Новый пользователь получает 25 MAFIA бонус
        await self.add_tokens(referred_id, 25, f"referred_by_{referrer_id}")

    async def calculate_game_rewards(self, game_id: str, game_results: Dict) -> Dict[str, int]:
        """Расчет наград за игру"""
        rewards = {}

        # Базовые награды
        base_reward = 10
        win_bonus = 20
        mvp_bonus = 15
        linguistic_bonus = 5

        for player_id, stats in game_results.items():
            reward = base_reward

            # Бонус за победу
            if stats.get("won"):
                reward += win_bonus

            # MVP бонус (лучший игрок)
            if stats.get("is_mvp"):
                reward += mvp_bonus

            # Бонус за хорошую речь
            if stats.get("linguistic_rating", 0) >= 4.0:
                reward += linguistic_bonus

            # Штраф за AFK или плохое поведение
            if stats.get("was_afk"):
                reward = max(0, reward - 5)

            rewards[player_id] = reward

        return rewards

    async def purchase_skin(self, user_id: str, skin_id: str, price: int) -> bool:
        """Покупка скина"""
        if not await self.spend_tokens(user_id, price, f"skin_purchase_{skin_id}"):
            return False

        from app.domains.skins.repository import add_skin_to_user
        await add_skin_to_user(user_id, skin_id)

        return True

    async def purchase_language_pack(self, user_id: str, language: str, price: int) -> bool:
        """Покупка языкового пакета"""
        if not await self.spend_tokens(user_id, price, f"language_{language}"):
            return False

        from app.domains.auth.repository import add_purchased_language
        await add_purchased_language(user_id, language)

        return True

    async def _process_on_chain_transfer(self, user_id: str, wallet_address: str, amount: int):
        """Обработка on-chain транзакции"""
        # Это будет вызываться в фоновой задаче
        try:
            if self.token_contract:
                tx_hash = await self.token_contract.transfer(
                    from_wallet=self.rewards_pool_address,
                    to_wallet=wallet_address,
                    amount=Decimal(amount),
                    private_key=self._get_pool_private_key()
                )

                # Сохраняем хэш транзакции
                from app.domains.economy.repository import save_blockchain_tx
                await save_blockchain_tx(user_id, tx_hash, amount)
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс
            print(f"On-chain transfer failed: {e}")

    async def _log_transaction(self, user_id: str, amount: int, type: str, reason: str):
        """Логирование транзакции"""
        from app.domains.economy.repository import save_transaction
        await save_transaction({
            "user_id": user_id,
            "amount": amount,
            "type": type,
            "reason": reason,
            "timestamp": datetime.utcnow()
        })

    def _encrypt_key(self, private_key: str) -> str:
        """Шифрование приватного ключа"""
        # Используем криптографию для безопасного хранения
        from cryptography.fernet import Fernet
        cipher = Fernet(self._get_encryption_key())
        return cipher.encrypt(private_key.encode()).decode()

    def _get_encryption_key(self) -> bytes:
        """Получение ключа шифрования из переменных окружения"""
        import os
        key = os.getenv("WALLET_ENCRYPTION_KEY")
        if not key:
            raise ValueError("WALLET_ENCRYPTION_KEY not set")
        return key.encode()

    def _get_pool_private_key(self) -> str:
        """Получение приватного ключа пула наград"""
        import os
        return os.getenv("REWARDS_POOL_PRIVATE_KEY")

economy_service = EconomyService()
