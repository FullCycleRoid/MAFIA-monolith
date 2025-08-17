"""Deploy jetton to testnet"""
import asyncio
import os

from deploy_jetton import JettonDeployer


async def main():
    # Check if already deployed
    if os.getenv("MAFIA_JETTON_MASTER_ADDRESS"):
        print("Jetton already deployed, skipping...")
        return

    deployer = JettonDeployer()
    await deployer.connect()

    # Generate new mnemonic for testnet
    from mnemonic import Mnemonic

    mnemo = Mnemonic("english")
    mnemonic = mnemo.generate(strength=256)

    print(f"Generated service wallet mnemonic (SAVE THIS!):")
    print(f"{mnemonic}")
    print("-" * 50)

    # Get testnet TON from faucet first
    print("Get testnet TON from: https://t.me/testgiver_ton_bot")
    print("Send TON to service wallet address")
    input("Press Enter when ready...")

    # Deploy jetton
    jetton_address = await deployer.deploy_jetton(
        owner_mnemonic=mnemonic,
        jetton_name="MAFIA Test Token",
        jetton_symbol="tMAFIA",
        decimals=9,
        total_supply=1_000_000_000,
    )

    print(f"✅ Testnet jetton deployed: {jetton_address}")

    # Save mnemonic
    with open(".env.dev", "a") as f:
        f.write(f"\nSERVICE_WALLET_MNEMONIC={mnemonic}")
