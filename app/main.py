from typing import Optional

from fastapi import FastAPI, WebSocket
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect
from .domains import matchmaking, social, moderation
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
app.include_router(matchmaking.router, prefix="/api/matchmaking", tags=["matchmaking"])
app.include_router(social.router, prefix="/api/social", tags=["social"])
app.include_router(moderation.router, prefix="/api/moderation", tags=["moderation"])


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


@app.websocket("/ws/games/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, user_id: Optional[str] = None):
    await websocket_manager.connect(websocket, game_id=game_id, user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


# Добавить глобальный WebSocket для уведомлений:
@app.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket, user_id: str):
    await websocket_manager.connect(websocket, user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Обработка команд от клиента (подписки и т.д.)
            await websocket_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
