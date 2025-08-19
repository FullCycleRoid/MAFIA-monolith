# app/domains/game/api.py
"""
Complete Game API with proper validation and error handling
"""
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from starlette.websockets import WebSocketState

from app.core.websocket_manager import websocket_manager
from app.domains.auth.dependencies import get_current_user
from app.domains.game import service
from app.domains.game.logic import GamePhase, Role
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Request/Response Models
class CreateGameRequest(BaseModel):
    """Request model for creating a game"""
    player_count: int = Field(ge=4, le=20, description="Number of players")
    mode: str = Field(default="classic", description="Game mode")
    settings: dict = Field(default_factory=dict, description="Custom game settings")

    @validator('mode')
    def validate_mode(cls, v):
        allowed_modes = ["classic", "turbo", "custom"]
        if v not in allowed_modes:
            raise ValueError(f"Mode must be one of {allowed_modes}")
        return v


class GameStateResponse(BaseModel):
    """Response model for game state"""
    game_id: str
    phase: str
    day_count: int
    alive_players: List[str]
    my_role: Optional[str]
    can_act: bool
    time_remaining: Optional[int]
    mafia_players: Optional[List[str]] = None  # Only for mafia


class VoteRequest(BaseModel):
    """Request model for voting"""
    target_id: Optional[str] = Field(None, description="Player to vote for, null to skip")

    @validator('target_id')
    def validate_target(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Target ID cannot be empty string")
        return v


class NightActionRequest(BaseModel):
    """Request model for night actions"""
    action: str = Field(..., description="Action type")
    target_id: str = Field(..., description="Target player ID")

    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ["kill", "heal", "investigate", "block"]
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of {allowed_actions}")
        return v


class GameListResponse(BaseModel):
    """Response model for game list"""
    games: List[dict]
    total: int
    page: int
    per_page: int


# Error handlers
class GameError(Exception):
    """Base exception for game errors"""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@router.exception_handler(GameError)
async def game_error_handler(request, exc: GameError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )


# Endpoints
@router.post("/create", response_model=dict)
async def create_game(
        request: CreateGameRequest,
        user=Depends(get_current_user)
):
    """Create a new game (deprecated - use matchmaking instead)"""
    return {
        "message": "Direct game creation is deprecated. Please use /api/matchmaking/queue/join",
        "redirect": "/api/matchmaking/queue/join"
    }


@router.get("/{game_id}/state", response_model=GameStateResponse)
async def get_game_state(
        game_id: str,
        user=Depends(get_current_user)
):
    """Get current game state for player"""
    try:
        # Check if player is in game
        player = await service.repository.get_player(game_id, user["id"])
        if not player:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not in this game"
            )

        # Get game state
        state = await service.game_service.get_game_state(game_id, user["id"])
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found or ended"
            )

        # Calculate time remaining for current phase
        time_remaining = None
        if game_id in service.game_service.phase_timers:
            # This is simplified - in production you'd track actual time
            time_remaining = 30

        # Check if player can act
        can_act = await _can_player_act(game_id, user["id"], state["phase"])

        return GameStateResponse(
            game_id=game_id,
            phase=state["phase"],
            day_count=state["day_count"],
            alive_players=state["alive_players"],
            my_role=state["my_role"],
            can_act=can_act,
            time_remaining=time_remaining,
            mafia_players=state.get("mafia_players")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting game state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get game state"
        )


@router.post("/{game_id}/vote")
async def cast_vote(
        game_id: str,
        request: VoteRequest,
        user=Depends(get_current_user)
):
    """Cast vote during day voting phase"""
    try:
        # Verify player is alive and in game
        player = await service.repository.get_player(game_id, user["id"])
        if not player or not player.alive:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot vote"
            )

        # Verify game is in voting phase
        game = await service.repository.get_game(game_id)
        if not game or game.phase != GamePhase.DAY_VOTING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not in voting phase"
            )

        # Find active voting session
        voting_session = None
        for session_id, session in service.game_service.voting_sessions.items():
            if session["game_id"] == game_id and session["type"] == service.VotingType.DAY_ELIMINATION:
                voting_session = session_id
                break

        if not voting_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active voting session"
            )

        # Cast vote
        success = await service.game_service.cast_vote(
            voting_session,
            user["id"],
            request.target_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cast vote"
            )

        return {"success": True, "message": "Vote cast successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error casting vote: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cast vote"
        )


@router.post("/{game_id}/action")
async def perform_night_action(
        game_id: str,
        request: NightActionRequest,
        user=Depends(get_current_user)
):
    """Perform night action"""
    try:
        # Verify player can perform action
        player = await service.repository.get_player(game_id, user["id"])
        if not player or not player.alive:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot perform actions"
            )

        # Verify it's night phase
        game = await service.repository.get_game(game_id)
        if not game or not game.phase.startswith("night_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not in night phase"
            )

        # Verify action matches player role
        role_actions = {
            Role.MAFIA.value: "kill",
            Role.DOCTOR.value: "heal",
            Role.DETECTIVE.value: "investigate",
            Role.PROSTITUTE.value: "block"
        }

        if player.role not in role_actions or role_actions[player.role] != request.action:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid action for your role"
            )

        # Process action
        success = await service.game_service.process_night_action(
            game_id,
            user["id"],
            request.action,
            request.target_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to perform action"
            )

        return {"success": True, "message": "Action performed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing night action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform action"
        )


@router.post("/{game_id}/advance_phase")
async def advance_phase(
        game_id: str,
        user=Depends(get_current_user)
):
    """Force advance to next phase (admin/debug only)"""
    # Check admin privileges
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        result = await service.advance_phase(game_id)
        return {"success": True, "new_phase": result.phase}
    except Exception as e:
        logger.error(f"Error advancing phase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to advance phase"
        )


