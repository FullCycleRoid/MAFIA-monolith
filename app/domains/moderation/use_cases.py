from app.domains.moderation.service import moderation_service


# API функции для использования в других модулях
async def check_can_play(user_id: str) -> bool:
    """Может ли пользователь играть"""
    status = await moderation_service.check_user_status(user_id)
    return status["can_play"]


async def check_can_voice(user_id: str) -> bool:
    """Может ли пользователь использовать голосовой чат"""
    status = await moderation_service.check_user_status(user_id)
    return status["can_voice"]


async def check_can_send_gifts(user_id: str) -> bool:
    """Может ли пользователь отправлять подарки"""
    status = await moderation_service.check_user_status(user_id)
    return status["can_send_gifts"]


async def auto_moderate_content(user_id: str, content: str, content_type: str) -> bool:
    """Автоматическая модерация контента"""
    result = await moderation_service.auto_moderate_message(
        user_id=user_id,
        message=content,
        context={"type": content_type}
    )

    return result is None  # True если контент прошел модерацию
