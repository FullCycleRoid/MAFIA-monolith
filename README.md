# MAFIA-monolith
Monolith MAFIA fastapi backend


1. Начало работы (локальная разработка)
# Установка зависимостей
make setup ENVIRONMENT=local
make install-ton-tools

# Запуск локального окружения с TON sandbox
make local-up

# Проверка здоровья сервисов
make health ENVIRONMENT=local

# Запуск тестов
make local-test


2. Переход на testnet (dev)
cp .env.dev.example .env.dev
# Отредактируйте .env.dev с вашими ключами

# Запуск dev окружения
make dev-up

# Получение тестовых TON
make dev-get-tons

# Деплой jetton на testnet
make dev-deploy-jetton

# Проверка баланса
make ton-balance ENVIRONMENT=dev


3. Staging (предпродакшн)
# Настройка staging
cp .env.staging.example .env.staging
# Настройте production-like инфраструктуру

# Деплой на staging
make staging-deploy

# Запуск миграций
make staging-migrate


4. Production (mainnet)

# Проверка готовности к production
make prod-check

# Деплой (требует подтверждения)
make prod-deploy VERSION=1.0.0