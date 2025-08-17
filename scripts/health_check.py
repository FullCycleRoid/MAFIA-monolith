"""Health check script for all environments"""
import asyncio

import httpx

from app.core.environments import get_settings


async def check_health():
    settings = get_settings()

    urls = {
        "local": "http://localhost:8001/health",
        "dev": "http://localhost:8000/health",
        "staging": "https://staging.yourapp.com/health",
        "prod": "https://api.yourapp.com/health",
    }

    url = urls.get(settings.ENV)
    if not url:
        print(f"Unknown environment: {settings.ENV}")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

            print(f"Environment: {settings.ENV}")
            print(f"Status: {data['status']}")
            print(f"Services:")
            for service, status in data["services"].items():
                emoji = "✅" if status else "❌"
                print(f"  {emoji} {service}: {status}")

            return data["status"] == "healthy"

    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(check_health())
