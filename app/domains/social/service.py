# app/domains/social/service.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from app.domains.social.entities import SocialInteraction, GiftType, Gift, InteractionType, UserSocialStats


class SocialService:
    def __init__(self):
        self.interactions: List[SocialInteraction] = []
        self.user_stats: Dict[str, UserSocialStats] = {}
        self.gifts_catalog = self._init_gifts_catalog()

    def _init_gifts_catalog(self) -> Dict[GiftType, Gift]:
        return {
            GiftType.ROSE: Gift(
                gift_id="gift_rose",
                type=GiftType.ROSE,
                price_mafia=10,
                icon_url="/assets/gifts/rose.png",
                animation_url="/assets/gifts/rose_animation.json"
            ),
            GiftType.CHAMPAGNE: Gift(
                gift_id="gift_champagne",
                type=GiftType.CHAMPAGNE,
                price_mafia=50,
                icon_url="/assets/gifts/champagne.png",
                animation_url="/assets/gifts/champagne_animation.json"
            ),
            GiftType.DIAMOND: Gift(
                gift_id="gift_diamond",
                type=GiftType.DIAMOND,
                price_mafia=100,
                icon_url="/assets/gifts/diamond.png",
                animation_url="/assets/gifts/diamond_animation.json"
            ),
            GiftType.CROWN: Gift(
                gift_id="gift_crown",
                type=GiftType.CROWN,
                price_mafia=500,
                icon_url="/assets/gifts/crown.png",
                animation_url="/assets/gifts/crown_animation.json",
                is_limited=True
            )
        }

    async def send_gift(self, from_user: str, to_user: str,
                        gift_type: GiftType, game_id: Optional[str] = None) -> bool:
        """Отправка подарка"""
        gift = self.gifts_catalog.get(gift_type)
        if not gift:
            return False

        # Проверяем баланс
        from app.domains.economy.service import EconomyService
        economy = EconomyService()

        if not await economy.spend_tokens(from_user, gift.price_mafia, f"gift_{gift_type}"):
            return False

        # Начисляем получателю часть стоимости (50%)
        await economy.add_tokens(to_user, gift.price_mafia // 2, "gift_received")

        # Записываем взаимодействие
        interaction = SocialInteraction(
            interaction_id=self._generate_id(),
            from_user=from_user,
            to_user=to_user,
            type=InteractionType.GIFT,
            game_id=game_id,
            timestamp=datetime.utcnow(),
            data={"gift_type": gift_type.value, "price": gift.price_mafia}
        )

        self.interactions.append(interaction)

        # Обновляем статистику
        self._update_stats(to_user, "gifts_received", 1)
        self._update_stats(from_user, "gifts_sent", 1)

        # Уведомление
        await self._notify_gift_received(to_user, from_user, gift_type)

        return True

    async def rate_linguistic_ability(self, rater: str, rated: str,
                                      language: str, score: int, game_id: str) -> bool:
        """Оценка лингвистических способностей (1-5)"""
        if score < 1 or score > 5:
            return False

        interaction = SocialInteraction(
            interaction_id=self._generate_id(),
            from_user=rater,
            to_user=rated,
            type=InteractionType.LINGUISTIC_RATE,
            game_id=game_id,
            timestamp=datetime.utcnow(),
            data={"language": language, "score": score}
        )

        self.interactions.append(interaction)

        # Обновляем средний рейтинг
        await self._update_linguistic_rating(rated, language, score)

        # Награда за высокий рейтинг
        if score >= 4:
            from app.domains.economy.service import EconomyService
            economy = EconomyService()
            await economy.add_tokens(rated, 5, "linguistic_bonus")

        return True

    async def report_player(self, reporter: str, reported: str,
                            reason: str, game_id: str, evidence: Optional[str] = None) -> str:
        """Жалоба на игрока"""
        report_id = self._generate_id()

        interaction = SocialInteraction(
            interaction_id=report_id,
            from_user=reporter,
            to_user=reported,
            type=InteractionType.REPORT,
            game_id=game_id,
            timestamp=datetime.utcnow(),
            data={
                "reason": reason,
                "evidence": evidence,
                "status": "pending"
            }
        )

        self.interactions.append(interaction)

        # Автоматическая проверка
        await self._auto_moderate_report(report_id, reported, reason)

        return report_id

    async def _auto_moderate_report(self, report_id: str, user_id: str, reason: str):
        """Автоматическая модерация"""
        # Подсчитываем количество жалоб за последние 24 часа
        recent_reports = self._get_recent_reports(user_id, hours=24)

        # Если больше 5 жалоб - временный бан
        if len(recent_reports) >= 5:
            from app.domains.moderation.service import ModerationService
            moderation = ModerationService()

            # Проверяем причины
            if reason in ["toxic_behavior", "hate_speech", "cheating"]:
                await moderation.ban_user(user_id, duration_hours=24, reason="auto_ban_reports")
            elif reason in ["bad_language_skills", "afk"]:
                await moderation.restrict_user(user_id, restriction_type="voice_mute", hours=2)

    def _get_recent_reports(self, user_id: str, hours: int) -> List[SocialInteraction]:
        """Получение недавних жалоб"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            i for i in self.interactions
            if i.type == InteractionType.REPORT
               and i.to_user == user_id
               and i.timestamp > cutoff_time
        ]

    def _update_stats(self, user_id: str, stat: str, value: int):
        """Обновление статистики пользователя"""
        if user_id not in self.user_stats:
            self.user_stats[user_id] = UserSocialStats(user_id=user_id)

        current = getattr(self.user_stats[user_id], stat, 0)
        setattr(self.user_stats[user_id], stat, current + value)

    async def _update_linguistic_rating(self, user_id: str, language: str, score: int):
        """Обновление лингвистического рейтинга"""
        from app.domains.auth.repository import update_linguistic_rating
        await update_linguistic_rating(user_id, language, score)

    async def _notify_gift_received(self, to_user: str, from_user: str, gift_type: GiftType):
        """Уведомление о получении подарка"""
        from app.core.websocket_manager import websocket_manager
        await websocket_manager.send_to_user(
            to_user,
            {
                "event": "gift_received",
                "from": from_user,
                "gift": gift_type.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())


social_service = SocialService()


