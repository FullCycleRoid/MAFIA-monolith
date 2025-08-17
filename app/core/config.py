# app/core/config.py
"""
Updated configuration with TON blockchain settings
"""
import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = os.getenv("ENV", "dev")  # dev, staging, prod

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mafia_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672"

    # Override for production
    if ENV == "prod":
        DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://prod_user:prod_pass@postgres:5432/mafia_prod",
        )
        REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
        RABBITMQ_URL: str = os.getenv(
            "RABBITMQ_URL", "amqp://mafia:mafia@rabbitmq:5672"
        )

    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev_secret_key_change_in_production")
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    WALLET_ENCRYPTION_KEY: str = os.getenv(
        "WALLET_ENCRYPTION_KEY", "dev_encryption_key_must_be_32_bytes_long!!!"
    )

    # TON Blockchain Configuration
    TON_NETWORK: str = os.getenv("TON_NETWORK", "testnet")  # mainnet, testnet
    TON_API_KEY: str = os.getenv("TON_API_KEY", "")

    # $MAFIA Jetton Configuration
    MAFIA_JETTON_MASTER_ADDRESS: str = os.getenv(
        "MAFIA_JETTON_MASTER_ADDRESS",
        "EQC_1YoM8RBixN95lz7odcF3Vrkc_N8Ne7gQi7Abttr_Efi3",  # Example testnet address
    )

    # Service wallet for minting/rewards (should have minter role)
    SERVICE_WALLET_MNEMONIC: str = os.getenv("SERVICE_WALLET_MNEMONIC", "")
    SERVICE_WALLET_ADDRESS: str = os.getenv("SERVICE_WALLET_ADDRESS", "")

    # TON Light Server Configuration
    TON_LS_INDEX: int = int(os.getenv("TON_LS_INDEX", "0"))
    TON_TRUST_LEVEL: int = int(os.getenv("TON_TRUST_LEVEL", "2"))

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBAPP_URL: str = os.getenv(
        "TELEGRAM_WEBAPP_URL", "https://t.me/mafia_game_bot/app"
    )

    # Voice Server
    MEDIASOUP_URL: str = os.getenv("MEDIASOUP_URL", "http://voice-server:4443")
    MEDIASOUP_WORKERS: int = int(os.getenv("MEDIASOUP_WORKERS", "10"))

    # CORS
    CORS_ORIGINS: List[str] = (
        ["*"] if ENV == "dev" else ["https://your-domain.com", "https://t.me"]
    )

    # Economy Settings
    MIN_WITHDRAWAL_AMOUNT: int = 100
    MAX_WITHDRAWAL_AMOUNT: int = 100000
    WITHDRAWAL_FEE_PERCENT: int = 2
    GIFT_FEE_PERCENT: int = 10

    # Game Settings
    MIN_PLAYERS_PER_GAME: int = 4
    MAX_PLAYERS_PER_GAME: int = 20
    DEFAULT_GAME_DURATION_MINUTES: int = 30

    # Rate Limits
    MAX_REQUESTS_PER_MINUTE: int = 60
    MAX_WITHDRAWALS_PER_DAY: int = 3
    MAX_REPORTS_PER_DAY: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
