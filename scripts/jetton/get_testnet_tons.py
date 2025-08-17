"""Get testnet TON from faucet"""
import asyncio

import httpx

from app.core.config import get_settings


async def get_testnet_tons():
    """Request testnet TON from faucet"""

    settings = get_settings()

    if settings.ENV not in ["dev", "staging"]:
        print("This script is only for dev/staging environments")
        return

    # Get service wallet address
    if not settings.SERVICE_WALLET_ADDRESS:
        print("SERVICE_WALLET_ADDRESS not set")
        return

    print(f"Requesting testnet TON for: {settings.SERVICE_WALLET_ADDRESS}")

    # TON testnet faucet API
    faucet_url = "https://testnet.toncenter.com/api/v2/faucet/request"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            faucet_url, json={"address": settings.SERVICE_WALLET_ADDRESS}
        )

        if response.status_code == 200:
            print("✅ Testnet TON requested successfully")
            print("Check balance in a few seconds")
        else:
            print(f"❌ Failed to request TON: {response.text}")
