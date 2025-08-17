from datetime import datetime
from typing import List

from app.domains.matchmaking.service import (MatchmakingMode, QueuePlayer,
                                             matchmaking_queue)


# API функции
async def join_queue(user_id: str, mode: str, languages: List[str]) -> str:
    """Присоединение к очереди поиска игры"""
    # Получаем профиль игрока
    from app.domains.auth.repository import get_user_profile

    profile = await get_user_profile(user_id)

    if not profile:
        raise ValueError("User profile not found")

    queue_player = QueuePlayer(
        profile=profile,
        mode=MatchmakingMode(mode),
        preferred_languages=languages,
        join_time=datetime.utcnow(),
    )

    return await matchmaking_queue.add_player(queue_player)


async def leave_queue(user_id: str) -> bool:
    """Выход из очереди"""
    return await matchmaking_queue.remove_player(user_id)


async def create_private_lobby(host_id: str) -> str:
    """Создание приватного лобби"""
    from app.domains.auth.repository import get_user_profile

    profile = await get_user_profile(host_id)

    invite_code = _generate_invite_code()
    party_id = f"party_{invite_code}"

    host_player = QueuePlayer(
        profile=profile,
        mode=MatchmakingMode.FRIENDS,
        preferred_languages=[profile.native_language],
        join_time=datetime.utcnow(),
        invite_code=invite_code,
        party_id=party_id,
    )

    await matchmaking_queue.add_player(host_player)

    return invite_code


async def join_private_lobby(user_id: str, invite_code: str) -> bool:
    """Присоединение к приватному лобби по коду"""
    # Находим party_id по коду
    party_id = f"party_{invite_code}"

    # Проверяем существует ли такое лобби
    for player in matchmaking_queue.queues[MatchmakingMode.FRIENDS]:
        if player.party_id == party_id:
            # Добавляем игрока в ту же группу
            from app.domains.auth.repository import get_user_profile

            profile = await get_user_profile(user_id)

            new_player = QueuePlayer(
                profile=profile,
                mode=MatchmakingMode.FRIENDS,
                preferred_languages=[profile.native_language],
                join_time=datetime.utcnow(),
                invite_code=invite_code,
                party_id=party_id,
            )

            await matchmaking_queue.add_player(new_player)
            return True

    return False


def _generate_invite_code() -> str:
    """Генерация кода приглашения"""
    import random
    import string

    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
