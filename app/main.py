from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

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
from app.domains.economy.service import economy_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    celery.init_celery()
    event_bus.init_event_bus()
    await economy_service.initialize()
    voice.register_event_handlers()
    economy.register_event_handlers()
    await websocket_manager.start()
    yield
    await websocket_manager.stop()


app = FastAPI(title="Mafia Game Backend with TON Integration", version="2.0.0", lifespan=lifespan)

app.middleware("http")(auth_middleware)
exception_handlers.setup_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(game.router, prefix="/api/game", tags=["Game"])
if hasattr(game, "ws_router"):
    app.include_router(game.ws_router, prefix="/api/game", tags=["Game WS"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(economy.router, prefix="/api/economy", tags=["Economy"])
app.include_router(matchmaking.router, prefix="/api/matchmaking", tags=["Matchmaking"])
app.include_router(social.router, prefix="/api/social", tags=["Social"])
app.include_router(moderation.router, prefix="/api/moderation", tags=["Moderation"])


@app.get("/health")
async def health():
    services = {
        "database": await database.check_connection(),
        "redis": await redis.check_connection(),
        "rabbitmq": await celery.check_connection(),
    }
    try:
        addr = config.settings.SERVICE_WALLET_ADDRESS
        if not addr:
            raise RuntimeError("no service wallet")
        # lightweight TON probe with timeout
        import asyncio
        async def probe():
            return await ton_service.get_ton_balance(addr)
        await asyncio.wait_for(probe(), timeout=2.0)
        services["ton_blockchain"] = True
    except Exception:
        services["ton_blockchain"] = False
    status = "healthy" if all(services.values()) else "degraded"
    return {
        "status": status,
        "services": services,
        "version": "2.0.0",
        "blockchain": "TON",
        "token_ticker": config.settings.TOKEN_TICKER,
    }