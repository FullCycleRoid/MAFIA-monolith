# app/domains/moderation/service.py
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.domains.game.repository import kick_player
from app.domains.moderation.entities import (Ban, BanReason, BanType,
                                             ModeratorAction, Restriction,
                                             RestrictionType)
from app.domains.voice.repository import disconnect_user


class ModerationService:
    def __init__(self):
        self.bans: Dict[str, Ban] = {}
        self.restrictions: Dict[str, List[Restriction]] = {}
        self.warnings: Dict[str, List[Warning]] = {}
        self.moderator_actions: List[ModeratorAction] = []
        self.auto_mod_rules = self._init_auto_mod_rules()

    def _init_auto_mod_rules(self) -> Dict:
        """Инициализация правил автомодерации"""
        return {
            "toxic_words": ["список", "запрещенных", "слов"],  # Загружается из файла
            "spam_threshold": 5,  # Сообщений в минуту
            "afk_threshold": 120,  # Секунд без активности
            "report_threshold": {
                "hour": 3,  # 3 жалобы в час = предупреждение
                "day": 10,  # 10 жалоб в день = временный бан
                "week": 20,  # 20 жалоб в неделю = проверка модератором
            },
            "linguistic_threshold": 2.0,  # Минимальный рейтинг языка
            "auto_ban_duration": {
                BanReason.TOXIC_BEHAVIOR: 24,  # часов
                BanReason.HATE_SPEECH: 168,  # 7 дней
                BanReason.SPAM: 2,
                BanReason.AFK_ABUSE: 1,
                BanReason.POOR_LANGUAGE: 0,  # Только ограничения
            },
        }

    async def ban_user(
        self,
        user_id: str,
        duration_hours: Optional[int] = None,
        reason: BanReason = BanReason.TOXIC_BEHAVIOR,
        issued_by: str = "system",
        evidence: Optional[str] = None,
    ) -> Ban:
        """Забанить пользователя"""
        ban_id = self._generate_id()

        ban = Ban(
            ban_id=ban_id,
            user_id=user_id,
            type=BanType.PERMANENT if duration_hours is None else BanType.TEMPORARY,
            reason=reason,
            issued_by=issued_by,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=duration_hours)
            if duration_hours
            else None,
            evidence=evidence,
        )

        self.bans[user_id] = ban

        # Логируем действие
        await self._log_moderator_action(
            moderator_id=issued_by,
            action_type="ban",
            target_user=user_id,
            details={
                "reason": reason.value,
                "duration": duration_hours,
                "evidence": evidence,
            },
        )

        # Отключаем активные сессии
        await self._kick_user_from_games(user_id)

        # Уведомляем пользователя
        await self._notify_user_ban(user_id, ban)

        return ban

    async def unban_user(self, user_id: str, moderator_id: str, reason: str) -> bool:
        """Разбанить пользователя"""
        if user_id not in self.bans:
            return False

        del self.bans[user_id]

        await self._log_moderator_action(
            moderator_id=moderator_id,
            action_type="unban",
            target_user=user_id,
            details={"reason": reason},
        )

        return True

    async def restrict_user(
        self,
        user_id: str,
        restriction_type: RestrictionType,
        hours: int,
        reason: str,
        value: Optional[int] = None,
    ) -> Restriction:
        """Наложить ограничение на пользователя"""
        restriction = Restriction(
            restriction_id=self._generate_id(),
            user_id=user_id,
            type=restriction_type,
            expires_at=datetime.utcnow() + timedelta(hours=hours),
            reason=reason,
            value=value,
        )

        if user_id not in self.restrictions:
            self.restrictions[user_id] = []

        self.restrictions[user_id].append(restriction)

        # Применяем ограничение немедленно
        await self._apply_restriction(user_id, restriction)

        return restriction

    async def warn_user(self, user_id: str, reason: str, severity: int = 1) -> Warning:
        """Выдать предупреждение пользователю"""
        warning = Warning(
            warning_id=self._generate_id(),
            user_id=user_id,
            reason=reason,
            severity=severity,
            issued_at=datetime.utcnow(),
        )

        if user_id not in self.warnings:
            self.warnings[user_id] = []

        self.warnings[user_id].append(warning)

        # Проверяем накопление предупреждений
        total_severity = sum(
            w.severity for w in self.warnings[user_id][-5:]
        )  # Последние 5

        if total_severity >= 5:
            # Автоматический бан при накоплении предупреждений
            await self.ban_user(
                user_id=user_id,
                duration_hours=24,
                reason=BanReason.TOXIC_BEHAVIOR,
                issued_by="system",
                evidence=f"Accumulated {total_severity} warning points",
            )

        return warning

    async def check_user_status(self, user_id: str) -> Dict:
        """Проверка статуса пользователя"""
        status = {
            "banned": False,
            "ban_details": None,
            "restrictions": [],
            "warnings": [],
            "can_play": True,
            "can_voice": True,
            "can_chat": True,
            "can_send_gifts": True,
        }

        # Проверяем бан
        if user_id in self.bans:
            ban = self.bans[user_id]
            if ban.expires_at is None or ban.expires_at > datetime.utcnow():
                status["banned"] = True
                status["ban_details"] = ban
                status["can_play"] = False
                status["can_voice"] = False
                status["can_chat"] = False
                status["can_send_gifts"] = False
                return status
            else:
                # Бан истек, удаляем
                del self.bans[user_id]

        # Проверяем ограничения
        if user_id in self.restrictions:
            active_restrictions = []
            for restriction in self.restrictions[user_id]:
                if restriction.expires_at > datetime.utcnow():
                    active_restrictions.append(restriction)

                    # Применяем ограничения
                    if restriction.type == RestrictionType.MUTE_VOICE:
                        status["can_voice"] = False
                    elif restriction.type == RestrictionType.MUTE_TEXT:
                        status["can_chat"] = False
                    elif restriction.type == RestrictionType.NO_GIFTS:
                        status["can_send_gifts"] = False
                    elif restriction.type == RestrictionType.NO_RANKED:
                        status["can_play"] = False  # Только для рейтинговых

            status["restrictions"] = active_restrictions
            self.restrictions[user_id] = active_restrictions  # Очищаем истекшие

        # Добавляем предупреждения
        if user_id in self.warnings:
            status["warnings"] = self.warnings[user_id][-5:]  # Последние 5

        return status

    async def auto_moderate_message(
        self, user_id: str, message: str, context: Dict
    ) -> Optional[ModeratorAction]:
        """Автоматическая модерация сообщения"""
        # Проверка на токсичность
        if self._contains_toxic_words(message):
            await self.warn_user(user_id, "Toxic language detected", severity=2)
            return ModeratorAction(
                action_id=self._generate_id(),
                moderator_id="auto_mod",
                action_type="message_blocked",
                target_user=user_id,
                timestamp=datetime.utcnow(),
                details={"reason": "toxic_content", "message": message[:50]},
            )

        # Проверка на спам
        if await self._is_spamming(user_id):
            await self.restrict_user(
                user_id=user_id,
                restriction_type=RestrictionType.SLOW_MODE,
                hours=1,
                reason="spam_detected",
                value=30,  # 30 секунд между сообщениями
            )
            return ModeratorAction(
                action_id=self._generate_id(),
                moderator_id="auto_mod",
                action_type="slow_mode_applied",
                target_user=user_id,
                timestamp=datetime.utcnow(),
                details={"duration": 30},
            )

        return None

    async def process_game_behavior(
        self, user_id: str, game_id: str, behavior_data: Dict
    ):
        """Обработка поведения в игре"""
        # AFK проверка
        if behavior_data.get("afk_time", 0) > self.auto_mod_rules["afk_threshold"]:
            await self.warn_user(user_id, f"AFK in game {game_id}")

            # Если часто AFK - бан
            recent_afk_warnings = [
                w
                for w in self.warnings.get(user_id, [])
                if "AFK" in w.reason and (datetime.utcnow() - w.issued_at).days < 7
            ]

            if len(recent_afk_warnings) >= 3:
                await self.ban_user(
                    user_id=user_id,
                    duration_hours=2,
                    reason=BanReason.AFK_ABUSE,
                    evidence=f"Multiple AFK violations in games",
                )

        # Проверка лингвистического рейтинга
        if (
            behavior_data.get("linguistic_rating", 5.0)
            < self.auto_mod_rules["linguistic_threshold"]
        ):
            await self.restrict_user(
                user_id=user_id,
                restriction_type=RestrictionType.NO_RANKED,
                hours=24,
                reason="poor_language_skills",
            )

    async def appeal_ban(self, user_id: str, appeal_text: str) -> str:
        """Подача апелляции на бан"""
        if user_id not in self.bans:
            return "no_ban_found"

        ban = self.bans[user_id]
        ban.appeal_status = "pending"
        ban.notes = appeal_text

        # Уведомляем модераторов
        await self._notify_moderators_appeal(user_id, ban, appeal_text)

        return "appeal_submitted"

    async def review_appeal(
        self, user_id: str, moderator_id: str, approved: bool, reason: str
    ) -> bool:
        """Рассмотрение апелляции"""
        if user_id not in self.bans:
            return False

        ban = self.bans[user_id]
        ban.appeal_status = "approved" if approved else "rejected"

        if approved:
            await self.unban_user(user_id, moderator_id, f"Appeal approved: {reason}")
        else:
            ban.notes += f"\nAppeal rejected by {moderator_id}: {reason}"

        return True

    def _contains_toxic_words(self, message: str) -> bool:
        """Проверка на токсичные слова"""
        message_lower = message.lower()
        for word in self.auto_mod_rules["toxic_words"]:
            if word in message_lower:
                return True
        return False

    async def _is_spamming(self, user_id: str) -> bool:
        """Проверка на спам"""
        # Здесь должна быть проверка частоты сообщений из Redis
        # Упрощенная версия:
        from app.core.redis import RedisManager

        redis = RedisManager.get_client()

        key = f"msg_count:{user_id}"
        count = await redis.incr(key)
        await redis.expire(key, 60)  # Счетчик на минуту

        return count > self.auto_mod_rules["spam_threshold"]

    async def _apply_restriction(self, user_id: str, restriction: Restriction):
        """Применение ограничения"""
        # Уведомляем соответствующие сервисы
        if restriction.type == RestrictionType.MUTE_VOICE:
            from app.domains.voice.service import mute_user_globally

            await mute_user_globally(user_id, True)

        # Уведомляем пользователя
        from app.core.websocket_manager import websocket_manager

        await websocket_manager.send_to_user(
            user_id,
            {
                "event": "restriction_applied",
                "type": restriction.type.value,
                "expires_at": restriction.expires_at.isoformat(),
                "reason": restriction.reason,
            },
        )

    async def _kick_user_from_games(self, user_id: str):
        """Выкинуть пользователя из активных игр"""

        # Находим активные игры пользователя
        await kick_player(user_id)
        await disconnect_user(user_id)
        pass

    async def _notify_user_ban(self, user_id: str, ban: Ban):
        """Уведомление пользователя о бане"""
        from app.core.websocket_manager import websocket_manager

        await websocket_manager.send_to_user(
            user_id,
            {
                "event": "banned",
                "reason": ban.reason.value,
                "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
                "appeal_available": True,
            },
        )

    async def _notify_moderators_appeal(self, user_id: str, ban: Ban, appeal_text: str):
        """Уведомление модераторов об апелляции"""
        # Здесь должна быть отправка в канал модераторов
        pass

    async def _log_moderator_action(
        self, moderator_id: str, action_type: str, target_user: str, details: Dict
    ):
        """Логирование действий модератора"""
        action = ModeratorAction(
            action_id=self._generate_id(),
            moderator_id=moderator_id,
            action_type=action_type,
            target_user=target_user,
            timestamp=datetime.utcnow(),
            details=details,
        )

        self.moderator_actions.append(action)

        # Сохраняем в БД для аудита
        from app.domains.moderation.repository import save_moderator_action

        await save_moderator_action(action)

    def _generate_id(self) -> str:
        import uuid

        return str(uuid.uuid4())


# Глобальный экземпляр
moderation_service = ModerationService()
