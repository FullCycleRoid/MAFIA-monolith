# app/domains/game/repository.py
"""
Complete Game Repository with all database operations
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import and_, select, update, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.domains.game.models import Game, Player, Action, GameStats
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


async def get_players(game_id: str, role: str = None) -> List[Player]:
    """Get players in a game, optionally filtered by role"""
    async with get_db() as db:
        query = select(Player).filter(Player.game_id == game_id)
        if role:
            query = query.filter(Player.role == role)
        result = await db.execute(query)
        return result.scalars().all()


async def get_alive_players(game_id: str) -> List[Player]:
    """Get all alive players in a game"""
    async with get_db() as db:
        result = await db.execute(
            select(Player).filter(
                and_(
                    Player.game_id == game_id,
                    Player.alive == True
                )
            )
        )
        return result.scalars().all()


async def create_game_from_lobby(
        players: List["PlayerProfile"],
        settings: "LobbySettings"
) -> str:
    """Create a new game from lobby"""
    game_id = str(uuid.uuid4())

    async with get_db() as db:
        # Create game
        game = Game(
            id=game_id,
            status="starting",
            settings=settings.__dict__,
            phase="lobby",
            day_count=0,
            started_at=datetime.utcnow()
        )
        db.add(game)

        # Add players
        for profile in players:
            player = Player(
                id=str(uuid.uuid4()),
                game_id=game_id,
                user_id=profile.user_id,
                role="unassigned",
                alive=True,
                stats={}
            )
            db.add(player)

        await db.commit()
        logger.info(f"Created game {game_id} with {len(players)} players")

    return game_id


async def update_player_role(game_id: str, user_id: str, role: str):
    """Update player's role in game"""
    async with get_db() as db:
        await db.execute(
            update(Player)
            .where(and_(
                Player.game_id == game_id,
                Player.user_id == user_id
            ))
            .values(role=role)
        )
        await db.commit()


async def update_game_phase(game_id: str, phase: str):
    """Update game phase"""
    async with get_db() as db:
        await db.execute(
            update(Game)
            .where(Game.id == game_id)
            .values(
                phase=phase,
                updated_at=datetime.utcnow()
            )
        )

        # Increment day count if moving to day phase
        if phase == "day_discussion":
            await db.execute(
                update(Game)
                .where(Game.id == game_id)
                .values(day_count=Game.day_count + 1)
            )

        await db.commit()


async def save_action(
        game_id: str,
        player_id: str,
        action_type: str,
        target_id: str,
        phase: str
):
    """Save player action"""
    async with get_db() as db:
        # Get current day from game
        game_result = await db.execute(
            select(Game.day_count).filter(Game.id == game_id)
        )
        day = game_result.scalar_one_or_none() or 0

        action = Action(
            id=str(uuid.uuid4()),
            game_id=game_id,
            player_id=player_id,
            action_type=action_type,
            target_id=target_id,
            phase=phase,
            day=day
        )
        db.add(action)
        await db.commit()


async def eliminate_player(game_id: str, user_id: str, reason: str):
    """Mark player as eliminated"""
    async with get_db() as db:
        # Get current day
        game_result = await db.execute(
            select(Game.day_count).filter(Game.id == game_id)
        )
        day = game_result.scalar_one_or_none() or 0

        # Update player
        await db.execute(
            update(Player)
            .where(and_(
                Player.game_id == game_id,
                Player.user_id == user_id
            ))
            .values(
                alive=False,
                death_reason=reason,
                death_day=day,
                updated_at=datetime.utcnow()
            )
        )
        await db.commit()
        logger.info(f"Player {user_id} eliminated in game {game_id}: {reason}")


async def end_game(game_id: str, winner_team: str, results: Dict):
    """End the game and save results"""
    async with get_db() as db:
        # Update game status
        await db.execute(
            update(Game)
            .where(Game.id == game_id)
            .values(
                status="ended",
                phase="game_ended",
                winner_team=winner_team,
                ended_at=datetime.utcnow()
            )
        )

        # Calculate game duration
        game = await db.execute(
            select(Game).filter(Game.id == game_id)
        )
        game_obj = game.scalar_one()

        duration = (game_obj.ended_at - game_obj.started_at).total_seconds()

        # Save game statistics
        stats = GameStats(
            id=str(uuid.uuid4()),
            game_id=game_id,
            duration_seconds=int(duration),
            total_players=len(results),
            mafia_count=sum(1 for r in results.values() if r.get("role") == "mafia"),
            stats={
                "winner_team": winner_team,
                "final_day": game_obj.day_count,
                "player_results": results
            }
        )
        db.add(stats)

        # Update player statistics
        from app.domains.auth.models import User

        for player_id, result in results.items():
            # Update user stats
            user = await db.execute(
                select(User).filter(User.id == player_id)
            )
            user_obj = user.scalar_one_or_none()

            if user_obj:
                user_obj.games_played += 1
                if result.get("won"):
                    user_obj.games_won += 1
                user_obj.win_rate = user_obj.games_won / user_obj.games_played

                # Update rating based on win/loss
                rating_change = 25 if result.get("won") else -10
                if result.get("survived"):
                    rating_change += 5
                user_obj.rating = max(0, user_obj.rating + rating_change)

        await db.commit()
        logger.info(f"Game {game_id} ended. Winner: {winner_team}")


