from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from ..shared.utils.logger import get_logger
from .config import settings

logger = get_logger(__name__)


Base = declarative_base()

# Создаем движок БД с asyncpg
# Добавить пул соединений
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
)

# Создаем асинхронную сессию
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# app/core/database.py
async def init_db():
    if settings.ENV == "dev":
        # Автоматическое создание таблиц в dev
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        # В prod используем только миграции
        logger.info("Skipping auto table creation in production")


async def check_connection() -> bool:
    try:
        async with engine.connect():
            return True
    except Exception:
        return False
