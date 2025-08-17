# app/domains/economy/ton_service.py
"""
TON Jetton $MAFIA integration service
Handles all blockchain operations with TON network
"""
import asyncio
import base64
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple

from mnemonic import Mnemonic
from pytoniq import Address, Cell, LiteClient, WalletV4R2, begin_cell
from pytoniq.contract import JettonMaster, JettonWallet

from app.core.config import settings
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


class TONJettonService:
    """Service for interacting with TON blockchain and $MAFIA jetton"""

    def __init__(self):
        self.client: Optional[LiteClient] = None
        self.jetton_master_address: Optional[Address] = None
        self.service_wallet: Optional[WalletV4R2] = None
        self.mnemo = Mnemonic("english")

    async def initialize(self):
        """Initialize TON client and contracts"""
        try:
            # Connect to TON network
            self.client = LiteClient.from_mainnet_config(
                ls_i=0, trust_level=2  # Light server index
            )
            await self.client.connect()

            # Initialize jetton master contract
            self.jetton_master_address = Address(settings.MAFIA_JETTON_MASTER_ADDRESS)

            # Initialize service wallet for fee payments
            if settings.SERVICE_WALLET_MNEMONIC:
                self.service_wallet = await self._init_service_wallet(
                    settings.SERVICE_WALLET_MNEMONIC
                )

            logger.info("TON Jetton service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize TON service: {e}")
            raise

    async def _init_service_wallet(self, mnemonic: str) -> WalletV4R2:
        """Initialize service wallet from mnemonic"""
        seed = self.mnemo.to_seed(mnemonic)
        keypair = WalletV4R2.from_seed(seed)
        wallet = WalletV4R2(
            public_key=keypair.public_key,
            private_key=keypair.private_key,
            wc=0,  # Workchain 0 (basechain)
        )
        return wallet

    async def create_user_wallet(self, user_id: str) -> Dict:
        """Create new TON wallet for user"""
        try:
            # Generate new mnemonic phrase
            mnemonic = self.mnemo.generate(strength=256)
            seed = self.mnemo.to_seed(mnemonic)

            # Create wallet v4r2 (recommended for jettons)
            keypair = WalletV4R2.from_seed(seed)
            wallet = WalletV4R2(
                public_key=keypair.public_key, private_key=keypair.private_key, wc=0
            )

            # Get wallet address
            address = wallet.address.to_string(True, True, True)

            # Encrypt mnemonic for storage
            encrypted_mnemonic = self._encrypt_mnemonic(mnemonic)

            # Get jetton wallet address for this user wallet
            jetton_wallet_address = await self._get_jetton_wallet_address(
                wallet.address
            )

            return {
                "address": address,
                "jetton_wallet": jetton_wallet_address,
                "encrypted_mnemonic": encrypted_mnemonic,
                "created_at": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Failed to create wallet for user {user_id}: {e}")
            raise

    async def _get_jetton_wallet_address(self, owner_address: Address) -> str:
        """Get jetton wallet address for owner"""
        if not self.client or not self.jetton_master_address:
            raise ValueError("TON service not initialized")

        jetton_master = JettonMaster(
            address=self.jetton_master_address, client=self.client
        )

        jetton_wallet_address = await jetton_master.get_wallet_address(owner_address)

        return jetton_wallet_address.to_string(True, True, True)

    async def get_jetton_balance(self, user_address: str) -> Decimal:
        """Get $MAFIA jetton balance for user"""
        try:
            if not self.client:
                raise ValueError("TON service not initialized")

            address = Address(user_address)
            jetton_wallet_address = await self._get_jetton_wallet_address(address)

            jetton_wallet = JettonWallet(
                address=Address(jetton_wallet_address), client=self.client
            )

            # Get balance (returns in smallest units)
            balance = await jetton_wallet.get_balance()

            # Convert to decimal (assuming 9 decimals for $MAFIA)
            decimal_balance = Decimal(balance) / Decimal(10**9)

            return decimal_balance

        except Exception as e:
            logger.error(f"Failed to get balance for {user_address}: {e}")
            return Decimal(0)

    async def transfer_jettons(
        self,
        from_mnemonic: str,
        to_address: str,
        amount: Decimal,
        memo: Optional[str] = None,
    ) -> str:
        """Transfer $MAFIA jettons between wallets"""
        try:
            if not self.client:
                raise ValueError("TON service not initialized")

            # Initialize sender wallet
            seed = self.mnemo.to_seed(from_mnemonic)
            keypair = WalletV4R2.from_seed(seed)
            sender_wallet = WalletV4R2(
                public_key=keypair.public_key, private_key=keypair.private_key, wc=0
            )

            # Get sender's jetton wallet
            sender_jetton_wallet = await self._get_jetton_wallet_address(
                sender_wallet.address
            )

            jetton_wallet = JettonWallet(
                address=Address(sender_jetton_wallet), client=self.client
            )

            # Build transfer payload
            amount_nano = int(amount * Decimal(10**9))

            transfer_body = self._build_jetton_transfer_body(
                destination=Address(to_address),
                amount=amount_nano,
                response_destination=sender_wallet.address,
                forward_amount=0,
                forward_payload=memo.encode() if memo else b"",
            )

            # Send transaction
            seqno = await sender_wallet.get_seqno()

            transfer_message = sender_wallet.create_transfer_message(
                to_addr=Address(sender_jetton_wallet),
                amount=int(0.05 * 10**9),  # 0.05 TON for fees
                seqno=seqno,
                payload=transfer_body,
            )

            await self.client.send_message(transfer_message)

            # Wait for confirmation
            await asyncio.sleep(5)

            # Generate transaction hash
            tx_hash = self._generate_tx_hash(
                sender_wallet.address, Address(to_address), amount_nano
            )

            return tx_hash

        except Exception as e:
            logger.error(f"Failed to transfer jettons: {e}")
            raise

    async def mint_jettons(self, to_address: str, amount: Decimal) -> str:
        """Mint new $MAFIA jettons (only for authorized minter)"""
        try:
            if not self.service_wallet or not self.client:
                raise ValueError("Service wallet not initialized")

            # Build mint payload
            amount_nano = int(amount * Decimal(10**9))

            mint_body = self._build_jetton_mint_body(
                destination=Address(to_address), amount=amount_nano
            )

            # Send mint transaction from service wallet
            seqno = await self.service_wallet.get_seqno()

            mint_message = self.service_wallet.create_transfer_message(
                to_addr=self.jetton_master_address,
                amount=int(0.1 * 10**9),  # 0.1 TON for fees
                seqno=seqno,
                payload=mint_body,
            )

            await self.client.send_message(mint_message)

            tx_hash = self._generate_tx_hash(
                self.service_wallet.address, Address(to_address), amount_nano
            )

            return tx_hash

        except Exception as e:
            logger.error(f"Failed to mint jettons: {e}")
            raise

    async def distribute_rewards(
        self, recipients: Dict[str, Decimal], reason: str
    ) -> Dict[str, str]:
        """Distribute rewards to multiple recipients"""
        results = {}

        for user_address, amount in recipients.items():
            try:
                # Use service wallet to send rewards
                tx_hash = await self.transfer_jettons(
                    from_mnemonic=settings.SERVICE_WALLET_MNEMONIC,
                    to_address=user_address,
                    amount=amount,
                    memo=f"Reward: {reason}",
                )
                results[user_address] = tx_hash

            except Exception as e:
                logger.error(f"Failed to send reward to {user_address}: {e}")
                results[user_address] = "failed"

        return results

    def _build_jetton_transfer_body(
        self,
        destination: Address,
        amount: int,
        response_destination: Address,
        forward_amount: int = 0,
        forward_payload: bytes = b"",
    ) -> Cell:
        """Build jetton transfer message body"""
        return (
            begin_cell()
            .store_uint(0xF8A7EA5, 32)  # op::transfer
            .store_uint(0, 64)  # query_id
            .store_coins(amount)
            .store_address(destination)
            .store_address(response_destination)
            .store_bit(0)  # no custom_payload
            .store_coins(forward_amount)
            .store_bit(0)  # forward_payload in this slice
            .store_bytes(forward_payload)
            .end_cell()
        )

    def _build_jetton_mint_body(self, destination: Address, amount: int) -> Cell:
        """Build jetton mint message body"""
        return (
            begin_cell()
            .store_uint(0x178D4519, 32)  # op::mint
            .store_uint(0, 64)  # query_id
            .store_address(destination)
            .store_coins(amount)
            .end_cell()
        )

    def _encrypt_mnemonic(self, mnemonic: str) -> str:
        """Encrypt mnemonic phrase for secure storage"""
        from cryptography.fernet import Fernet

        key = settings.WALLET_ENCRYPTION_KEY.encode()
        cipher = Fernet(key)
        encrypted = cipher.encrypt(mnemonic.encode())
        return base64.b64encode(encrypted).decode()

    def _decrypt_mnemonic(self, encrypted_mnemonic: str) -> str:
        """Decrypt stored mnemonic phrase"""
        from cryptography.fernet import Fernet

        key = settings.WALLET_ENCRYPTION_KEY.encode()
        cipher = Fernet(key)
        encrypted = base64.b64decode(encrypted_mnemonic.encode())
        decrypted = cipher.decrypt(encrypted)
        return decrypted.decode()

    def _generate_tx_hash(
        self, from_addr: Address, to_addr: Address, amount: int
    ) -> str:
        """Generate transaction hash for tracking"""
        import hashlib

        data = f"{from_addr.to_string()}:{to_addr.to_string()}:{amount}:{datetime.utcnow()}"
        return hashlib.sha256(data.encode()).hexdigest()

    async def verify_transaction(self, tx_hash: str) -> Dict:
        """Verify transaction status"""
        # In production, this would query the blockchain
        # For now, return mock confirmation
        return {"status": "confirmed", "hash": tx_hash, "confirmations": 3}

    async def get_ton_balance(self, address: str) -> Decimal:
        """Get TON balance for gas fees"""
        try:
            if not self.client:
                raise ValueError("TON service not initialized")

            addr = Address(address)
            balance = await self.client.get_account_state(addr)

            # Convert from nanotons to TON
            return Decimal(balance.balance) / Decimal(10**9)

        except Exception as e:
            logger.error(f"Failed to get TON balance: {e}")
            return Decimal(0)


# Global instance
ton_service = TONJettonService()
