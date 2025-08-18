"""Initialize local development data"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import engine
from app.shared.utils.logger import get_logger
from alembic.config import Config
from alembic import command
from sqlalchemy import text

logger = get_logger(__name__)


async def check_and_run_migrations():
    """Check if migrations need to be run and run them if necessary"""
    async with engine.begin() as conn:
        # Check if alembic_version table exists
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                );
            """)
        )
        alembic_exists = result.scalar()

        # Check if skins_catalog table exists
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'skins_catalog'
                );
            """)
        )
        table_exists = result.scalar()

        if not alembic_exists or not table_exists:
            logger.info("Running database migrations...")
            # Run migrations
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
            logger.info("✅ Migrations completed")
        else:
            logger.info("Database schema is up to date")


async def wait_for_table(table_name: str, max_attempts: int = 30):
    """Wait for table to exist in database"""
    from sqlalchemy import text

    for attempt in range(max_attempts):
        async with engine.begin() as conn:
            result = await conn.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table_name}'
                    );
                """)
            )
            if result.scalar():
                logger.info(f"✅ Table {table_name} exists")
                return True

        logger.info(f"Waiting for table {table_name}... (attempt {attempt + 1}/{max_attempts})")
        await asyncio.sleep(1)

    raise Exception(f"Table {table_name} was not created after {max_attempts} attempts")


async def init_local_data():
    """Initialize test data for local development"""

    # Wait for critical tables to exist
    await wait_for_table('skins_catalog')
    await wait_for_table('auth_users')
    await wait_for_table('economy_wallets')

    logger.info("Initializing local development data...")
    # Import models after tables are created
    from app.domains.auth.models import User
    from app.domains.economy.models import Wallet
    from app.domains.skins.models import SkinCatalog
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Check if data already exists
            from sqlalchemy import select
            result = await db.execute(select(User).limit(1))
            if result.scalar_one_or_none():
                logger.info("Data already exists, skipping initialization")
                return

            # Create test users
            test_users = [
                {
                    "id": "test_user_1",
                    "telegram_id": 123456789,
                    "first_name": "Test",
                    "last_name": "User",
                    "username": "testuser",
                    "language_code": "en",
                    "rating": 1200,
                    "games_played": 10,
                    "games_won": 5,
                    "win_rate": 0.5,
                },
                {
                    "id": "test_user_2",
                    "telegram_id": 987654321,
                    "first_name": "Demo",
                    "last_name": "Player",
                    "username": "demoplayer",
                    "language_code": "ru",
                    "rating": 1000,
                    "games_played": 5,
                    "games_won": 2,
                    "win_rate": 0.4,
                },
            ]

            for user_data in test_users:
                user = User(**user_data)
                db.add(user)

                # Create wallet for user
                wallet = Wallet(
                    id=f"wallet_{user_data['id']}",
                    user_id=user_data['id'],
                    ton_address=f"EQ_test_address_{user_data['id']}",
                    jetton_wallet=f"EQ_test_jetton_{user_data['id']}",
                    encrypted_mnemonic="mock_encrypted_mnemonic",
                    balance_offchain=1000,
                    balance_onchain=0,
                )
                db.add(wallet)

            # Create test skins
            test_skins = [
                {
                    "id": "skin_classic",
                    "name": "Classic Mafia",
                    "description": "Traditional mafia look",
                    "price_mafia": 0,
                    "image_url": "/assets/skins/classic.png",
                    "preview_url": "/assets/skins/classic_preview.png",
                    "rarity": "common",
                    "is_limited": False,  # Add missing field
                },
                {
                    "id": "skin_golden",
                    "name": "Golden Boss",
                    "description": "Luxurious golden style",
                    "price_mafia": 500,
                    "image_url": "/assets/skins/golden.png",
                    "preview_url": "/assets/skins/golden_preview.png",
                    "rarity": "legendary",
                    "is_limited": False,  # Add missing field
                },
            ]

            for skin_data in test_skins:
                skin = SkinCatalog(**skin_data)
                db.add(skin)

            await db.commit()
            logger.info("✅ Local data initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing data: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(init_local_data())