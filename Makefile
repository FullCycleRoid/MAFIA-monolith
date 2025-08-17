# Makefile for MAFIA TON Project
# Multi-environment management

# Variables
ENVIRONMENT ?= local
VERSION ?= latest
DOCKER_REGISTRY ?= your-registry.com
PYTHON := python3
COMPOSE := docker compose
COMPOSE_FILE := docker-compose.$(ENVIRONMENT).yml

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

.PHONY: help
help: ## Show this help message
	@echo "$(GREEN)MAFIA TON Project - Environment Management$(NC)"
	@echo ""
	@echo "Usage: make [target] ENVIRONMENT=[local|dev|staging|prod]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ============= ENVIRONMENT SETUP =============

.PHONY: setup
setup: ## Setup environment (install dependencies, create .env files)
	@echo "$(YELLOW)Setting up $(ENVIRONMENT) environment...$(NC)"
	@cp .env.$(ENVIRONMENT).example .env.$(ENVIRONMENT) 2>/dev/null || true
	@$(PYTHON) -m venv venv
	@. venv/bin/activate && pip install -r requirements.txt
	@echo "$(GREEN)Environment setup complete!$(NC)"

.PHONY: install-ton-tools
install-ton-tools: ## Install TON development tools
	@echo "$(YELLOW)Installing TON tools...$(NC)"
	@npm install -g ton-compiler ton-contract-executor
	@pip install pytoniq pytoniq-core tonsdk
	@echo "$(GREEN)TON tools installed!$(NC)"

# ============= LOCAL DEVELOPMENT =============

.PHONY: local-up
local-up: ## Start local environment with TON sandbox
	@echo "$(YELLOW)Starting local environment with TON sandbox...$(NC)"
	@ENVIRONMENT=local $(COMPOSE) -f docker/docker-compose.local.yml up
	@sleep 5
	@make local-init
	@echo "$(GREEN)Local environment is running!$(NC)"
	@echo "Backend: http://localhost:8001"
	@echo "TON Sandbox: http://localhost:8082"

.PHONY: local-build
local-build: ## Start local environment with TON sandbox
	@echo "$(YELLOW)Starting build local environment with TON sandbox...$(NC)"
	@ENVIRONMENT=local $(COMPOSE) -f docker/docker-compose.local.yml build
	@sleep 10
	@echo "$(GREEN)Local environment was build"


.PHONY: local-down
local-down: ## Stop local environment
	@ENVIRONMENT=local $(COMPOSE) -f docker/docker-compose.local.yml down

.PHONY: local-init
local-init: ## Initialize local data and deploy test contracts
	@echo "$(YELLOW)Initializing local data...$(NC)"
	@ENVIRONMENT=local $(PYTHON) scripts/init_local_data.py
	@echo "$(GREEN)Local data initialized!$(NC)"

.PHONY: local-logs
local-logs: ## Show local environment logs
	@ENVIRONMENT=local $(COMPOSE) -f docker/docker-compose.local.yml logs -f

.PHONY: local-test
local-test: ## Run tests in local environment
	@echo "$(YELLOW)Running tests...$(NC)"
	@ENVIRONMENT=local pytest tests/ -v --cov=app --cov-report=term-missing

# ============= DEVELOPMENT (TESTNET) =============

.PHONY: dev-up
dev-up: ## Start development environment with TON testnet
	@echo "$(YELLOW)Starting dev environment with TON testnet...$(NC)"
	@ENVIRONMENT=dev $(COMPOSE) -f docker/docker-compose.dev.yml up -d
	@echo "$(GREEN)Dev environment is running!$(NC)"

.PHONY: dev-down
dev-down: ## Stop development environment
	@ENVIRONMENT=dev $(COMPOSE) -f docker/docker-compose.dev.yml down

.PHONY: dev-deploy-jetton
dev-deploy-jetton: ## Deploy jetton to testnet
	@echo "$(YELLOW)Deploying jetton to testnet...$(NC)"
	@ENVIRONMENT=dev $(PYTHON) scripts/deploy_testnet_jetton.py
	@echo "$(GREEN)Jetton deployed to testnet!$(NC)"

.PHONY: dev-get-tons
dev-get-tons: ## Get testnet TON from faucet
	@echo "$(YELLOW)Requesting testnet TON...$(NC)"
	@ENVIRONMENT=dev $(PYTHON) scripts/get_testnet_tons.py

.PHONY: dev-logs
dev-logs: ## Show dev environment logs
	@ENVIRONMENT=dev $(COMPOSE) -f docker/docker-compose.dev.yml logs -f $(service)

.PHONY: dev-shell
dev-shell: ## Open shell in dev backend container
	@ENVIRONMENT=dev $(COMPOSE) -f docker/docker-compose.dev.yml exec backend /bin/sh

# ============= STAGING =============

