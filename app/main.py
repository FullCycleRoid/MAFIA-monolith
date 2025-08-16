from starlette.requests import Request
from fastapi import FastAPI, WebSocket
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect

from .core import (
    config,
    event_bus,
    database,
    celery,
    websocket_manager,
    exception_handlers,
    redis,
)
from .core.middleware import auth_middleware, locale_middleware
from .domains import game, voice, economy, auth


app = FastAPI(title="Mafia Monolith Backend")

# Подключение middleware
app.middleware("http")(auth_middleware)
# app.middleware("http")(locale_middleware)

# Настройка обработчиков ошибок
exception_handlers.setup_exception_handlers(app)

# Настройки CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Инициализация компонентов
@app.on_event("startup")
async def startup_event():
    # Инициализация базы данных
    await database.init_db()

    # Инициализация Celery
    celery.init_celery()

    # Инициализация шины событий
    event_bus.init_event_bus()

    # Регистрация обработчиков событий
    await voice.register_event_handlers()
    await economy.register_event_handlers()


# Подключение роутов
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(game.router, prefix="/api/game", tags=["game"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(economy.router, prefix="/api/economy", tags=["economy"])


# Health check
@app.get("/health")
async def health():
    services = {
        "database": await database.check_connection(),
        "redis": await redis.check_connection(),
        "rabbitmq": await celery.check_connection()
    }
    status = "ok" if all(services.values()) else "degraded"
    return {"status": status, "services": services}

# WebSocket endpoint
@app.websocket("/ws/games/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket_manager.connect(game_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Обработка входящих сообщений
            await websocket_manager.handle_connection(game_id, websocket)
    except WebSocketDisconnect:
        websocket_manager.disconnect(game_id, websocket)
