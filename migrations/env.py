import os
import sys
import pathlib
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Подготовим PYTHONPATH
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Важно: app.__init__ теперь лёгкий
from app import Base

# ЯВНО импортируем модули с моделями (без сервисов!)
import importlib

# Список модулей моделей, которые надо прогрузить для target_metadata
MODEL_MODULES = [
    "app.domains.auth.models",
    "app.domains.economy.models",
    "app.domains.game.models",
    "app.domains.skins.models",
    "app.domains.social.models",
    "app.domains.voice.models",
]

for mod in MODEL_MODULES:
    importlib.import_module(mod)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

db_url = (
    os.environ.get("ALEMBIC_SYNC_DB_URL")
    or os.environ.get("DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)

if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "+psycopg2")

config.set_main_option("sqlalchemy.url", db_url)
config.compare_type = True
config.compare_server_default = True


def run_migrations_offline() -> None:
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


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