.PHONY: staging-up
staging-up: ## Start staging environment
	@echo "$(YELLOW)Starting staging environment...$(NC)"
	@ENVIRONMENT=staging $(COMPOSE) -f docker/docker-compose.staging.yml up -d
	@echo "$(GREEN)Staging environment is running!$(NC)"

.PHONY: staging-down
staging-down: ## Stop staging environment
	@ENVIRONMENT=staging $(COMPOSE) -f docker/docker-compose.staging.yml down

.PHONY: staging-deploy
staging-deploy: ## Deploy to staging
	@echo "$(YELLOW)Deploying to staging...$(NC)"
	@docker build -t $(DOCKER_REGISTRY)/mafia-backend:staging .
	@docker push $(DOCKER_REGISTRY)/mafia-backend:staging
	@ENVIRONMENT=staging $(COMPOSE) -f docker/docker-compose.staging.yml pull
	@ENVIRONMENT=staging $(COMPOSE) -f docker/docker-compose.staging.yml up -d
	@echo "$(GREEN)Deployed to staging!$(NC)"

.PHONY: staging-migrate
staging-migrate: ## Run migrations on staging
	@echo "$(YELLOW)Running staging migrations...$(NC)"
	@ENVIRONMENT=staging $(COMPOSE) -f docker/docker-compose.staging.yml exec backend alembic upgrade head

# ============= PRODUCTION =============

.PHONY: prod-deploy
prod-deploy: prod-check ## Deploy to production (requires confirmation)
	@echo "$(RED)⚠️  DEPLOYING TO PRODUCTION ⚠️$(NC)"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ]
	@echo "$(YELLOW)Building production images...$(NC)"
	@docker build -t $(DOCKER_REGISTRY)/mafia-backend:$(VERSION) -f docker/Dockerfile.prod .
	@docker build -t $(DOCKER_REGISTRY)/mafia-voice:$(VERSION) -f voice-server/Dockerfile voice-server/
	@echo "$(YELLOW)Pushing to registry...$(NC)"
	@docker push $(DOCKER_REGISTRY)/mafia-backend:$(VERSION)
	@docker push $(DOCKER_REGISTRY)/mafia-voice:$(VERSION)
	@echo "$(YELLOW)Deploying to production...$(NC)"
	@ENVIRONMENT=prod VERSION=$(VERSION) docker stack deploy -c docker-compose.prod.yml mafia
	@echo "$(GREEN)✅ Deployed to production!$(NC)"

.PHONY: prod-check
prod-check: ## Check production readiness
	@echo "$(YELLOW)Checking production readiness...$(NC)"
	@$(PYTHON) scripts/prod_check.py
	@echo "$(GREEN)Production checks passed!$(NC)"

.PHONY: prod-rollback
prod-rollback: ## Rollback production to previous version
	@echo "$(RED)Rolling back production...$(NC)"
	@read -p "Enter previous version: " prev_version && \
	ENVIRONMENT=prod VERSION=$$prev_version docker stack deploy -c docker-compose.prod.yml mafia
	@echo "$(GREEN)Rolled back successfully!$(NC)"

# ============= DATABASE =============

.PHONY: db-migrate
db-migrate: ## Run database migrations
	@echo "$(YELLOW)Running migrations for $(ENVIRONMENT)...$(NC)"
	@ENVIRONMENT=$(ENVIRONMENT) alembic upgrade head

.PHONY: db-rollback
db-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back migration for $(ENVIRONMENT)...$(NC)"
	@ENVIRONMENT=$(ENVIRONMENT) alembic downgrade -1

.PHONY: db-create-migration
db-create-migration: ## Create new migration
	@read -p "Migration name: " name && \
	ENVIRONMENT=$(ENVIRONMENT) alembic revision --autogenerate -m "$$name"

.PHONY: db-backup
db-backup: ## Backup database
	@echo "$(YELLOW)Backing up $(ENVIRONMENT) database...$(NC)"
	@./scripts/backup_db.sh $(ENVIRONMENT)
	@echo "$(GREEN)Backup complete!$(NC)"

# ============= TON BLOCKCHAIN =============

.PHONY: ton-balance
ton-balance: ## Check TON wallet balance
	@echo "$(YELLOW)Checking TON balance for $(ENVIRONMENT)...$(NC)"
	@ENVIRONMENT=$(ENVIRONMENT) $(PYTHON) scripts/check_balance.py

.PHONY: ton-deploy-jetton
ton-deploy-jetton: ## Deploy jetton contract
	@echo "$(YELLOW)Deploying jetton for $(ENVIRONMENT)...$(NC)"
	@ENVIRONMENT=$(ENVIRONMENT) $(PYTHON) scripts/jetton/deploy_jetton.py

.PHONY: ton-mint
ton-mint: ## Mint tokens (dev/staging only)
	@if [ "$(ENVIRONMENT)" = "prod" ]; then \
		echo "$(RED)Cannot mint in production!$(NC)"; \
		exit 1; \
	fi
	@read -p "Amount to mint: " amount && \
	read -p "Recipient address: " address && \
	ENVIRONMENT=$(ENVIRONMENT) $(PYTHON) scripts/jetton/mint_tokens.py $$amount $$address

