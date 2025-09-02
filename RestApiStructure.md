# Полный анализ бэкенда: REST API, WebSocket и схемы данных

## Детальная структура REST API

### 1. Authentication (`/api/auth`)
- **POST /api/auth/telegram** - Аутентификация через Telegram WebApp
  - Request: 
    ```python
    class TelegramAuthData(BaseModel):
        id: int
        first_name: str
        last_name: Optional[str] = None
        username: Optional[str] = None
        language_code: str = "en"
        is_bot: bool = False
        allows_write_to_pm: bool = False
        auth_date: int
        hash: str
    ```
  - Response: `{"access_token": str, "token_type": "bearer"}`

### 2. Game (`/api/game`)
- **POST /api/game/create** - Создание игры (deprecated, использовать matchmaking)
  - Request:
    ```python
    class CreateGameRequest(BaseModel):
        player_count: int = Field(ge=4, le=20)
        mode: str = Field(default="classic")
        settings: dict = Field(default_factory=dict)
    ```
  - Response: `{"message": str, "redirect": str}`

- **GET /api/game/{game_id}/state** - Получить состояние игры
  - Response:
    ```python
    class GameStateResponse(BaseModel):
        game_id: str
        phase: str
        day_count: int
        alive_players: List[str]
        my_role: Optional[str]
        can_act: bool
        time_remaining: Optional[int]
        mafia_players: Optional[List[str]] = None
    ```

- **POST /api/game/{game_id}/vote** - Голосование
  - Request:
    ```python
    class VoteRequest(BaseModel):
        target_id: Optional[str] = Field(None)
    ```

- **POST /api/game/{game_id}/action** - Ночное действие
  - Request:
    ```python
    class NightActionRequest(BaseModel):
        action: str = Field(...)
        target_id: str = Field(...)
    ```

- **POST /api/game/{game_id}/advance_phase** - Принудительно сменить фазу (admin)
- **GET /api/game/{game_id}/players** - Получить игроков
  - Query params: `role: Optional[str] = None`
  - Response: `{"players": List[PlayerInfo]}`

- **GET /api/game/{game_id}/history** - История игры
  - Query params: `day: Optional[int] = None`
  - Response: `{"game_id": str, "actions": List[GameAction]}`

- **GET /api/game/active** - Активные игры
  - Query params: `page: int = 1, per_page: int = 20`
  - Response:
    ```python
    class GameListResponse(BaseModel):
        games: List[dict]
        total: int
        page: int
        per_page: int
    ```

- **GET /api/game/my_game** - Текущая игра пользователя
  - Response: `{"active_game": Optional[str]}`

- **POST /api/game/admin/{game_id}/end** - Завершить игру (admin)
  - Query params: `winner_team: str` (mafia|citizens)

### 3. Economy (`/api/economy`)
- **POST /api/economy/wallet/create** - Создать кошелек
  - Response:
    ```python
    class CreateWalletResponse(BaseModel):
        ton_address: str
        jetton_wallet: str
        balance_offchain: int
        balance_onchain: float
    ```

- **GET /api/economy/balance** - Получить баланс
  - Response:
    ```python
    class BalanceResponse(BaseModel):
        offchain: int
        onchain: float
        total: float
        ton_balance: float
    ```

- **POST /api/economy/withdraw** - Вывод средств
  - Request:
    ```python
    class WithdrawRequest(BaseModel):
        amount: int = Field(gt=0)
    ```

- **POST /api/economy/gift** - Отправить подарок
  - Request:
    ```python
    class SendGiftRequest(BaseModel):
        to_user: str
        amount: int = Field(gt=0, le=10000)
        message: Optional[str] = None
    ```

- **POST /api/economy/purchase** - Покупка предметов
  - Request:
    ```python
    class PurchaseRequest(BaseModel):
        item_type: str
        item_id: str
        price: int = Field(gt=0)
    ```

- **GET /api/economy/transactions** - История транзакций
  - Query params: `limit: int = 50`
  - Response: `List[Transaction]`

- **GET /api/economy/leaderboard** - Токен-лидерборд
  - Query params: `period: str = "all"`
  - Response: `List[LeaderboardEntry]`

### 4. Voice (`/api/voice`)
- **POST /api/voice/rooms** - Создать голосовую комнату
  - Query params: `game_id: str`
  - Response: `{"room_id": str}`

- **GET /api/voice/rooms/{room_id}** - Получить информацию о комнате
  - Response: `{"room_id": str}`

### 5. Matchmaking (`/api/matchmaking`)
- **POST /api/matchmaking/queue/join** - Войти в очередь
  - Query params: `mode: str, languages: List[str]`
  - Response: `{"status": str}`

- **POST /api/matchmaking/queue/leave** - Покинуть очередь
  - Response: `{"success": bool}`

- **POST /api/matchmaking/lobby/create** - Создать лобби
  - Response: `{"invite_code": str}`

- **POST /api/matchmaking/lobby/join/{invite_code}** - Присоединиться к лобби
  - Response: `{"success": bool}`

- **POST /api/matchmaking/lobby/{lobby_id}/ready** - Отметить готовность
  - Response: `{"success": bool}`

### 6. Social (`/api/social`)
- **POST /api/social/gifts/send** - Отправить подарок
  - Request:
    ```python
    class SendGiftRequest(BaseModel):
        to_user: str
        gift_type: str
        game_id: Optional[str] = None
    ```

- **POST /api/social/linguistic/rate** - Оценить языковые навыки
  - Request:
    ```python
    class RateLinguisticRequest(BaseModel):
        rated_user: str
        language: str
        score: int  # 1-5
        game_id: str
    ```

