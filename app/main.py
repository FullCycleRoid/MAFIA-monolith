from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect

from app.core import (
    celery,
    config,
    database,
    event_bus,
    exception_handlers,
    redis,
)
from app.core.websocket_manager import websocket_manager
from app.core.middleware import auth_middleware
from app.domains import auth, economy, game, matchmaking, moderation, social, voice
from app.domains.economy.ton_service import ton_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting application...")

    # Initialize Celery
    celery.init_celery()

    # Initialize event bus
    event_bus.init_event_bus()

    # Initialize TON service
    await economy.service.economy_service.initialize()

    # Register event handlers
    voice.register_event_handlers()
    economy.register_event_handlers()

    await websocket_manager.start()

    print("Application started successfully")

    yield

    await websocket_manager.stop()
    # Shutdown
    print("Shutting down application...")
    # Clean up resources here


# Create FastAPI app
app = FastAPI(
    title="Mafia Game Backend with TON Integration", version="2.0.0", lifespan=lifespan
)

# Add middleware
app.middleware("http")(auth_middleware)

# Setup exception handlers
exception_handlers.setup_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(game.router, prefix="/api/game", tags=["Game"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(economy.router, prefix="/api/economy", tags=["Economy"])
app.include_router(matchmaking.router, prefix="/api/matchmaking", tags=["Matchmaking"])
app.include_router(social.router, prefix="/api/social", tags=["Social"])
app.include_router(moderation.router, prefix="/api/moderation", tags=["Moderation"])


# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    services = {
        "database": await database.check_connection(),
        "redis": await redis.check_connection(),
        "rabbitmq": await celery.check_connection(),
    }

    # Check TON connection
    try:

        if ton_service.client:
            services["ton_blockchain"] = True
        else:
            services["ton_blockchain"] = False
    except:
        services["ton_blockchain"] = False

    status = "healthy" if all(services.values()) else "degraded"

    return {
        "status": status,
        "services": services,
        "version": "2.0.0",
        "blockchain": "TON",
        "token": "$MAFIA",
    }


# WebSocket endpoints
@app.websocket("/ws/games/{game_id}")
async def websocket_game_endpoint(
    websocket: WebSocket, game_id: str, user_id: Optional[str] = None
):
    """Game WebSocket endpoint"""
    await websocket_manager.connect(websocket, game_id=game_id, user_id=user_id)

    try:
        while True:
            data = await websocket.receive_text()
            await websocket_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


@app.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket, user_id: str):
    """Notifications WebSocket endpoint"""
    await websocket_manager.connect(websocket, user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
