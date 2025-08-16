import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = os.getenv("ENV", "dev")  # dev, prod

    # Настройки по умолчанию для dev
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mafia_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672"

    # Переопределение для prod
    if ENV == "prod":
        DATABASE_URL: str = "postgresql+asyncpg://prod_user:prod_pass@postgres:5432/mafia_prod"
        REDIS_URL: str = "redis://redis:6379/0"
        RABBITMQ_URL: str = "amqp://mafia:mafia@rabbitmq:5672"

    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev_secret_fallback")
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: list = ["*"] if ENV == "dev" else ["https://your-prod-domain.com"]
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    MEDIASOUP_URL: str = "http://voice-server:4443"
    MEDIASOUP_WORKERS: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
