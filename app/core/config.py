# app/core/config.py
"""
Multi-environment configuration with a single env directory (config/env).
- Loads {ENV_DIR}/.env.{ENVIRONMENT} or fallback to {ENV_DIR}/.env
- Ignores unknown keys from env-files (extra='ignore') so shared .env works
- Tolerant CORS_ORIGINS parser: "*", CSV, or JSON array
"""

import os
import json
from enum import Enum
from typing import Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


def _compute_env_file() -> Optional[str]:
    """
    Pick env file based on ENVIRONMENT and ENV_DIR.
    Order:
      1) {ENV_DIR}/.env.{ENVIRONMENT}
      2) {ENV_DIR}/.env
    """
    env = os.getenv("ENVIRONMENT", "local").lower()
    env_dir = os.getenv("ENV_DIR", "config/env")
    candidates = [
        os.path.join(env_dir, f".env.{env}"),
        os.path.join(env_dir, ".env"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


class Settings(BaseSettings):
    # КРИТИЧНО: extra='ignore' — лишние ключи из общего .env не ломают валидацию.
    # env_ignore_empty=True — пустые значения не ломают парсинг сложных полей.
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_ignore_empty=True,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Environment = Field(default="local", env="ENVIRONMENT")

    # Database / brokers
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/mafia_local"
    )
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    RABBITMQ_URL: str = Field(default="amqp://guest:guest@localhost:5672")

    # TON
    TON_NETWORK: str = Field(default="sandbox")
    TON_ENDPOINT: Optional[str] = Field(default=None)
    TON_API_KEY: Optional[str] = Field(default=None)
    TON_LS_INDEX: int = Field(default=0)
    TON_TRUST_LEVEL: int = Field(default=2)
    TON_USE_SANDBOX: bool = Field(default=False)
    TON_TEST_WALLET_SEED: Optional[str] = Field(default=None)

    # Jetton
    MAFIA_JETTON_MASTER_ADDRESS: Optional[str] = Field(default=None)
    SERVICE_WALLET_MNEMONIC: Optional[str] = Field(default=None)
    SERVICE_WALLET_ADDRESS: Optional[str] = Field(default=None)

    # Transaction settings
    MIN_WITHDRAWAL_AMOUNT: int = Field(default=100)
    MAX_WITHDRAWAL_AMOUNT: int = Field(default=100000)
    WITHDRAWAL_FEE_PERCENT: int = Field(default=2)

    # Services
    MEDIASOUP_URL: str = Field(default="http://localhost:4443")
    MEDIASOUP_WORKERS: int = Field(default=2)

    # Security
    JWT_SECRET: str = Field(default="local_secret_key_for_development_only")
    JWT_ALG: str = Field(default="HS256")
    WALLET_ENCRYPTION_KEY: str = Field(default="local_encryption_key_32_bytes_ok!")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)

    # Features
    AUTO_CREATE_WALLET: bool = Field(default=False)
    MOCK_BLOCKCHAIN_CALLS: bool = Field(default=False)
    USE_TESTNET_FAUCET: bool = Field(default=False)
    REQUIRE_KYC: bool = Field(default=False)
    REQUIRE_2FA: bool = Field(default=False)
    AUDIT_MODE: bool = Field(default=False)

    # Telegram
    TELEGRAM_BOT_TOKEN: str = Field(default="test_token")
    TELEGRAM_WEBAPP_URL: Optional[str] = Field(default=None)

    # CORS — List[str]
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None)
    AMPLITUDE_API_KEY: Optional[str] = Field(default=None)

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = Field(default=60)
    MAX_WITHDRAWALS_PER_DAY: int = Field(default=3)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        """
        Accept:
          - "*"  -> ["*"]
          - "http://a, http://b" -> ["http://a", "http://b"]
          - '["http://a","http://b"]' (JSON) -> as-is
        """
        if v is None or v == "":
            return ["*"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s == "*" or s == '"*"':
                return ["*"]
            if s.startswith("["):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass
            return [x.strip() for x in s.split(",") if x.strip()]
        return v


class LocalConfig(Settings):
    ENVIRONMENT: Environment = "local"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres-local:5432/mafia_local"
    REDIS_URL: str = "redis://redis-local:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq-local:5672"

    TON_NETWORK: str = "sandbox"
    TON_ENDPOINT: str = "http://ton-local:8081"
    TON_USE_SANDBOX: bool = True
    TON_TEST_WALLET_SEED: str = "test_seed_12345"

    MEDIASOUP_URL: str = "http://localhost:4443"

    AUTO_CREATE_WALLET: bool = True
    MOCK_BLOCKCHAIN_CALLS: bool = True


class DevConfig(Settings):
    ENVIRONMENT: Environment = "dev"
    TON_NETWORK: str = "testnet"
    TON_ENDPOINT: str = "https://testnet.toncenter.com/api/v2/jsonRPC"
    AUTO_CREATE_WALLET: bool = True
    USE_TESTNET_FAUCET: bool = True


class StagingConfig(Settings):
    ENVIRONMENT: Environment = "staging"
    TON_NETWORK: str = "testnet"
    AUTO_CREATE_WALLET: bool = False
    REQUIRE_KYC: bool = True
    MEDIASOUP_WORKERS: int = 10


class ProdConfig(Settings):
    ENVIRONMENT: Environment = "prod"
    TON_NETWORK: str = "mainnet"
    TON_ENDPOINT: str = "https://toncenter.com/api/v2/jsonRPC"
    AUTO_CREATE_WALLET: bool = False
    REQUIRE_KYC: bool = True
    REQUIRE_2FA: bool = True
    AUDIT_MODE: bool = True
    MEDIASOUP_WORKERS: int = 20
    MAX_REQUESTS_PER_MINUTE: int = 60
    MAX_WITHDRAWALS_PER_DAY: int = 3


def get_settings() -> Settings:
    env = os.getenv("ENVIRONMENT", "local").lower()
    configs = {
        "local": LocalConfig,
        "dev": DevConfig,
        "staging": StagingConfig,
        "prod": ProdConfig,
    }
    config_class = configs.get(env, LocalConfig)
    env_file = _compute_env_file()
    if env_file:
        return config_class(_env_file=env_file, _env_file_encoding="utf-8")
    return config_class()


# Global settings instance
settings = get_settings()
