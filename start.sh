#!/bin/sh

# Применение миграций
alembic upgrade head

# Запуск сервера
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --no-access-log