@router.get("/{game_id}/players")
async def get_game_players(
        game_id: str,
        role: Optional[str] = Query(None, description="Filter by role"),
        user=Depends(get_current_user)
):
    """Get players in game"""
    try:
        # Check if user is in game
        player = await service.repository.get_player(game_id, user["id"])
        if not player:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not in this game"
            )

        players = await service.get_players(game_id, role)

        # Filter information based on what player should know
        player_info = []
        for p in players:
            info = {
                "user_id": p.user_id,
                "alive": p.alive,
                "death_reason": p.death_reason if not p.alive else None
            }

            # Only show roles if game ended or for own team
            game = await service.repository.get_game(game_id)
            if game and (game.status == "ended" or
                         (player.role == Role.MAFIA.value and p.role == Role.MAFIA.value)):
                info["role"] = p.role

            player_info.append(info)

        return {"players": player_info}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting players: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get players"
        )


@router.get("/{game_id}/history")
async def get_game_history(
        game_id: str,
        day: Optional[int] = Query(None, description="Filter by day"),
        user=Depends(get_current_user)
):
    """Get game action history"""
    try:
        # Check if user was in game
        player = await service.repository.get_player(game_id, user["id"])
        if not player:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You were not in this game"
            )

        # Check if game has ended
        game = await service.repository.get_game(game_id)
        if not game or game.status != "ended":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Game history only available after game ends"
            )

        actions = await service.repository.get_game_actions(game_id, day)

        return {
            "game_id": game_id,
            "actions": [
                {
                    "day": a.day,
                    "phase": a.phase,
                    "player_id": a.player_id,
                    "action_type": a.action_type,
                    "target_id": a.target_id,
                    "result": a.result,
                    "timestamp": a.created_at.isoformat()
                }
                for a in actions
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting game history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get game history"
        )


@router.get("/active", response_model=GameListResponse)
async def get_active_games(
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        user=Depends(get_current_user)
):
    """Get list of active games"""
    try:
        games = await service.repository.get_active_games()

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        paginated_games = games[start:end]

        game_list = []
        for game in paginated_games:
            players = await service.repository.get_players(game.id)
            game_list.append({
                "game_id": game.id,
                "status": game.status,
                "phase": game.phase,
                "player_count": len(players),
                "day_count": game.day_count,
                "started_at": game.started_at.isoformat() if game.started_at else None
            })

        return GameListResponse(
            games=game_list,
            total=len(games),
            page=page,
            per_page=per_page
        )

    except Exception as e:
        logger.error(f"Error getting active games: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active games"
        )


@router.get("/my_game")
async def get_my_active_game(user=Depends(get_current_user)):
    """Get user's active game if any"""
    try:
        game_id = await service.repository.get_player_active_game(user["id"])

        if not game_id:
            return {"active_game": None}

        return {"active_game": game_id}

    except Exception as e:
        logger.error(f"Error getting user's game: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active game"
        )


# WebSocket endpoint
@router.websocket("/{game_id}/ws")
async def game_websocket(
        websocket: WebSocket,
        game_id: str
):
    """WebSocket connection for real-time game updates"""
    # Get user from query params or headers
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        # Validate token and get user
        from app.domains.auth.service import validate_token
        user = await validate_token(token)

        # Check if user is in game
        player = await service.repository.get_player(game_id, user.id)
        if not player:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Connect to websocket manager
        await websocket_manager.connect(websocket, game_id=game_id, user_id=user.id)

        # Send initial state
        state = await service.game_service.get_game_state(game_id, user.id)
        await websocket.send_json({
            "type": "game_state",
            "data": state
        })

        # Handle messages
        while websocket.client_state == WebSocketState.CONNECTED:
            try:
                data = await websocket.receive_json()

                # Process different message types
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                elif data.get("type") == "chat":
                    # Broadcast chat message
                    await websocket_manager.broadcast(
                        game_id,
                        {
                            "type": "chat",
                            "from": user.id,
                            "message": data.get("message", ""),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

                elif data.get("type") == "emoji":
                    # Broadcast emoji reaction
                    await websocket_manager.broadcast(
                        game_id,
                        {
                            "type": "emoji",
                            "from": user.id,
                            "emoji": data.get("emoji", ""),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        # Disconnect and handle AFK
        websocket_manager.disconnect(websocket)
        await service.game_service.handle_player_disconnect(game_id, user.id)


# Helper functions
async def _can_player_act(game_id: str, user_id: str, phase: str) -> bool:
    """Check if player can perform actions in current phase"""
    player = await service.repository.get_player(game_id, user_id)
    if not player or not player.alive:
        return False

    # Check phase-specific permissions
    if phase == GamePhase.DAY_VOTING.value:
        return True
    elif phase == GamePhase.NIGHT_MAFIA.value:
        return player.role == Role.MAFIA.value
    elif phase == GamePhase.NIGHT_DOCTOR.value:
        return player.role == Role.DOCTOR.value
    elif phase == GamePhase.NIGHT_DETECTIVE.value:
        return player.role == Role.DETECTIVE.value
    elif phase == GamePhase.NIGHT_PROSTITUTE.value:
        return player.role == Role.PROSTITUTE.value

    return False


# Admin endpoints
@router.post("/admin/{game_id}/end", tags=["admin"])
async def force_end_game(
        game_id: str,
        winner_team: str = Query(..., regex="^(mafia|citizens)$"),
        user=Depends(get_current_user)
):
    """Force end a game (admin only)"""
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        await service.game_service.end_game(game_id)
        return {"success": True, "message": f"Game ended with {winner_team} winning"}
    except Exception as e:
        logger.error(f"Error force ending game: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end game"
        )
