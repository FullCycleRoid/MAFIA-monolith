"""
Multi-environment configuration system for TON integration
"""
import os
from enum import Enum
from typing import Optional

from pydantic import BaseSettings, Field


class Environment(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class TONConfig(BaseSettings):
    """TON blockchain configuration"""

    network: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    ls_index: int = 0
    trust_level: int = 2

    # Jetton settings
    jetton_master_address: Optional[str] = None
    service_wallet_mnemonic: Optional[str] = None
    service_wallet_address: Optional[str] = None

    # Transaction settings
    min_withdrawal: int = 100
    max_withdrawal: int = 100000
    withdrawal_fee_percent: int = 2

    class Config:
        env_prefix = "TON_"


class LocalConfig(BaseSettings):
    """Local development with TON sandbox"""

    ENV: str = "local"

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/mafia_local"
    )
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672"

    # TON Sandbox
    TON_NETWORK: str = "sandbox"
    TON_ENDPOINT: str = "http://localhost:8081"
    TON_USE_SANDBOX: bool = True

    # Auto-generated test wallet
    TON_TEST_WALLET_SEED: str = "test_seed_12345"

    # Services
    MEDIASOUP_URL: str = "http://localhost:4443"

    # Security (test keys)
    JWT_SECRET: str = "local_secret_key_for_development_only"
    WALLET_ENCRYPTION_KEY: str = "local_encryption_key_32_bytes_ok!"

    # Features
    AUTO_CREATE_WALLET: bool = True
    MOCK_BLOCKCHAIN_CALLS: bool = True

    class Config:
        env_file = ".env.local"


class DevConfig(BaseSettings):
    """Development environment with TON testnet"""

    ENV: str = "dev"

    # Database (Docker)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/mafia_dev",
        env="DATABASE_URL",
    )
    REDIS_URL: str = Field(default="redis://redis:6379/0", env="REDIS_URL")
    RABBITMQ_URL: str = Field(
        default="amqp://guest:guest@rabbitmq:5672", env="RABBITMQ_URL"
    )

    # TON Testnet
    TON_NETWORK: str = "testnet"
    TON_ENDPOINT: str = "https://testnet.toncenter.com/api/v2/jsonRPC"
    TON_API_KEY: Optional[str] = Field(default=None, env="TON_API_KEY")

    # Testnet Jetton (will be deployed)
    MAFIA_JETTON_MASTER_ADDRESS: Optional[str] = Field(
        default=None, env="MAFIA_JETTON_MASTER_ADDRESS"
    )
    SERVICE_WALLET_MNEMONIC: Optional[str] = Field(
        default=None, env="SERVICE_WALLET_MNEMONIC"
    )

    # Services
    MEDIASOUP_URL: str = "http://voice-server:4443"

    # Security
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    WALLET_ENCRYPTION_KEY: str = Field(..., env="WALLET_ENCRYPTION_KEY")

    # Features
    AUTO_CREATE_WALLET: bool = True
    USE_TESTNET_FAUCET: bool = True

    # Telegram
    TELEGRAM_BOT_TOKEN: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBAPP_URL: str = Field(
        default="https://t.me/mafia_test_bot/app", env="TELEGRAM_WEBAPP_URL"
    )

    class Config:
        env_file = ".env.dev"


class StagingConfig(BaseSettings):
    """Staging environment - production-like with testnet"""

    ENV: str = "staging"

    # Production-like infrastructure
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field(..., env="REDIS_URL")
    RABBITMQ_URL: str = Field(..., env="RABBITMQ_URL")

    # TON Testnet (but production config)
    TON_NETWORK: str = "testnet"
    TON_ENDPOINT: str = Field(..., env="TON_ENDPOINT")
    TON_API_KEY: str = Field(..., env="TON_API_KEY")

    # Staging Jetton
    MAFIA_JETTON_MASTER_ADDRESS: str = Field(..., env="MAFIA_JETTON_MASTER_ADDRESS")
    SERVICE_WALLET_MNEMONIC: str = Field(..., env="SERVICE_WALLET_MNEMONIC")

    # Services with load balancing
    MEDIASOUP_URL: str = Field(..., env="MEDIASOUP_URL")
    MEDIASOUP_WORKERS: int = Field(default=10, env="MEDIASOUP_WORKERS")

    # Security (production-grade)
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    WALLET_ENCRYPTION_KEY: str = Field(..., env="WALLET_ENCRYPTION_KEY")

    # Features
    AUTO_CREATE_WALLET: bool = False
    REQUIRE_KYC: bool = True

    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")

    class Config:
        env_file = ".env.staging"


class ProdConfig(BaseSettings):
    """Production environment with TON mainnet"""

    ENV: str = "prod"

    # Production infrastructure
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field(..., env="REDIS_URL")
    RABBITMQ_URL: str = Field(..., env="RABBITMQ_URL")

    # TON Mainnet
    TON_NETWORK: str = "mainnet"
    TON_ENDPOINT: str = Field(
        default="https://toncenter.com/api/v2/jsonRPC", env="TON_ENDPOINT"
    )
    TON_API_KEY: str = Field(..., env="TON_API_KEY")

    # Production Jetton
    MAFIA_JETTON_MASTER_ADDRESS: str = Field(..., env="MAFIA_JETTON_MASTER_ADDRESS")
    SERVICE_WALLET_MNEMONIC: str = Field(..., env="SERVICE_WALLET_MNEMONIC")

    # Services with full scaling
    MEDIASOUP_URL: str = Field(..., env="MEDIASOUP_URL")
    MEDIASOUP_WORKERS: int = Field(default=20, env="MEDIASOUP_WORKERS")

    # Security (maximum)
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    WALLET_ENCRYPTION_KEY: str = Field(..., env="WALLET_ENCRYPTION_KEY")
    REQUIRE_2FA: bool = True

    # Features
    AUTO_CREATE_WALLET: bool = False
    REQUIRE_KYC: bool = True
    AUDIT_MODE: bool = True

    # Monitoring & Analytics
    SENTRY_DSN: str = Field(..., env="SENTRY_DSN")
    AMPLITUDE_API_KEY: Optional[str] = Field(default=None, env="AMPLITUDE_API_KEY")

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = 60
    MAX_WITHDRAWALS_PER_DAY: int = 3

    class Config:
        env_file = ".env.prod"


def get_settings() -> BaseSettings:
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
