import uuid

from sqlalchemy import select

from app.core.database import get_db

from .models import User
from ...shared.utils.logger import get_logger


logger = get_logger(__name__)


async def get_user_by_telegram_id(telegram_id: int):
    async with get_db() as db:
        result = await db.execute(select(User).filter(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def create_user(user_data: dict):
    async with get_db() as db:
        new_user = User(
            id=str(uuid.uuid4()),
            telegram_id=user_data["telegram_id"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            username=user_data["username"],
            language_code=user_data["language_code"],
            is_bot=user_data["is_bot"],
            allows_write_to_pm=user_data["allows_write_to_pm"],
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user


async def update_linguistic_rating(user_id: str, language: str, score: int):
    """Обновление лингвистического рейтинга"""
    from app.domains.auth.models import User

    async with get_db() as db:
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            if not hasattr(user, "linguistic_rating"):
                user.linguistic_rating = {}

            # Вычисляем средний рейтинг
            current_ratings = user.linguistic_rating.get(language, [])
            current_ratings.append(score)
            # Храним последние 10 оценок
            if len(current_ratings) > 10:
                current_ratings = current_ratings[-10:]

            avg_rating = sum(current_ratings) / len(current_ratings)
            user.linguistic_rating[language] = avg_rating

            await db.commit()


async def add_purchased_language(user_id: str, language: str):
    """Добавление купленного языка"""
    from app.domains.auth.models import User

    async with get_db() as db:
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            if not hasattr(user, "purchased_languages"):
                user.purchased_languages = []

            if language not in user.purchased_languages:
                user.purchased_languages.append(language)
                await db.commit()


async def get_user_profile(user_id: str):
    from app.domains.matchmaking.entities import PlayerProfile

    user = await get_user_by_id(user_id)
    if not user:
        return None

    return PlayerProfile(
        user_id=user.id,
        telegram_id=user.telegram_id,
        username=user.username or f"user_{user.telegram_id}",
        rating=user.rating,
        country=user.country,
        native_language=user.language_code,
        spoken_languages=user.spoken_languages,
        purchased_languages=user.purchased_languages,
        games_played=user.games_played,
        win_rate=user.win_rate,
        linguistic_rating=user.linguistic_rating,
        is_premium=user.is_premium,
        skin_id=user.skin_id,
        banned_until=user.banned_until,
        muted_players=set(user.muted_players),
    )


async def get_user_by_id(user_id: str):
    """Get user by ID"""
    from app.domains.auth.models import User

    async with get_db() as db:
        try:
            result = await db.execute(select(User).filter(User.id == user_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

async def get_user_by_referral_code(referral_code: str):
    """Get user by referral code"""
    from app.domains.auth.models import User

    async with get_db() as db:
        try:
            result = await db.execute(
                select(User).filter(User.referral_code == referral_code)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by referral {referral_code}: {e}")
            return None