# ============= MONITORING =============

.PHONY: monitor
monitor: ## Open monitoring dashboard
	@echo "$(YELLOW)Opening monitoring for $(ENVIRONMENT)...$(NC)"
	@if [ "$(ENVIRONMENT)" = "local" ]; then \
		open http://localhost:15673; \
		open http://localhost:5555; \
	elif [ "$(ENVIRONMENT)" = "dev" ]; then \
		open http://localhost:15672; \
		open http://localhost:5555; \
	else \
		echo "Monitoring URL: https://monitoring.yourapp.com"; \
	fi

.PHONY: logs
logs: ## Show logs for all services
	@$(COMPOSE) -f $(COMPOSE_FILE) logs -f

.PHONY: health
health: ## Check health of all services
	@echo "$(YELLOW)Checking health for $(ENVIRONMENT)...$(NC)"
	@ENVIRONMENT=$(ENVIRONMENT) $(PYTHON) scripts/health_check.py

# ============= TESTING =============

.PHONY: test
test: ## Run all tests
	@echo "$(YELLOW)Running tests...$(NC)"
	@ENVIRONMENT=test pytest tests/ -v

.PHONY: test-unit
test-unit: ## Run unit tests
	@ENVIRONMENT=test pytest tests/unit/ -v

.PHONY: test-integration
test-integration: ## Run integration tests
	@ENVIRONMENT=test pytest tests/integration/ -v

.PHONY: test-ton
test-ton: ## Test TON integration
	@echo "$(YELLOW)Testing TON integration for $(ENVIRONMENT)...$(NC)"
	@ENVIRONMENT=$(ENVIRONMENT) $(PYTHON) scripts/jetton/test_ton.py

.PHONY: test-load
test-load: ## Run load tests
	@echo "$(YELLOW)Running load tests...$(NC)"
	@locust -f tests/load_test.py --host=http://localhost:8000

# ============= UTILITY =============

.PHONY: clean
clean: ## Clean up temporary files and caches
	@echo "$(YELLOW)Cleaning up...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf htmlcov
	@echo "$(GREEN)Cleaned!$(NC)"

.PHONY: format
format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	@black app/ tests/
	@isort app/ tests/
	@echo "$(GREEN)Code formatted!$(NC)"

.PHONY: lint
lint: ## Run linters
	@echo "$(YELLOW)Running linters...$(NC)"
	@flake8 app/ tests/
	@mypy app/
	@echo "$(GREEN)Linting complete!$(NC)"

.PHONY: security
security: ## Run security checks
	@echo "$(YELLOW)Running security checks...$(NC)"
	@bandit -r app/
	@safety check
	@echo "$(GREEN)Security checks complete!$(NC)"

# ============= CI/CD =============

.PHONY: ci
ci: lint test security ## Run CI pipeline locally
	@echo "$(GREEN)CI pipeline passed!$(NC)"

.PHONY: build
build: ## Build Docker images
	@echo "$(YELLOW)Building images for $(ENVIRONMENT)...$(NC)"
	@docker build -t mafia-backend:$(ENVIRONMENT) -f docker/Dockerfile.$(ENVIRONMENT) .
	@docker build -t mafia-voice:$(ENVIRONMENT) -f voice-server/Dockerfile voice-server/
	@echo "$(GREEN)Images built!$(NC)"

.PHONY: push
push: build ## Push images to registry
	@echo "$(YELLOW)Pushing images...$(NC)"
	@docker tag mafia-backend:$(ENVIRONMENT) $(DOCKER_REGISTRY)/mafia-backend:$(ENVIRONMENT)
	@docker tag mafia-voice:$(ENVIRONMENT) $(DOCKER_REGISTRY)/mafia-voice:$(ENVIRONMENT)
	@docker push $(DOCKER_REGISTRY)/mafia-backend:$(ENVIRONMENT)
	@docker push $(DOCKER_REGISTRY)/mafia-voice:$(ENVIRONMENT)
	@echo "$(GREEN)Images pushed!$(NC)"

# ============= QUICK COMMANDS =============

.PHONY: up
up: $(ENVIRONMENT)-up ## Quick start for current environment

.PHONY: down
down: $(ENVIRONMENT)-down ## Quick stop for current environment

.PHONY: restart
restart: down up ## Restart current environment

.PHONY: status
status: ## Show status of all services
	@$(COMPOSE) -f $(COMPOSE_FILE) ps

.PHONY: reset
reset: ## Reset environment (WARNING: deletes data)
	@echo "$(RED)⚠️  This will delete all data for $(ENVIRONMENT)!$(NC)"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ]
	@make down
	@docker volume prune -f
	@make up
	@echo "$(GREEN)Environment reset complete!$(NC)"

# Default target
.DEFAULT_GOAL := help