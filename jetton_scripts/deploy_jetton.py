"""
Deploy $MAFIA jetton to different networks
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from mnemonic import Mnemonic
from pytoniq import Address, LiteClient, WalletV4R2
from pytoniq_core import Cell, begin_cell

from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


class JettonDeployer:
    """Deploy and manage $MAFIA jetton"""

    def __init__(self):
        self.settings = get_settings()
        self.mnemo = Mnemonic("english")
        self.client: Optional[LiteClient] = None

    async def connect(self):
        """Connect to TON network"""
        if self.settings.ENV == "local":
            logger.info("Connecting to local sandbox...")
            # For local, we'll use sandbox
            return True

        elif self.settings.ENV in ["dev", "staging"]:
            logger.info("Connecting to testnet...")
            self.client = LiteClient.from_testnet_config(ls_i=0, trust_level=2)

        elif self.settings.ENV == "prod":
            logger.info("Connecting to mainnet...")
            if not self.settings.TON_API_KEY:
                raise ValueError("TON_API_KEY required for mainnet")
            self.client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
        else:
            raise ValueError(f"Unknown environment: {self.settings.ENV}")

        if self.client:
            await self.client.connect()
            logger.info("Connected to TON network")

        return True

    async def deploy_jetton(
        self,
        owner_mnemonic: str,
        jetton_name: str = "MAFIA Token",
        jetton_symbol: str = "MAFIA",
        decimals: int = 9,
        total_supply: int = 1_000_000_000,
    ):
        """Deploy jetton master contract"""

        if self.settings.ENV == "prod":
            response = input("⚠️  WARNING: Deploying to MAINNET. Continue? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Deployment cancelled")
                return None

        # Create wallet from mnemonic
        seed = self.mnemo.to_seed(owner_mnemonic)
        keypair = WalletV4R2.from_seed(seed)
        wallet = WalletV4R2(
            public_key=keypair.public_key, private_key=keypair.private_key, wc=0
        )

        logger.info(f"Deploying from wallet: {wallet.address.to_string()}")

        # Check wallet balance
        balance = await self._get_balance(wallet.address)
        logger.info(f"Wallet balance: {balance} TON")

        if balance < 0.5:
            raise ValueError(
                "Insufficient balance for deployment (need at least 0.5 TON)"
            )

        # Build jetton init data
        jetton_init_data = self._build_jetton_init_data(
            owner_address=wallet.address,
            jetton_name=jetton_name,
            jetton_symbol=jetton_symbol,
            decimals=decimals,
            total_supply=total_supply,
        )

        # Deploy contract
        jetton_address = await self._deploy_contract(
            wallet=wallet,
            init_data=jetton_init_data,
            amount=0.2,  # 0.2 TON for deployment
        )

        logger.info(f"✅ Jetton deployed at: {jetton_address}")

        # Save to environment file
        self._save_jetton_address(jetton_address)

        return jetton_address

    def _build_jetton_init_data(
        self,
        owner_address: Address,
        jetton_name: str,
        jetton_symbol: str,
        decimals: int,
        total_supply: int,
    ) -> Cell:
        """Build jetton initialization data"""

        # Jetton metadata
        metadata = {
            "name": jetton_name,
            "symbol": jetton_symbol,
            "decimals": str(decimals),
            "total_supply": str(total_supply),
            "description": "In-game currency for Mafia game",
        }

        # Build metadata cell
        metadata_cell = begin_cell()
        for key, value in metadata.items():
            metadata_cell = metadata_cell.store_string(f"{key}:{value};")

        # Build init data
        return (
            begin_cell()
            .store_coins(total_supply * (10**decimals))  # Total supply
            .store_address(owner_address)  # Admin address
            .store_ref(metadata_cell.end_cell())  # Metadata
            .store_ref(Cell())  # Jetton wallet code
            .end_cell()
        )

    async def _deploy_contract(
        self, wallet: WalletV4R2, init_data: Cell, amount: float
    ) -> str:
        """Deploy smart contract"""

        # Get contract code (simplified, in real case load from file)
        contract_code = self._get_jetton_code()

        # Calculate contract address
        state_init = (
            begin_cell()
            .store_uint(0, 2)
            .store_dict(contract_code)
            .store_dict(init_data)
            .store_uint(0, 1)
            .end_cell()
        )

        contract_address = Address.from_state_init(0, state_init)

        # Send deployment transaction
        seqno = await wallet.get_seqno()

        deploy_message = wallet.create_transfer_message(
            to_addr=contract_address,
            amount=int(amount * 10**9),
            seqno=seqno,
            state_init=state_init,
        )

        await self.client.send_message(deploy_message)

        # Wait for confirmation
        await asyncio.sleep(10)

        return contract_address.to_string()

    def _get_jetton_code(self) -> Cell:
        """Get jetton master contract code"""
        # In real implementation, load from compiled .fc file
        # For now, return placeholder
        return Cell()

    async def _get_balance(self, address: Address) -> float:
        """Get wallet balance"""
        if self.settings.ENV == "local":
            return 1000.0  # Mock balance for local

        account = await self.client.get_account_state(address)
        return account.balance / (10**9)

    def _save_jetton_address(self, address: str):
        """Save jetton address to environment file"""
        env_file = f".env.{self.settings.ENV}"

        # Read existing env file
        env_vars = {}
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        env_vars[key] = value

        # Update jetton address
        env_vars["MAFIA_JETTON_MASTER_ADDRESS"] = address

        # Write back
        with open(env_file, "w") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        logger.info(f"Jetton address saved to {env_file}")
