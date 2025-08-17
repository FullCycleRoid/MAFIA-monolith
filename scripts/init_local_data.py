"""Initialize local development data"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import get_db, init_db
from app.domains.auth.models import User
from app.domains.economy.models import Wallet
from app.domains.skins.models import SkinCatalog
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


async def init_local_data():
    """Initialize test data for local development"""

    logger.info("Initializing local development data...")

    # Initialize database
    await init_db()

    async with get_db() as db:
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
            },
        ]

        for user_data in test_users:
            user = User(**user_data)
            db.add(user)

            # Create wallet for user
            wallet = Wallet(
                id=f"wallet_{user_data['id']}",
                user_id=user_data["id"],
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
            },
            {
                "id": "skin_golden",
                "name": "Golden Boss",
                "description": "Luxurious golden style",
                "price_mafia": 500,
                "image_url": "/assets/skins/golden.png",
                "preview_url": "/assets/skins/golden_preview.png",
                "rarity": "legendary",
            },
        ]

        for skin_data in test_skins:
            skin = SkinCatalog(**skin_data)
            db.add(skin)

        await db.commit()

    logger.info("✅ Local data initialized successfully")
