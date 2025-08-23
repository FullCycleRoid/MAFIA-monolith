# app/domains/game/service.py
"""
Complete Game Service implementation with all missing methods
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

from app.core import event_bus
from app.domains.game import repository
from app.domains.game.logic import GameLogic, GamePhase, PhaseManager, Role
from app.shared.utils.logger import get_logger
from app.core.websocket_manager import websocket_manager

logger = get_logger(__name__)


class VotingType(str, Enum):
    DAY_ELIMINATION = "day_elimination"
    MAFIA_KILL = "mafia_kill"
    SKIP_VOTE = "skip_vote"


class GameService:
    def __init__(self):
        self.game_logic = GameLogic()
        self.phase_manager = PhaseManager(self.game_logic)
        self.active_games: Dict[str, Dict] = {}
        self.phase_timers: Dict[str, asyncio.Task] = {}
        self.voting_sessions: Dict[str, Dict] = {}

    async def create_game_from_lobby(
            self,
            players: List["PlayerProfile"],
            settings: "LobbySettings"
    ) -> str:
        """Create game from matchmaking lobby"""
        try:
            # Create game in database
            game_id = await repository.create_game_from_lobby(players, settings)

            # Initialize game state
            player_ids = [p.user_id for p in players]
            self.game_logic.create_game(game_id, player_ids)

            # Store active game info
            self.active_games[game_id] = {
                "players": {p.user_id: p for p in players},
                "settings": settings,
                "created_at": datetime.utcnow(),
                "phase": GamePhase.LOBBY,
                "votes": {},
                "actions": {},
            }

            # Start game after delay
            asyncio.create_task(self._start_game_countdown(game_id))

            logger.info(f"Game {game_id} created with {len(players)} players")
            return game_id

        except Exception as e:
            logger.error(f"Failed to create game: {e}")
            raise

    async def _start_game_countdown(self, game_id: str, countdown: int = 10):
        """Start countdown before game begins"""
        try:
            await asyncio.sleep(countdown)
            await self.start_game(game_id)
        except asyncio.CancelledError:
            logger.info(f"Game {game_id} countdown cancelled")

    async def start_game(self, game_id: str):
        """Start the game and assign roles"""
        if game_id not in self.active_games:
            raise ValueError(f"Game {game_id} not found")

        game = self.active_games[game_id]

        # Assign roles
        roles = self.game_logic.assign_roles(game_id)

        # Save roles to database
        for player_id, role in roles.items():
            await repository.update_player_role(game_id, player_id, role.value)

        # Notify players of their roles
        for player_id, role in roles.items():
            await websocket_manager.send_to_user(
                player_id,
                {
                    "event": "role_assigned",
                    "game_id": game_id,
                    "role": role.value,
                    "role_description": self._get_role_description(role)
                }
            )

        # Move to first day
        await self.advance_phase(game_id)

        # Start phase timer
        self._start_phase_timer(game_id)

    async def advance_phase(self, game_id: str) -> "GamePhaseChanged":
        """Advance to next game phase"""
        event = await self.phase_manager.advance_phase(game_id)

        # Update database
        await repository.update_game_phase(game_id, event.phase)

        # Handle phase-specific logic
        await self._handle_phase_transition(game_id, event.phase)

        # Publish event
        await event_bus.event_bus.publish("game:phase_changed", event.dict())

        # Update active game state
        if game_id in self.active_games:
            self.active_games[game_id]["phase"] = event.phase

        # Restart phase timer
        self._start_phase_timer(game_id)

        return event

    async def _handle_phase_transition(self, game_id: str, phase: str):
        """Handle specific logic for phase transitions"""
        if phase == GamePhase.DAY_VOTING.value:
            await self.start_voting_session(game_id, VotingType.DAY_ELIMINATION)

        elif phase == GamePhase.DAY_EXECUTION.value:
            await self.execute_day_voting_results(game_id)

        elif phase == GamePhase.NIGHT_RESULTS.value:
            await self.process_night_actions(game_id)

        elif phase == GamePhase.GAME_ENDED.value:
            await self.end_game(game_id)

    def _start_phase_timer(self, game_id: str):
        """Start timer for current phase"""
        # Cancel existing timer
        if game_id in self.phase_timers:
            self.phase_timers[game_id].cancel()

        # Get phase duration
        state = self.game_logic.game_states.get(game_id)
        if not state:
            return

        phase = state["phase"]
        duration = self._get_phase_duration(phase)

        # Create timer task
        self.phase_timers[game_id] = asyncio.create_task(
            self._phase_timer_task(game_id, duration)
        )

    async def _phase_timer_task(self, game_id: str, duration: int):
        """Timer task that advances phase after duration"""
        try:
            await asyncio.sleep(duration)
            await self.advance_phase(game_id)
        except asyncio.CancelledError:
            logger.debug(f"Phase timer cancelled for game {game_id}")

    def _get_phase_duration(self, phase: GamePhase) -> int:
        """Get duration for phase in seconds"""
        durations = {
            GamePhase.LOBBY: 30,
            GamePhase.ROLE_ASSIGNMENT: 10,
            GamePhase.DAY_DISCUSSION: 180,
            GamePhase.DAY_VOTING: 60,
            GamePhase.DAY_EXECUTION: 10,
            GamePhase.NIGHT_START: 5,
            GamePhase.NIGHT_MAFIA: 30,
            GamePhase.NIGHT_DOCTOR: 15,
            GamePhase.NIGHT_PROSTITUTE: 15,
            GamePhase.NIGHT_DETECTIVE: 15,
            GamePhase.NIGHT_RESULTS: 10,
        }
        return durations.get(phase, 30)

    async def start_voting_session(
            self,
            game_id: str,
            voting_type: VotingType
    ) -> str:
        """Start a voting session"""
        session_id = str(uuid.uuid4())

        # Get alive players
        alive_players = await repository.get_alive_players(game_id)

        self.voting_sessions[session_id] = {
            "game_id": game_id,
            "type": voting_type,
            "votes": {},  # voter_id -> target_id
            "started_at": datetime.utcnow(),
            "eligible_voters": [p.user_id for p in alive_players],
            "eligible_targets": [p.user_id for p in alive_players],
        }

        # Notify players
        await websocket_manager.broadcast(
            game_id,
            {
                "event": "voting_started",
                "session_id": session_id,
                "type": voting_type.value,
                "eligible_targets": self.voting_sessions[session_id]["eligible_targets"],
            }
        )

        return session_id

    async def cast_vote(
            self,
            session_id: str,
            voter_id: str,
            target_id: Optional[str]
    ) -> bool:
        """Cast a vote in voting session"""
        if session_id not in self.voting_sessions:
            return False

        session = self.voting_sessions[session_id]

        # Validate voter
        if voter_id not in session["eligible_voters"]:
            return False

        # Validate target (None = skip vote)
        if target_id and target_id not in session["eligible_targets"]:
            return False

        # Record vote
        session["votes"][voter_id] = target_id

        # Check if all voted
        if len(session["votes"]) == len(session["eligible_voters"]):
            await self._process_voting_results(session_id)

        return True

    async def _process_voting_results(self, session_id: str):
        """Process voting results"""
        session = self.voting_sessions[session_id]
        votes = session["votes"]

        # Count votes
        vote_counts = {}
        for target in votes.values():
            if target:  # Skip None votes
                vote_counts[target] = vote_counts.get(target, 0) + 1

        # Find winner (most votes)
        if vote_counts:
            winner = max(vote_counts.items(), key=lambda x: x[1])
            eliminated_player = winner[0] if winner[1] > len(votes) // 2 else None
        else:
            eliminated_player = None

        # Store result
        session["result"] = eliminated_player

        # Notify players
        await websocket_manager.broadcast(
            session["game_id"],
            {
                "event": "voting_results",
                "eliminated": eliminated_player,
                "vote_counts": vote_counts,
            }
        )

    async def execute_day_voting_results(self, game_id: str):
        """Execute the results of day voting"""
        # Find latest voting session for this game
        latest_session = None
        for session in self.voting_sessions.values():
            if session["game_id"] == game_id and session["type"] == VotingType.DAY_ELIMINATION:
                latest_session = session

        if not latest_session or "result" not in latest_session:
            return

        eliminated = latest_session["result"]
        if eliminated:
            # Kill player
            await self.eliminate_player(game_id, eliminated, "voted_out")

            # Check win conditions
            if await self.check_win_conditions(game_id):
                await self.advance_phase(game_id)  # Will transition to GAME_ENDED

    async def process_night_action(
            self,
            game_id: str,
            player_id: str,
            action: str,
            target_id: str
    ) -> bool:
        """Process a night action from a player"""
        # Validate action
        success = self.game_logic.process_night_action(
            game_id, player_id, action, target_id
        )

        if success:
            # Save to database
            await repository.save_action(
                game_id, player_id, action, target_id,
                self.game_logic.game_states[game_id]["phase"]
            )

        return success

    async def process_night_actions(self, game_id: str):
        """Process all night actions and apply results"""
        results = self.game_logic.resolve_night_actions(game_id)

        # Apply results
        if results["killed"]:
            await self.eliminate_player(game_id, results["killed"], "killed_by_mafia")

        # Notify detective
        if results["investigated"]:
            detective_id = None
            state = self.game_logic.game_states.get(game_id)
            for player_id, role in state["roles"].items():
                if role == Role.DETECTIVE:
                    detective_id = player_id
                    break

            if detective_id:
                await websocket_manager.send_to_user(
                    detective_id,
                    {
                        "event": "investigation_result",
                        "target": results["investigated"]["player"],
                        "is_mafia": results["investigated"]["is_mafia"],
                    }
                )

        # Broadcast night results
        await websocket_manager.broadcast(
            game_id,
            {
                "event": "night_results",
                "killed": results["killed"],
                "saved": results["healed"] == results["killed"],
            }
        )

        # Check win conditions
        if await self.check_win_conditions(game_id):
            await self.advance_phase(game_id)

    async def eliminate_player(self, game_id: str, player_id: str, reason: str):
        """Eliminate a player from the game"""
        # Update game logic state
        state = self.game_logic.game_states.get(game_id)
        if state:
            state["alive_players"].discard(player_id)

        # Update database
        await repository.eliminate_player(game_id, player_id, reason)

        # Notify player
        await websocket_manager.send_to_user(
            player_id,
            {
                "event": "eliminated",
                "reason": reason,
            }
        )

        logger.info(f"Player {player_id} eliminated from game {game_id}: {reason}")

    async def check_win_conditions(self, game_id: str) -> bool:
        """Check if game has ended"""
        return self.game_logic._check_win_conditions(game_id)

    async def end_game(self, game_id: str):
        """End the game and calculate results"""
        state = self.game_logic.game_states.get(game_id)
        if not state:
            return

        # Determine winner
        alive_players = state["alive_players"]
        roles = state["roles"]

        mafia_alive = sum(1 for p in alive_players if roles.get(p) == Role.MAFIA)
        citizens_alive = len(alive_players) - mafia_alive

        winner_team = "mafia" if mafia_alive > 0 else "citizens"

        # Calculate rewards
        from app.domains.economy.service import economy_service

        game_results = {}
        for player_id in state["players"]:
            player_role = roles.get(player_id, Role.CITIZEN)
            won = (player_role == Role.MAFIA and winner_team == "mafia") or \
                  (player_role != Role.MAFIA and winner_team == "citizens")

            game_results[player_id] = {
                "won": won,
                "role": player_role.value,
                "survived": player_id in alive_players,
            }

        rewards = await economy_service.calculate_game_rewards(game_id, game_results)
        await economy_service.distribute_game_rewards(game_id, rewards)

        # Update database
        await repository.end_game(game_id, winner_team, game_results)

        # Clean up
        if game_id in self.active_games:
            del self.active_games[game_id]
        if game_id in self.phase_timers:
            self.phase_timers[game_id].cancel()
            del self.phase_timers[game_id]
        if game_id in self.game_logic.game_states:
            del self.game_logic.game_states[game_id]

        # Notify players
        await websocket_manager.broadcast(
            game_id,
            {
                "event": "game_ended",
                "winner": winner_team,
                "results": game_results,
                "rewards": rewards,
            }
        )

        logger.info(f"Game {game_id} ended. Winner: {winner_team}")

    async def get_game_state(self, game_id: str, player_id: str) -> Dict:
        """Get current game state for a player"""
        state = self.game_logic.game_states.get(game_id)
        if not state:
            return None

        player_role = state["roles"].get(player_id)

        # Build state based on what player can see
        game_state = {
            "phase": state["phase"].value,
            "day_count": state["day_count"],
            "alive_players": list(state["alive_players"]),
            "my_role": player_role.value if player_role else None,
        }

        # Mafia can see other mafia
        if player_role == Role.MAFIA:
            game_state["mafia_players"] = [
                p for p, r in state["roles"].items()
                if r == Role.MAFIA
            ]

        return game_state

    async def handle_player_disconnect(self, game_id: str, player_id: str):
        """Handle player disconnection"""
        # Mark player as disconnected
        if game_id in self.active_games:
            if "disconnected" not in self.active_games[game_id]:
                self.active_games[game_id]["disconnected"] = set()
            self.active_games[game_id]["disconnected"].add(player_id)

        # Start AFK timer
        asyncio.create_task(self._afk_timer(game_id, player_id))

    async def _afk_timer(self, game_id: str, player_id: str, timeout: int = 120):
        """Kick player if AFK too long"""
        await asyncio.sleep(timeout)

        if game_id in self.active_games:
            disconnected = self.active_games[game_id].get("disconnected", set())
            if player_id in disconnected:
                # Player still disconnected, eliminate them
                await self.eliminate_player(game_id, player_id, "afk")

    def _get_role_description(self, role: Role) -> str:
        """Get role description for player"""
        descriptions = {
            Role.CITIZEN: "Вы мирный житель. Найдите и устраните всех мафиози!",
            Role.MAFIA: "Вы мафия. Устраните всех мирных жителей!",
            Role.DOCTOR: "Вы доктор. Каждую ночь можете спасти одного игрока.",
            Role.DETECTIVE: "Вы детектив. Каждую ночь можете проверить одного игрока.",
            Role.PROSTITUTE: "Вы путана. Каждую ночь можете заблокировать действия игрока.",
        }
        return descriptions.get(role, "")

    async def get_players(self, game_id: str, role: str = None):
        """Get players in game"""
        return await repository.get_players(game_id, role)


# Initialize service
game_service = GameService()


# Exported functions for compatibility
async def create_game():
    """Legacy function for backwards compatibility"""
    # This would be called from lobby service now
    pass


async def advance_phase(game_id: str):
    """Legacy function for backwards compatibility"""
    return await game_service.advance_phase(game_id)


async def get_players(game_id: str, role: str = None):
    """Legacy function for backwards compatibility"""
    return await game_service.get_players(game_id, role)


async def create_game_from_lobby(players, settings):
    """Legacy function for backwards compatibility"""
    return await game_service.create_game_from_lobby(players, settings)