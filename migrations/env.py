from logging.config import fileConfig
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import asyncio
import sys
import os
import socket

sys.path.append(os.getcwd())
from app.core.config import settings
from app.domains.voice.models import *

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# # Определяем URL базы данных в зависимости от окружения
# if socket.gethostname() in ['postgres-local', 'docker-postgres-local-1']:  # Замените на имя вашего хоста
#     # Для локального запуска вне Docker
# db_url = "postgresql+asyncpg://postgres:postgres@localhost:5433/mafia_local"
# else:
#     # Для запуска внутри Docker
db_url = settings.DATABASE_URL

config.set_main_option("sqlalchemy.url", db_url)
print(f"Using database URL: {db_url}")  # Добавьте для отладки

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    # Используем явное создание движка с таймаутом
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
        connect_args={"timeout": 30}
    )

    async with connectable.connect() as connection:
        await connection.execute(text("SET search_path TO public"))
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()