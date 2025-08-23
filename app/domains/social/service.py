# app/domains/social/service.py
"""
Complete Social Service with all friendship, blocking, and interaction features
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import json

from app.domains.social.entities import (
    Gift,
    GiftType,
    InteractionType,
    SocialInteraction,
    UserSocialStats,
)
from app.core.redis import RedisManager
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


class FriendshipStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    BLOCKED = "blocked"


class NotificationType(str, Enum):
    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPTED = "friend_accepted"
    GIFT_RECEIVED = "gift_received"
    LINGUISTIC_RATING = "linguistic_rating"
    GAME_INVITE = "game_invite"


class SocialService:
    """Complete social service with all features"""

    def __init__(self):
        self.interactions: List[SocialInteraction] = []
        self.user_stats: Dict[str, UserSocialStats] = {}
        self.gifts_catalog = self._init_gifts_catalog()
        self.redis_client = RedisManager.get_client()

        # Cache configuration
        self.cache_ttl = 300  # 5 minutes
        self.max_friends = 200
        self.max_blocks = 100
        self.report_cooldown = 60  # seconds between reports

    def _init_gifts_catalog(self) -> Dict[GiftType, Gift]:
        """Initialize gift catalog with all gift types"""
        return {
            GiftType.ROSE: Gift(
                gift_id="gift_rose",
                type=GiftType.ROSE,
                price_mafia=10,
                icon_url="/assets/gifts/rose.png",
                animation_url="/assets/gifts/rose_animation.json",
            ),
            GiftType.CHAMPAGNE: Gift(
                gift_id="gift_champagne",
                type=GiftType.CHAMPAGNE,
                price_mafia=50,
                icon_url="/assets/gifts/champagne.png",
                animation_url="/assets/gifts/champagne_animation.json",
            ),
            GiftType.DIAMOND: Gift(
                gift_id="gift_diamond",
                type=GiftType.DIAMOND,
                price_mafia=100,
                icon_url="/assets/gifts/diamond.png",
                animation_url="/assets/gifts/diamond_animation.json",
            ),
            GiftType.CROWN: Gift(
                gift_id="gift_crown",
                type=GiftType.CROWN,
                price_mafia=500,
                icon_url="/assets/gifts/crown.png",
                animation_url="/assets/gifts/crown_animation.json",
                is_limited=True,
            ),
            GiftType.EXCLUSIVE: Gift(
                gift_id="gift_exclusive",
                type=GiftType.EXCLUSIVE,
                price_mafia=1000,
                icon_url="/assets/gifts/exclusive.png",
                animation_url="/assets/gifts/exclusive_animation.json",
                is_limited=True,
                available_until=datetime.utcnow() + timedelta(days=30)
            ),
        }

    async def add_friend(
            self,
            user_id: str,
            friend_id: str,
            message: Optional[str] = None
    ) -> Dict:
        """Send friend request"""
        try:
            # Check if users are the same
            if user_id == friend_id:
                return {"success": False, "error": "Cannot add yourself as friend"}

            # Check if already friends
            friendship_status = await self._get_friendship_status(user_id, friend_id)
            if friendship_status == FriendshipStatus.ACCEPTED:
                return {"success": False, "error": "Already friends"}
            elif friendship_status == FriendshipStatus.PENDING:
                return {"success": False, "error": "Friend request already sent"}
            elif friendship_status == FriendshipStatus.BLOCKED:
                return {"success": False, "error": "User is blocked"}

            # Check friend limit
            friends_count = await self._get_friends_count(user_id)
            if friends_count >= self.max_friends:
                return {"success": False, "error": f"Friend limit reached ({self.max_friends})"}

            # Check if target user blocked sender
            if await self._is_blocked_by(user_id, friend_id):
                return {"success": False, "error": "Cannot send friend request"}

            # Create friend request
            from app.domains.social.repository import create_friendship

            friendship_id = await create_friendship({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "friend_id": friend_id,
                "status": FriendshipStatus.PENDING,
                "initiated_by": user_id,
                "message": message
            })

            # Record interaction
            interaction = SocialInteraction(
                interaction_id=str(uuid.uuid4()),
                from_user=user_id,
                to_user=friend_id,
                type=InteractionType.FRIEND_REQUEST,
                game_id=None,
                timestamp=datetime.utcnow(),
                data={"message": message}
            )

            await self._save_interaction(interaction)

            # Send notification
            await self._send_notification(
                friend_id,
                NotificationType.FRIEND_REQUEST,
                {
                    "from_user": user_id,
                    "message": message,
                    "friendship_id": friendship_id
                }
            )

            # Update stats
            self._update_stats(user_id, "friend_requests_sent", 1)

            return {
                "success": True,
                "friendship_id": friendship_id,
                "status": FriendshipStatus.PENDING
            }

        except Exception as e:
            logger.error(f"Failed to add friend: {e}")
            return {"success": False, "error": "Failed to send friend request"}

    async def accept_friend_request(
            self,
            user_id: str,
            friendship_id: str
    ) -> bool:
        """Accept a friend request"""
        try:
            from app.domains.social.repository import get_friendship, update_friendship_status

            friendship = await get_friendship(friendship_id)
            if not friendship:
                return False

            # Verify the request is for this user
            if friendship.friend_id != user_id:
                return False

            # Check status
            if friendship.status != FriendshipStatus.PENDING:
                return False

            # Update status
            await update_friendship_status(friendship_id, FriendshipStatus.ACCEPTED)

            # Create reverse friendship for bidirectional relationship
            await create_friendship({
                "id": str(uuid.uuid4()),
                "user_id": friendship.friend_id,
                "friend_id": friendship.user_id,
                "status": FriendshipStatus.ACCEPTED,
                "initiated_by": friendship.initiated_by
            })

            # Update stats
            self._update_stats(user_id, "friends_count", 1)
            self._update_stats(friendship.user_id, "friends_count", 1)

            # Send notification
            await self._send_notification(
                friendship.user_id,
                NotificationType.FRIEND_ACCEPTED,
                {"friend_id": user_id}
            )

            # Clear cache
            await self._clear_friends_cache(user_id)
            await self._clear_friends_cache(friendship.user_id)

            return True

        except Exception as e:
            logger.error(f"Failed to accept friend request: {e}")
            return False

    async def remove_friend(self, user_id: str, friend_id: str) -> bool:
        """Remove a friend"""
        try:
            from app.domains.social.repository import delete_friendship

            # Delete both directions
            deleted = await delete_friendship(user_id, friend_id)
            deleted += await delete_friendship(friend_id, user_id)

            if deleted > 0:
                # Update stats
                self._update_stats(user_id, "friends_count", -1)
                self._update_stats(friend_id, "friends_count", -1)

                # Clear cache
                await self._clear_friends_cache(user_id)
                await self._clear_friends_cache(friend_id)

                return True

            return False

        except Exception as e:
            logger.error(f"Failed to remove friend: {e}")
            return False

    async def block_user(
            self,
            user_id: str,
            blocked_user_id: str,
            reason: Optional[str] = None
    ) -> bool:
        """Block a user"""
        try:
            # Check if already blocked
            if await self._is_blocked(user_id, blocked_user_id):
                return True

            # Check block limit
            blocks_count = await self._get_blocks_count(user_id)
            if blocks_count >= self.max_blocks:
                return False

            # Remove friendship if exists
            await self.remove_friend(user_id, blocked_user_id)

            # Create block entry
            from app.domains.social.repository import create_block

            await create_block({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "blocked_user_id": blocked_user_id,
                "reason": reason,
                "created_at": datetime.utcnow()
            })

            # Update muted players list in user profile
            from app.domains.auth.repository import add_muted_player
            await add_muted_player(user_id, blocked_user_id)

            # Clear cache
            await self._clear_blocks_cache(user_id)

            return True

        except Exception as e:
            logger.error(f"Failed to block user: {e}")
            return False

    async def unblock_user(self, user_id: str, blocked_user_id: str) -> bool:
        """Unblock a user"""
        try:
            from app.domains.social.repository import delete_block
            from app.domains.auth.repository import remove_muted_player

            deleted = await delete_block(user_id, blocked_user_id)

            if deleted:
                await remove_muted_player(user_id, blocked_user_id)
                await self._clear_blocks_cache(user_id)
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to unblock user: {e}")
            return False

    async def get_friends_list(
            self,
            user_id: str,
            include_pending: bool = False,
            limit: int = 100,
            offset: int = 0
    ) -> List[Dict]:
        """Get user's friends list"""
        try:
            # Check cache first
            cache_key = f"friends:{user_id}:{include_pending}"
            cached = await self.redis_client.get(cache_key)
            if cached:
                import json
                friends = json.loads(cached)
                return friends[offset:offset + limit]

            from app.domains.social.repository import get_user_friends

            friends = await get_user_friends(
                user_id,
                include_pending=include_pending
            )

            # Format friend data
            friend_list = []
            for friendship in friends:
                friend_data = {
                    "friendship_id": friendship.id,
                    "friend_id": friendship.friend_id,
                    "status": friendship.status,
                    "created_at": friendship.created_at.isoformat()
                }

                # Get friend profile
                from app.domains.auth.repository import get_user_by_id
                friend = await get_user_by_id(friendship.friend_id)

                if friend:
                    friend_data.update({
                        "username": friend.username or f"User_{friend.telegram_id}",
                        "rating": friend.rating,
                        "is_online": await self._is_user_online(friendship.friend_id),
                        "is_in_game": await self._is_user_in_game(friendship.friend_id),
                    })

                friend_list.append(friend_data)

            # Cache result
            await self.redis_client.set(
                cache_key,
                json.dumps(friend_list),
                ex=self.cache_ttl
            )

            return friend_list[offset:offset + limit]

        except Exception as e:
            logger.error(f"Failed to get friends list: {e}")
            return []

    async def get_blocked_users(self, user_id: str) -> List[Dict]:
        """Get list of blocked users"""
        try:
            from app.domains.social.repository import get_user_blocks

            blocks = await get_user_blocks(user_id)

            blocked_list = []
            for block in blocks:
                blocked_list.append({
                    "blocked_user_id": block.blocked_user_id,
                    "reason": block.reason,
                    "blocked_at": block.created_at.isoformat()
                })

            return blocked_list

        except Exception as e:
            logger.error(f"Failed to get blocked users: {e}")
            return []

    async def send_gift(
            self,
            from_user: str,
            to_user: str,
            gift_type: GiftType,
            game_id: Optional[str] = None,
            message: Optional[str] = None
    ) -> bool:
        """Send a gift to another user"""
        try:
            # Check if users are friends (optional requirement)
            # friendship_status = await self._get_friendship_status(from_user, to_user)
            # if friendship_status != FriendshipStatus.ACCEPTED:
            #     return False

            # Check if blocked
            if await self._is_blocked(to_user, from_user):
                return False

            gift = self.gifts_catalog.get(gift_type)
            if not gift:
                return False

            # Check if limited gift is still available
            if gift.is_limited and gift.available_until:
                if datetime.utcnow() > gift.available_until:
                    return False

            # Process payment
            from app.domains.economy.service import economy_service

            if not await economy_service.spend_tokens(
                    from_user, gift.price_mafia, f"gift_{gift_type.value}"
            ):
                return False

            # Give recipient 50% of gift value
            await economy_service.add_tokens(
                to_user, gift.price_mafia // 2, "gift_received"
            )

            # Record interaction
            interaction = SocialInteraction(
                interaction_id=str(uuid.uuid4()),
                from_user=from_user,
                to_user=to_user,
                type=InteractionType.GIFT,
                game_id=game_id,
                timestamp=datetime.utcnow(),
                data={
                    "gift_type": gift_type.value,
                    "price": gift.price_mafia,
                    "message": message
                }
            )

            await self._save_interaction(interaction)

            # Update stats
            self._update_stats(to_user, "gifts_received", 1)
            self._update_stats(from_user, "gifts_sent", 1)

            # Send notification
            await self._send_notification(
                to_user,
                NotificationType.GIFT_RECEIVED,
                {
                    "from_user": from_user,
                    "gift_type": gift_type.value,
                    "message": message,
                    "game_id": game_id
                }
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send gift: {e}")
            return False

    async def report_player(
            self,
            reporter: str,
            reported: str,
            reason: str,
            game_id: str,
            evidence: Optional[str] = None
    ) -> str:
        """Report a player for misconduct"""
        try:
            # Check cooldown
            cooldown_key = f"report_cooldown:{reporter}:{reported}"
            if await self.redis_client.exists(cooldown_key):
                raise ValueError("Please wait before reporting this player again")

            # Check if reporter is in the same game
            from app.domains.game.repository import get_player
            reporter_player = await get_player(game_id, reporter)
            reported_player = await get_player(game_id, reported)

            if not reporter_player or not reported_player:
                raise ValueError("Both players must be in the same game")

            report_id = str(uuid.uuid4())

            # Save report
            from app.domains.social.repository import create_report

            await create_report({
                "id": report_id,
                "reporter_id": reporter,
                "reported_id": reported,
                "game_id": game_id,
                "reason": reason,
                "evidence": evidence,
                "status": "pending",
                "created_at": datetime.utcnow()
            })

            # Set cooldown
            await self.redis_client.set(
                cooldown_key,
                "1",
                ex=self.report_cooldown
            )

            # Record interaction
            interaction = SocialInteraction(
                interaction_id=report_id,
                from_user=reporter,
                to_user=reported,
                type=InteractionType.REPORT,
                game_id=game_id,
                timestamp=datetime.utcnow(),
                data={"reason": reason, "evidence": evidence}
            )

            await self._save_interaction(interaction)

            # Auto-moderation check
            await self._auto_moderate_report(report_id, reported, reason)

            return report_id

        except Exception as e:
            logger.error(f"Failed to report player: {e}")
            raise

    async def rate_linguistic_ability(
            self,
            rater: str,
            rated: str,
            language: str,
            score: int,
            game_id: str
    ) -> bool:
        """Rate a player's linguistic abilities"""
        try:
            if score < 1 or score > 5:
                return False

            # Check if both players were in the same game
            from app.domains.game.repository import get_player
            rater_player = await get_player(game_id, rater)
            rated_player = await get_player(game_id, rated)

            if not rater_player or not rated_player:
                return False

            # Check if already rated in this game
            rating_key = f"linguistic_rating:{game_id}:{rater}:{rated}"
            if await self.redis_client.exists(rating_key):
                return False

            # Record interaction
            interaction = SocialInteraction(
                interaction_id=str(uuid.uuid4()),
                from_user=rater,
                to_user=rated,
                type=InteractionType.LINGUISTIC_RATE,
                game_id=game_id,
                timestamp=datetime.utcnow(),
                data={"language": language, "score": score}
            )

            await self._save_interaction(interaction)

            # Update linguistic rating
            from app.domains.auth.repository import update_linguistic_rating
            await update_linguistic_rating(rated, language, score)

            # Mark as rated
            await self.redis_client.set(rating_key, "1", ex=86400)  # 24 hours

            # Reward for high rating
            if score >= 4:
                from app.domains.economy.service import economy_service
                await economy_service.add_tokens(rated, 5, "linguistic_bonus")

            # Send notification
            await self._send_notification(
                rated,
                NotificationType.LINGUISTIC_RATING,
                {
                    "from_user": rater,
                    "language": language,
                    "score": score,
                    "game_id": game_id
                }
            )

            return True

        except Exception as e:
            logger.error(f"Failed to rate linguistic ability: {e}")
            return False

    # Helper methods

    async def _get_friendship_status(
            self,
            user_id: str,
            friend_id: str
    ) -> Optional[FriendshipStatus]:
        """Get friendship status between two users"""
        from app.domains.social.repository import get_friendship_between_users

        friendship = await get_friendship_between_users(user_id, friend_id)
        if friendship:
            return FriendshipStatus(friendship.status)
        return None

    async def _get_friends_count(self, user_id: str) -> int:
        """Get number of friends"""
        from app.domains.social.repository import count_user_friends
        return await count_user_friends(user_id)

    async def _get_blocks_count(self, user_id: str) -> int:
        """Get number of blocked users"""
        from app.domains.social.repository import count_user_blocks
        return await count_user_blocks(user_id)

    async def _is_blocked(self, user_id: str, blocked_user_id: str) -> bool:
        """Check if user blocked another user"""
        from app.domains.social.repository import is_user_blocked
        return await is_user_blocked(user_id, blocked_user_id)

    async def _is_blocked_by(self, user_id: str, by_user_id: str) -> bool:
        """Check if user is blocked by another user"""
        return await self._is_blocked(by_user_id, user_id)

    async def _is_user_online(self, user_id: str) -> bool:
        """Check if user is online"""
        from app.core.websocket_manager import websocket_manager
        return user_id in websocket_manager.user_connections

    async def _is_user_in_game(self, user_id: str) -> bool:
        """Check if user is in an active game"""
        from app.domains.game.repository import get_player_active_game
        game_id = await get_player_active_game(user_id)
        return game_id is not None

    async def _clear_friends_cache(self, user_id: str):
        """Clear friends cache for user"""
        pattern = f"friends:{user_id}:*"
        async for key in self.redis_client.scan_iter(match=pattern):
            await self.redis_client.delete(key)

    async def _clear_blocks_cache(self, user_id: str):
        """Clear blocks cache for user"""
        pattern = f"blocks:{user_id}:*"
        async for key in self.redis_client.scan_iter(match=pattern):
            await self.redis_client.delete(key)

    async def _save_interaction(self, interaction: SocialInteraction):
        """Save interaction to database"""
        from app.domains.social.repository import save_interaction

        await save_interaction({
            "interaction_id": interaction.interaction_id,
            "from_user": interaction.from_user,
            "to_user": interaction.to_user,
            "type": interaction.type.value,
            "game_id": interaction.game_id,
            "timestamp": interaction.timestamp,
            "data": interaction.data
        })

        self.interactions.append(interaction)

    async def _send_notification(
            self,
            user_id: str,
            notification_type: NotificationType,
            data: Dict
    ):
        """Send notification to user"""
        from app.core.websocket_manager import websocket_manager, MessagePriority

        await websocket_manager.send_to_user(
            user_id,
            {
                "type": "notification",
                "notification_type": notification_type.value,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            },
            priority=MessagePriority.HIGH
        )

    async def _auto_moderate_report(self, report_id: str, user_id: str, reason: str):
        """Auto-moderate based on reports"""
        # Get recent reports
        recent_reports = await self._get_recent_reports(user_id, hours=24)

        # Auto-action thresholds
        if len(recent_reports) >= 5:
            from app.domains.moderation.service import moderation_service
            from app.domains.moderation.entities import BanReason, RestrictionType

            if reason in ["toxic_behavior", "hate_speech"]:
                await moderation_service.ban_user(
                    user_id=user_id,
                    duration_hours=24,
                    reason=BanReason.TOXIC_BEHAVIOR,
                    issued_by="auto_moderator",
                    evidence=f"Auto-ban: {len(recent_reports)} reports in 24h"
                )
            elif reason == "bad_language_skills":
                await moderation_service.restrict_user(
                    user_id=user_id,
                    restriction_type=RestrictionType.NO_RANKED,
                    hours=12,
                    reason="Multiple reports for poor language skills"
                )

    async def _get_recent_reports(self, user_id: str, hours: int) -> List:
        """Get recent reports for a user"""
        from app.domains.social.repository import get_recent_reports
        return await get_recent_reports(user_id, hours)

    def _update_stats(self, user_id: str, stat: str, value: int):
        """Update user statistics"""
        if user_id not in self.user_stats:
            self.user_stats[user_id] = UserSocialStats(user_id=user_id)

        current = getattr(self.user_stats[user_id], stat, 0)
        setattr(self.user_stats[user_id], stat, current + value)

        # Also update in database
        from app.domains.social.repository import update_user_stats
        asyncio.create_task(update_user_stats(user_id, stat, value))

    def _generate_id(self) -> str:
        """Generate unique ID"""
        return str(uuid.uuid4())


# Global instance
social_service = SocialService()