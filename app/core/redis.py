from redis.asyncio import Redis

from .config import settings


class RedisManager:
    _instance = None

    @classmethod
    def get_client(cls) -> Redis:
        if cls._instance is None:
            cls._instance = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return cls._instance


async def check_connection() -> bool:
    try:
        client = RedisManager.get_client()
        await client.ping()
        return True
    except Exception:
        return False