async def kick_player(user_id: str):
    """Kick player from all active games"""
    async with get_db() as db:
        # Find active games with this player
        result = await db.execute(
            select(Player).filter(
                and_(
                    Player.user_id == user_id,
                    Player.alive == True
                )
            )
        )
        active_players = result.scalars().all()

        # Mark as kicked
        for player in active_players:
            player.alive = False
            player.death_reason = "kicked"
            player.kicked_at = datetime.utcnow()

        await db.commit()


async def get_game(game_id: str) -> Optional[Game]:
    """Get game by ID"""
    async with get_db() as db:
        result = await db.execute(
            select(Game).filter(Game.id == game_id)
        )
        return result.scalar_one_or_none()


async def get_player(game_id: str, user_id: str) -> Optional[Player]:
    """Get specific player in game"""
    async with get_db() as db:
        result = await db.execute(
            select(Player).filter(
                and_(
                    Player.game_id == game_id,
                    Player.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()


async def get_game_actions(game_id: str, day: Optional[int] = None) -> List[Action]:
    """Get actions for a game, optionally filtered by day"""
    async with get_db() as db:
        query = select(Action).filter(Action.game_id == game_id)
        if day is not None:
            query = query.filter(Action.day == day)
        query = query.order_by(Action.created_at)

        result = await db.execute(query)
        return result.scalars().all()


async def get_active_games() -> List[Game]:
    """Get all active games"""
    async with get_db() as db:
        result = await db.execute(
            select(Game).filter(
                Game.status.in_(["starting", "in_progress"])
            )
        )
        return result.scalars().all()


async def get_player_active_game(user_id: str) -> Optional[str]:
    """Get active game ID for a player"""
    async with get_db() as db:
        result = await db.execute(
            select(Player.game_id).filter(
                and_(
                    Player.user_id == user_id,
                    Player.alive == True
                )
            )
        )
        game_id = result.scalar_one_or_none()

        if game_id:
            # Check if game is actually active
            game = await db.execute(
                select(Game).filter(
                    and_(
                        Game.id == game_id,
                        Game.status.in_(["starting", "in_progress"])
                    )
                )
            )
            if game.scalar_one_or_none():
                return game_id

        return None


async def update_player_stats(game_id: str, user_id: str, stats_update: Dict):
    """Update player statistics in game"""
    async with get_db() as db:
        player = await db.execute(
            select(Player).filter(
                and_(
                    Player.game_id == game_id,
                    Player.user_id == user_id
                )
            )
        )
        player_obj = player.scalar_one_or_none()

        if player_obj:
            current_stats = player_obj.stats or {}
            current_stats.update(stats_update)
            player_obj.stats = current_stats
            await db.commit()


async def get_game_stats(game_id: str) -> Optional[GameStats]:
    """Get statistics for a completed game"""
    async with get_db() as db:
        result = await db.execute(
            select(GameStats).filter(GameStats.game_id == game_id)
        )
        return result.scalar_one_or_none()


async def cleanup_old_games(days: int = 30):
    """Clean up old completed games"""
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    async with get_db() as db:
        # Find old games
        old_games = await db.execute(
            select(Game.id).filter(
                and_(
                    Game.status == "ended",
                    Game.ended_at < cutoff
                )
            )
        )
        game_ids = [g for g in old_games.scalars()]

        if game_ids:
            # Delete related data
            await db.execute(
                Action.__table__.delete().where(Action.game_id.in_(game_ids))
            )
            await db.execute(
                Player.__table__.delete().where(Player.game_id.in_(game_ids))
            )
            await db.execute(
                GameStats.__table__.delete().where(GameStats.game_id.in_(game_ids))
            )
            await db.execute(
                Game.__table__.delete().where(Game.id.in_(game_ids))
            )

            await db.commit()
            logger.info(f"Cleaned up {len(game_ids)} old games")


# Additional helper functions

async def get_game_summary(game_id: str) -> Dict:
    """Get comprehensive game summary"""
    async with get_db() as db:
        # Get game with all relations
        game = await db.execute(
            select(Game)
            .filter(Game.id == game_id)
            .options(selectinload(Game.players))  # Assuming relationship exists
        )
        game_obj = game.scalar_one_or_none()

        if not game_obj:
            return None

        # Get players
        players = await get_players(game_id)

        # Get stats
        stats = await get_game_stats(game_id)

        return {
            "game": {
                "id": game_obj.id,
                "status": game_obj.status,
                "phase": game_obj.phase,
                "day_count": game_obj.day_count,
                "started_at": game_obj.started_at,
                "ended_at": game_obj.ended_at,
                "winner_team": game_obj.winner_team,
            },
            "players": [
                {
                    "user_id": p.user_id,
                    "role": p.role,
                    "alive": p.alive,
                    "death_reason": p.death_reason,
                    "death_day": p.death_day,
                }
                for p in players
            ],
            "statistics": stats.stats if stats else None,
        }