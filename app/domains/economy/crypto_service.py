# app/domains/economy/crypto_service.py
from decimal import Decimal

from eth_account import Account
from web3 import Web3


class MafiaTokenContract:
    """Взаимодействие со смарт-контрактом токена $MAFIA"""

    def __init__(self, contract_address: str, abi: str, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )
        self.decimals = 18  # Стандартные decimals для ERC-20

    async def get_balance(self, wallet_address: str) -> Decimal:
        """Получение баланса кошелька"""
        balance = self.contract.functions.balanceOf(
            Web3.to_checksum_address(wallet_address)
        ).call()
        return Decimal(balance) / Decimal(10**self.decimals)

    async def transfer(
        self, from_wallet: str, to_wallet: str, amount: Decimal, private_key: str
    ) -> str:
        """Перевод токенов"""
        amount_wei = int(amount * Decimal(10**self.decimals))

        # Создаем транзакцию
        tx = self.contract.functions.transfer(
            Web3.to_checksum_address(to_wallet), amount_wei
        ).build_transaction(
            {
                "from": Web3.to_checksum_address(from_wallet),
                "nonce": self.w3.eth.get_transaction_count(from_wallet),
                "gas": 100000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )

        # Подписываем и отправляем
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return tx_hash.hex()
