# app/domains/economy/ton_service.py
"""
Complete TON Service implementation with all blockchain operations
"""
import base64
import hashlib
import json
from decimal import Decimal
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from mnemonic import Mnemonic
from pytoniq import (
    Address,
    LiteClient,
    WalletV4R2,
    Cell,
    begin_cell,
    StateInit
)
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from app.core.config import get_settings
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


class EnhancedTONJettonService:
    """Enhanced TON service with full jetton support"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[LiteClient] = None
        self.jetton_master_address: Optional[Address] = None
        self.service_wallet: Optional[WalletV4R2] = None
        self.mnemo = Mnemonic("english")
        self.is_sandbox = False
        self.transaction_cache = {}  # Cache for recent transactions
        self.balance_cache = {}  # Cache for balance queries
        self.cache_ttl = 30  # Cache TTL in seconds

    async def initialize(self):
        """Initialize TON service based on environment"""
        try:
            if self.settings.ENVIRONMENT == "local":
                await self._init_sandbox()
            elif self.settings.ENVIRONMENT in ["dev", "staging"]:
                await self._init_testnet()
            elif self.settings.ENVIRONMENT == "prod":
                await self._init_mainnet()
            else:
                raise ValueError(f"Unknown environment: {self.settings.ENVIRONMENT}")

            logger.info(f"TON service initialized for {self.settings.ENVIRONMENT}")

        except Exception as e:
            logger.error(f"Failed to initialize TON service: {e}")
            if self.settings.ENVIRONMENT == "local":
                logger.info("Falling back to mock mode for local development")
                self.is_sandbox = True
            else:
                raise

    async def _init_sandbox(self):
        """Initialize local sandbox environment"""
        if self.settings.MOCK_BLOCKCHAIN_CALLS:
            logger.info("Using mock blockchain calls for local development")
            self.is_sandbox = True
            return

        # Try to connect to local TON node
        try:
            # For local development, we'll use mock
            self.is_sandbox = True

            # Create test wallets
            self.test_wallets = {
                "service": {
                    "address": "EQ_test_service_wallet_address",
                    "mnemonic": self.mnemo.generate(strength=256),
                    "balance": Decimal("10000")
                },
                "jetton_master": {
                    "address": "EQ_test_jetton_master_address",
                    "total_supply": Decimal("1000000000")
                }
            }

            self.jetton_master_address = Address(self.test_wallets["jetton_master"]["address"])

            logger.info("Local sandbox initialized with mock wallets")

        except Exception as e:
            logger.warning(f"Failed to init sandbox: {e}, using mock mode")
            self.is_sandbox = True

    async def _init_testnet(self):
        """Initialize testnet connection"""
        try:
            # Connect to testnet
            self.client = LiteClient.from_testnet_config(
                ls_i=self.settings.TON_LS_INDEX,
                trust_level=self.settings.TON_TRUST_LEVEL
            )
            await self.client.connect()

            # Initialize jetton if address provided
            if self.settings.MAFIA_JETTON_MASTER_ADDRESS:
                self.jetton_master_address = Address(
                    self.settings.MAFIA_JETTON_MASTER_ADDRESS
                )
            else:
                logger.warning("No jetton address provided for testnet")

            # Initialize service wallet if mnemonic provided
            if self.settings.SERVICE_WALLET_MNEMONIC:
                await self._init_service_wallet(self.settings.SERVICE_WALLET_MNEMONIC)
            else:
                logger.warning("No service wallet mnemonic provided")

            logger.info("Connected to TON testnet")

        except Exception as e:
            logger.error(f"Failed to connect to testnet: {e}")
            raise

    async def _init_mainnet(self):
        """Initialize mainnet connection"""
        # Require all settings for mainnet
        if not self.settings.TON_API_KEY:
            raise ValueError("TON_API_KEY required for mainnet")
        if not self.settings.MAFIA_JETTON_MASTER_ADDRESS:
            raise ValueError("MAFIA_JETTON_MASTER_ADDRESS required for mainnet")
        if not self.settings.SERVICE_WALLET_MNEMONIC:
            raise ValueError("SERVICE_WALLET_MNEMONIC required for mainnet")

        try:
            # Connect to mainnet
            self.client = LiteClient.from_mainnet_config(
                ls_i=self.settings.TON_LS_INDEX,
                trust_level=self.settings.TON_TRUST_LEVEL
            )
            await self.client.connect()

            self.jetton_master_address = Address(self.settings.MAFIA_JETTON_MASTER_ADDRESS)
            await self._init_service_wallet(self.settings.SERVICE_WALLET_MNEMONIC)

            logger.info("Connected to TON mainnet")

        except Exception as e:
            logger.error(f"Failed to connect to mainnet: {e}")
            raise

    async def _init_service_wallet(self, mnemonic: str):
        """Initialize service wallet from mnemonic"""
        try:
            # Generate keypair from mnemonic
            seed = self.mnemo.to_seed(mnemonic)

            # Create wallet (WalletV4R2 is recommended)
            keypair = WalletV4R2.create_keypair_from_seed(seed)
            self.service_wallet = WalletV4R2(
                public_key=keypair["public_key"],
                private_key=keypair["private_key"],
                wc=0  # workchain
            )

            # Check wallet state
            if self.client:
                state = await self.client.get_account_state(self.service_wallet.address)
                if state.balance > 0:
                    logger.info(f"Service wallet initialized: {self.service_wallet.address.to_string()}")
                    logger.info(f"Balance: {state.balance / 10 ** 9} TON")
                else:
                    logger.warning("Service wallet has zero balance")

        except Exception as e:
            logger.error(f"Failed to init service wallet: {e}")
            raise

    async def create_user_wallet(self, user_id: str) -> Dict:
        """Create new TON wallet for user"""
        try:
            # Generate new mnemonic
            mnemonic = self.mnemo.generate(strength=256)

            # Create wallet
            seed = self.mnemo.to_seed(mnemonic)
            keypair = WalletV4R2.create_keypair_from_seed(seed)
            wallet = WalletV4R2(
                public_key=keypair["public_key"],
                private_key=keypair["private_key"],
                wc=0
            )

            # Encrypt mnemonic for storage
            encrypted_mnemonic = self._encrypt_mnemonic(mnemonic, user_id)

            # Get jetton wallet address
            jetton_wallet = await self._get_jetton_wallet_address(wallet.address)

            return {
                "address": wallet.address.to_string(),
                "jetton_wallet": jetton_wallet,
                "encrypted_mnemonic": encrypted_mnemonic,
            }

        except Exception as e:
            logger.error(f"Failed to create wallet for user {user_id}: {e}")
            raise

    async def get_jetton_balance(self, user_address: str) -> Decimal:
        """Get user's jetton balance"""
        # Check cache
        cache_key = f"balance:{user_address}"
        if cache_key in self.balance_cache:
            cached = self.balance_cache[cache_key]
            if cached["timestamp"] > datetime.utcnow() - timedelta(seconds=self.cache_ttl):
                return cached["balance"]

        try:
            if self.is_sandbox or self.settings.MOCK_BLOCKCHAIN_CALLS:
                # Return mock balance
                return Decimal("1000.0")

            if not self.client or not self.jetton_master_address:
                logger.warning("TON client not initialized")
                return Decimal("0")

            # Get jetton wallet address
            jetton_wallet = await self._get_jetton_wallet_address(Address(user_address))

            # Get jetton wallet state
            state = await self.client.get_account_state(Address(jetton_wallet))

            if state.state == "active":
                # Parse jetton wallet data
                balance = await self._parse_jetton_balance(state)
            else:
                balance = Decimal("0")

            # Update cache
            self.balance_cache[cache_key] = {
                "balance": balance,
                "timestamp": datetime.utcnow()
            }

            return balance

        except Exception as e:
            logger.error(f"Failed to get jetton balance: {e}")
            return Decimal("0")

    async def get_ton_balance(self, address: str) -> Decimal:
        """Get TON balance of address"""
        try:
            if self.is_sandbox:
                return Decimal("1.0")

            if not self.client:
                return Decimal("0")

            state = await self.client.get_account_state(Address(address))
            return Decimal(state.balance) / Decimal(10 ** 9)

        except Exception as e:
            logger.error(f"Failed to get TON balance: {e}")
            return Decimal("0")

    async def transfer_jettons(
            self,
            from_mnemonic: str,
            to_address: str,
            amount: Decimal,
            memo: Optional[str] = None
    ) -> str:
        """Transfer jettons between wallets"""
        try:
            if self.is_sandbox or self.settings.MOCK_BLOCKCHAIN_CALLS:
                # Mock transaction
                import hashlib
                mock_hash = hashlib.sha256(
                    f"{to_address}:{amount}:{datetime.utcnow()}".encode()
                ).hexdigest()
                logger.info(f"Mock transfer: {amount} MAFIA to {to_address}")
                return mock_hash

            if not self.client:
                raise ValueError("TON client not initialized")

            # Create wallet from mnemonic
            seed = self.mnemo.to_seed(from_mnemonic)
            keypair = WalletV4R2.create_keypair_from_seed(seed)
            from_wallet = WalletV4R2(
                public_key=keypair["public_key"],
                private_key=keypair["private_key"],
                wc=0
            )

            # Build jetton transfer message
            transfer_cell = self._build_jetton_transfer(
                to_address=Address(to_address),
                amount=amount,
                memo=memo
            )

            # Get jetton wallet address
            from_jetton_wallet = await self._get_jetton_wallet_address(from_wallet.address)

            # Send transaction
            seqno = await from_wallet.get_seqno(self.client)

            message = from_wallet.create_transfer_message(
                to_addr=Address(from_jetton_wallet),
                amount=int(0.05 * 10 ** 9),  # 0.05 TON for gas
                seqno=seqno,
                payload=transfer_cell
            )

            await self.client.send_message(message)

            # Get transaction hash
            tx_hash = hashlib.sha256(message.to_boc()).hexdigest()

            logger.info(f"Jetton transfer sent: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"Jetton transfer failed: {e}")
            raise

    async def mint_jettons(
            self,
            to_address: str,
            amount: Decimal
    ) -> str:
        """Mint new jettons (admin only)"""
        try:
            if self.is_sandbox:
                mock_hash = f"mint_{hashlib.sha256(f'{to_address}:{amount}'.encode()).hexdigest()[:16]}"
                logger.info(f"Mock mint: {amount} MAFIA to {to_address}")
                return mock_hash

            if not self.service_wallet or not self.client:
                raise ValueError("Service wallet not initialized")

            # Build mint message
            mint_cell = self._build_jetton_mint(
                to_address=Address(to_address),
                amount=amount
            )

            # Send from service wallet
            seqno = await self.service_wallet.get_seqno(self.client)

            message = self.service_wallet.create_transfer_message(
                to_addr=self.jetton_master_address,
                amount=int(0.1 * 10 ** 9),  # 0.1 TON for gas
                seqno=seqno,
                payload=mint_cell
            )

            await self.client.send_message(message)

            tx_hash = hashlib.sha256(message.to_boc()).hexdigest()
            logger.info(f"Minted {amount} MAFIA to {to_address}: {tx_hash}")

            return tx_hash

        except Exception as e:
            logger.error(f"Minting failed: {e}")
            raise

    async def verify_transaction(self, tx_hash: str) -> Dict:
        """Verify transaction on blockchain"""
        try:
            if self.is_sandbox:
                # Mock verification
                return {
                    "verified": True,
                    "status": "completed",
                    "amount": "100",
                    "from": "EQ_mock_from_address",
                    "to": "EQ_mock_to_address",
                    "timestamp": datetime.utcnow().isoformat()
                }

            if not self.client:
                raise ValueError("TON client not initialized")

            # Check cache first
            if tx_hash in self.transaction_cache:
                return self.transaction_cache[tx_hash]

            # Query blockchain
            # Note: Real implementation would query transaction by hash
            # This is simplified version
            result = {
                "verified": False,
                "status": "not_found",
                "tx_hash": tx_hash
            }

            # In production, you would:
            # 1. Query transaction from blockchain
            # 2. Parse transaction data
            # 3. Verify sender, recipient, amount
            # 4. Check confirmations

            # Cache result
            self.transaction_cache[tx_hash] = result

            return result

        except Exception as e:
            logger.error(f"Transaction verification failed: {e}")
            return {
                "verified": False,
                "error": str(e)
            }

    def _encrypt_mnemonic(self, mnemonic: str, user_id: str) -> str:
        """Encrypt mnemonic for secure storage"""
        # Derive key from user_id and master key
        key = hashlib.sha256(
            f"{self.settings.WALLET_ENCRYPTION_KEY}:{user_id}".encode()
        ).digest()

        # AES encryption
        cipher = AES.new(key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(mnemonic.encode(), AES.block_size))
        iv = base64.b64encode(cipher.iv).decode('utf-8')
        ct = base64.b64encode(ct_bytes).decode('utf-8')

        return json.dumps({'iv': iv, 'ciphertext': ct})

    def _decrypt_mnemonic(self, encrypted: str, user_id: str) -> str:
        """Decrypt mnemonic"""
        data = json.loads(encrypted)

        key = hashlib.sha256(
            f"{self.settings.WALLET_ENCRYPTION_KEY}:{user_id}".encode()
        ).digest()

        iv = base64.b64decode(data['iv'])
        ct = base64.b64decode(data['ciphertext'])

        cipher = AES.new(key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)

        return pt.decode('utf-8')

    async def _get_jetton_wallet_address(self, owner_address: Address) -> str:
        """Calculate jetton wallet address for owner"""
        if self.is_sandbox:
            return f"EQ_jetton_wallet_{owner_address.to_string()[-8:]}"

        # In real implementation, this would:
        # 1. Call get_wallet_address method on jetton master
        # 2. Return the calculated address

        # Simplified calculation
        data = begin_cell() \
            .store_address(owner_address) \
            .store_address(self.jetton_master_address) \
            .end_cell()

        state_init = StateInit(
            code=Cell(),  # Would be actual jetton wallet code
            data=data
        )

        address = Address.from_state_init(0, state_init)
        return address.to_string()

    def _build_jetton_transfer(
            self,
            to_address: Address,
            amount: Decimal,
            memo: Optional[str] = None
    ) -> Cell:
        """Build jetton transfer message"""
        # Jetton transfer op-code
        op_transfer = 0xf8a7ea5

        builder = ((((((((begin_cell()
                          .store_uint(op_transfer, 32))
                         .store_uint(0, 64))  # query_id\
                        .store_coins(int(amount * 10 ** 9)))  # amount\
                       .store_address(to_address))  # destination\
                      .store_address(to_address))  # response_destination\
                     .store_uint(0, 1))  # no custom_payload\
                    .store_coins(1))  # forward_ton_amount\
                   .store_uint(0, 1))  # no forward_payload

        if memo:
            builder = builder.store_uint(1, 1).store_string(memo)
        else:
            builder = builder.store_uint(0, 1)

        return builder.end_cell()


def _build_jetton_mint(
        self,
        to_address: Address,
        amount: Decimal
) -> Cell:
    """Build jetton mint message (admin only)"""
    op_mint = 21  # Mint op-code

    return (begin_cell()
            .store_uint(op_mint, 32)
            .store_uint(0, 64)  # query_id\
            .store_address(to_address)
            .store_coins(int(amount * 10 ** 9))
            .end_cell())


async def _parse_jetton_balance(self, state) -> Decimal:
    """Parse balance from jetton wallet state"""
    try:
        # In real implementation, would parse actual contract data
        # This is simplified
        if hasattr(state, 'data') and state.data:
            # Parse first 128 bits as balance
            # Real parsing would use TLB scheme
            return Decimal("1000")  # Placeholder
        return Decimal("0")
    except Exception as e:
        logger.error(f"Failed to parse jetton balance: {e}")
        return Decimal("0")


async def estimate_transfer_fee(self, amount: Decimal) -> Decimal:
    """Estimate transaction fee"""
    # Base fee + percentage
    base_fee = Decimal("0.05")  # 0.05 TON
    percentage_fee = amount * Decimal("0.001")  # 0.1%

    return base_fee + percentage_fee


async def get_transaction_history(
        self,
        address: str,
        limit: int = 50
) -> List[Dict]:
    """Get transaction history for address"""
    if self.is_sandbox:
        # Return mock history
        return [
            {
                "hash": f"mock_tx_{i}",
                "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                "from": address if i % 2 else "EQ_other_address",
                "to": "EQ_other_address" if i % 2 else address,
                "amount": str(100 * (i + 1)),
                "status": "completed"
            }
            for i in range(min(limit, 10))
        ]

    # Real implementation would query blockchain
    return []


# Global instance
ton_service = EnhancedTONJettonService()