- **POST /api/social/report** - Пожаловаться на игрока
  - Request:
    ```python
    class ReportPlayerRequest(BaseModel):
        reported_user: str
        reason: str
        game_id: str
        evidence: Optional[str] = None
    ```

- **GET /api/social/stats/{user_id}** - Социальная статистика
  - Response: `UserSocialStats`

### 7. Moderation (`/api/moderation`)
- **GET /api/moderation/status/{user_id}** - Статус модерации
  - Response: `UserModerationStatus`

- **POST /api/moderation/appeal** - Подать апелляцию
  - Request:
    ```python
    class AppealRequest(BaseModel):
        appeal_text: str
    ```

- **POST /api/moderation/admin/ban** - Забанить пользователя (admin)
  - Request:
    ```python
    class BanUserRequest(BaseModel):
        user_id: str
        duration_hours: Optional[int]
        reason: str
        evidence: Optional[str] = None
    ```

## WebSocket Endpoints

### Основные соединения (main.py):
```python
@app.websocket("/ws/games/{game_id}")
async def websocket_game_endpoint(websocket: WebSocket, game_id: str, user_id: Optional[str] = None)

@app.websocket("/ws/notifications")  
async def notifications_websocket(websocket: WebSocket, user_id: str)
```

### Игровые WebSocket (game/api.py):
```python
@router.websocket("/{game_id}/ws")
async def game_websocket(websocket: WebSocket, game_id: str)
```

## Дополнительные схемы данных

### Модели игровых сущностей:
```python
class PlayerInfo(BaseModel):
    user_id: str
    alive: bool
    death_reason: Optional[str] = None
    role: Optional[str] = None  # Только если игра окончена или это мафия

class GameAction(BaseModel):
    day: int
    phase: str
    player_id: str
    action_type: str
    target_id: Optional[str] = None
    result: Optional[str] = None
    timestamp: str

class Transaction(BaseModel):
    id: str
    user_id: str
    amount: int
    type: str  # credit, debit, withdrawal, mint
    reason: str
    is_onchain: bool
    tx_hash: Optional[str] = None
    timestamp: str
    status: str

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    balance: int
    total_earned: int
    transactions: int

class UserSocialStats(BaseModel):
    user_id: str
    likes_received: int
    likes_given: int
    gifts_received: int
    gifts_sent: int
    reports_received: int
    reports_sent: int
    friends_count: int
    linguistic_ratings: Dict[str, float]

class UserModerationStatus(BaseModel):
    banned: bool
    ban_details: Optional[Ban]
    restrictions: List[Restriction]
    warnings: List[Warning]
    can_play: bool
    can_voice: bool
    can_chat: bool
    can_send_gifts: bool

class Ban(BaseModel):
    ban_id: str
    user_id: str
    type: str
    reason: str
    issued_by: str
    issued_at: datetime
    expires_at: Optional[datetime]
    evidence: Optional[str]
    appeal_status: str
    notes: Optional[str]

class Restriction(BaseModel):
    restriction_id: str
    user_id: str
    type: str
    expires_at: datetime
    reason: str
    value: Optional[int]

class Warning(BaseModel):
    warning_id: str
    user_id: str
    reason: str
    severity: int
    issued_at: datetime
```

## WebSocket сообщения

### Входящие сообщения (от клиента):
- **ping**: `{"type": "ping"}`
- **chat**: `{"type": "chat", "message": str}`
- **emoji**: `{"type": "emoji", "emoji": str}`

### Исходящие сообщения (к клиенту):
- **pong**: `{"type": "pong"}`
- **chat**: `{"type": "chat", "from": user_id, "message": str, "timestamp": str}`
- **emoji**: `{"type": "emoji", "from": user_id, "emoji": str, "timestamp": str}`
- **game_state**: `{"type": "game_state", "data": GameStateResponse}`
- **connected**: `{"type": "connected", "reconnect_token": str, "timestamp": str}`
- **voting_started**: `{"event": "voting_started", "session_id": str, "type": str, "eligible_targets": List[str]}`
- **voting_results**: `{"event": "voting_results", "eliminated": Optional[str], "vote_counts": Dict[str, int]}`
- **role_assigned**: `{"event": "role_assigned", "game_id": str, "role": str, "role_description": str}`
- **eliminated**: `{"event": "eliminated", "reason": str}`
- **investigation_result**: `{"event": "investigation_result", "target": str, "is_mafia": bool}`
- **night_results**: `{"event": "night_results", "killed": Optional[str], "saved": bool}`
- **game_ended**: `{"event": "game_ended", "winner": str, "results": Dict, "rewards": Dict}`
- **notification**: `{"type": "notification", "notification_type": str, "data": Dict, "timestamp": str}`

## Архитектурные особенности

1. **Модульная структура**: Разделение на домены (auth, game, economy, voice, matchmaking, social, moderation)
2. **Аутентификация**: JWT с Telegram WebApp интеграцией
3. **WebSocket управление**: Централизованный WebSocketManager с поддержкой переподключения
4. **Блокчейн интеграция**: TON blockchain для экономики игры
5. **Фоновые задачи**: Celery для обработки выводов, обновления цен и очистки
6. **Голосовой чат**: Интеграция с Mediasoup через отдельный сервис
7. **Базы данных**: PostgreSQL (основные данные) + Redis (кэш и WebSocket управление)
8. **Кэширование**: Многоуровневое кэширование для балансов и транзакций
9. **Событийная система**: EventBus для межмодульного взаимодействия
10. **Модерация**: Полноценная система банов, ограничений и предупреждений

Архитектура обеспечивает масштабируемость, отказоустойчивость и высокую производительность для многопользовательской игры с экономикой на блокчейне.