# app/domains/economy/ton_service.py
from decimal import Decimal
from typing import Optional

from mnemonic import Mnemonic
from pytoniq import Address, LiteClient, WalletV4R2

from app.core.config import get_settings
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


class EnhancedTONJettonService:
    """Enhanced TON service with multi-environment support"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[LiteClient] = None
        self.jetton_master_address: Optional[Address] = None
        self.service_wallet: Optional[WalletV4R2] = None
        self.mnemo = Mnemonic("english")
        self.is_sandbox = False

    async def initialize(self):
        """Initialize based on environment"""
        try:
            if self.settings.ENVIRONMENT == "local":
                await self._init_sandbox()
            elif self.settings.ENVIRONMENT in ["dev", "staging"]:
                await self._init_testnet()
            elif self.settings.ENVIRONMENT == "prod":
                await self._init_mainnet()
            else:
                raise ValueError(f"Unknown environment: {self.settings.ENVIRONMENT}")

            logger.info(f"TON service initialized for {self.settings.ENVIRONMENT} environment")

        except Exception as e:
            logger.error(f"Failed to initialize TON service: {e}")
            if self.settings.ENVIRONMENT == "local":
                logger.info("Falling back to mock mode for local development")
                self.is_sandbox = True
            else:
                raise

    async def _init_sandbox(self):
        """Initialize local sandbox"""
        if self.settings.MOCK_BLOCKCHAIN_CALLS:
            logger.info("Using mock blockchain calls for local development")
            self.is_sandbox = True
            return

        # Try to connect to local sandbox
        try:
            from ton_sandbox import Sandbox

            self.sandbox = Sandbox()
            await self.sandbox.start()

            # Create test wallet with funds
            self.test_wallet = await self.sandbox.create_wallet()
            await self.sandbox.give_tons(self.test_wallet.address, 10000)

            # Deploy test jetton
            await self._deploy_test_jetton()

            self.is_sandbox = True
            logger.info("Local sandbox initialized successfully")

        except ImportError:
            logger.warning("ton_sandbox not installed, using mock mode")
            self.is_sandbox = True

    async def _init_testnet(self):
        """Initialize testnet connection"""
        # Connect to testnet
        self.client = LiteClient.from_testnet_config(
            ls_i=self.settings.TON_LS_INDEX, trust_level=self.settings.TON_TRUST_LEVEL
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

    async def _init_mainnet(self):
        """Initialize mainnet connection"""
        # Connect to mainnet with API key
        if not self.settings.TON_API_KEY:
            raise ValueError("TON_API_KEY required for mainnet")

        self.client = LiteClient.from_mainnet_config(
            ls_i=self.settings.TON_LS_INDEX, trust_level=self.settings.TON_TRUST_LEVEL
        )
        await self.client.connect()

        # Require jetton address for mainnet
        if not self.settings.MAFIA_JETTON_MASTER_ADDRESS:
            raise ValueError("MAFIA_JETTON_MASTER_ADDRESS required for mainnet")

        self.jetton_master_address = Address(self.settings.MAFIA_JETTON_MASTER_ADDRESS)

        # Require service wallet for mainnet
        if not self.settings.SERVICE_WALLET_MNEMONIC:
            raise ValueError("SERVICE_WALLET_MNEMONIC required for mainnet")

        await self._init_service_wallet(self.settings.SERVICE_WALLET_MNEMONIC)

    async def _deploy_test_jetton(self):
        """Deploy jetton for testing (sandbox/testnet only)"""
        if self.settings.ENVIRONMENT not in ["local", "dev"]:
            raise ValueError("Can only deploy test jetton in local/dev environment")

        # Jetton deployment logic here
        logger.info("Deploying test jetton...")

    async def get_jetton_balance(self, user_address: str) -> Decimal:
        """Get balance with environment-specific handling"""
        if self.is_sandbox or self.settings.MOCK_BLOCKCHAIN_CALLS:
            # Return mock balance for testing
            return Decimal("1000.0")

        # Real blockchain call
        return await super().get_jetton_balance(user_address)

    async def transfer_jettons(
        self,
        from_mnemonic: str,
        to_address: str,
        amount: Decimal,
        memo: Optional[str] = None,
    ) -> str:
        """Transfer with environment-specific handling"""
        if self.is_sandbox or self.settings.MOCK_BLOCKCHAIN_CALLS:
            # Return mock transaction hash
            import hashlib

            mock_hash = hashlib.sha256(f"{to_address}:{amount}".encode()).hexdigest()
            logger.info(f"Mock transfer: {amount} to {to_address}")
            return mock_hash

        # Real blockchain transaction
        return await super().transfer_jettons(from_mnemonic, to_address, amount, memo)
