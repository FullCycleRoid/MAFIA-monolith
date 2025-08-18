"""
Multi-environment configuration system for TON integration
"""
import os
from enum import Enum
from typing import Optional, List

from pydantic_settings import BaseSettings
from pydantic import Field


class Environment(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    """Base settings class"""
    # Environment
    ENVIRONMENT: Environment = Field(default="local", env="ENVIRONMENT")

    # Database
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

    # Jetton settings
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

    # CORS
    CORS_ORIGINS: List[str] = Field(default=["*"])

    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None)
    AMPLITUDE_API_KEY: Optional[str] = Field(default=None)

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = Field(default=60)
    MAX_WITHDRAWALS_PER_DAY: int = Field(default=3)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


class LocalConfig(Settings):
    """Local development with TON sandbox"""
    ENVIRONMENT: Environment = "local"

    # Override defaults for local
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres-local:5432/mafia_local"
    REDIS_URL: str = "redis://redis-local:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq-local:5672"

    # TON Sandbox
    TON_NETWORK: str = "sandbox"
    TON_ENDPOINT: str = "http://ton-local:8081"
    TON_USE_SANDBOX: bool = True
    TON_TEST_WALLET_SEED: str = "test_seed_12345"

    # Services
    MEDIASOUP_URL: str = "http://localhost:4443"

    # Features
    AUTO_CREATE_WALLET: bool = True
    MOCK_BLOCKCHAIN_CALLS: bool = True

    class Config:
        env_file = ".env.local"


class DevConfig(Settings):
    """Development environment with TON testnet"""
    ENVIRONMENT: Environment = "dev"

    # TON Testnet
    TON_NETWORK: str = "testnet"
    TON_ENDPOINT: str = "https://testnet.toncenter.com/api/v2/jsonRPC"

    # Features
    AUTO_CREATE_WALLET: bool = True
    USE_TESTNET_FAUCET: bool = True

    class Config:
        env_file = ".env.dev"


class StagingConfig(Settings):
    """Staging environment - production-like with testnet"""
    ENVIRONMENT: Environment = "staging"

    # TON Testnet
    TON_NETWORK: str = "testnet"

    # Features
    AUTO_CREATE_WALLET: bool = False
    REQUIRE_KYC: bool = True

    # Services
    MEDIASOUP_WORKERS: int = 10

    class Config:
        env_file = ".env.staging"


class ProdConfig(Settings):
    """Production environment with TON mainnet"""
    ENVIRONMENT: Environment = "prod"

    # TON Mainnet
    TON_NETWORK: str = "mainnet"
    TON_ENDPOINT: str = "https://toncenter.com/api/v2/jsonRPC"

    # Features
    AUTO_CREATE_WALLET: bool = False
    REQUIRE_KYC: bool = True
    REQUIRE_2FA: bool = True
    AUDIT_MODE: bool = True

    # Services
    MEDIASOUP_WORKERS: int = 20

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = 60
    MAX_WITHDRAWALS_PER_DAY: int = 3

    class Config:
        env_file = ".env.prod"


def get_settings() -> Settings:
    """Get settings based on environment"""
    env = os.getenv("ENVIRONMENT", "local").lower()

    configs = {
        "local": LocalConfig,
        "dev": DevConfig,
        "staging": StagingConfig,
        "prod": ProdConfig,
    }

    config_class = configs.get(env, LocalConfig)
    return config_class()


# Global settings instance
settings = get_settings()
