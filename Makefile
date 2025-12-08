# Raido - AI Pirate Radio Makefile

.PHONY: help setup up down build clean logs shell test lint format disk-usage clean-caches clean-dev

# Prefer Docker Compose v2 plugin; override with `make COMPOSE=docker-compose ...` if needed
COMPOSE ?= docker compose

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BLUE)🏴‍☠️ Raido - AI Pirate Radio$(RESET)"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Initial setup - copy env file and create directories
	@echo "$(BLUE)Setting up Raido...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)Created .env file from .env.example$(RESET)"; \
		echo "$(YELLOW)Please edit .env with your actual configuration!$(RESET)"; \
	else \
		echo "$(GREEN).env file already exists$(RESET)"; \
	fi
	@mkdir -p music shared/tts shared/logs
	@echo "$(GREEN)Setup complete!$(RESET)"

build: ## Build all services
	@echo "$(BLUE)Building all services...$(RESET)"
	$(COMPOSE) build

up: ## Start all services
	@echo "$(BLUE)🏴‍☠️ Starting Raido Pirate Radio...$(RESET)"
	$(COMPOSE) up -d
	@echo "$(GREEN)Raido is sailing! 🚢$(RESET)"
	@echo ""
	@echo "$(YELLOW)Services:$(RESET)"
	@echo "  • Web UI: http://localhost:3000"
	@echo "  • API: http://localhost:8000"
	@echo "  • Stream: http://localhost:8000/raido.mp3"
	@echo "  • Icecast Admin: http://localhost:8000/admin/"
	@echo "  • Database Admin: http://localhost:8080"

up-dev: ## Start services in development mode with live reload
	@echo "$(BLUE)🏴‍☠️ Starting Raido in development mode...$(RESET)"
	$(COMPOSE) -f docker-compose.yml -f docker-compose.override.yml up -d api web-dev proxy icecast liquidsoap
	@echo "$(GREEN)Development environment ready!$(RESET)"

down-dev: ## Stop dev stack and remove orphans
	@echo "$(BLUE)Stopping Raido dev stack...$(RESET)"
	$(COMPOSE) -f docker-compose.yml -f docker-compose.override.yml down --remove-orphans
	@echo "$(GREEN)Dev stack stopped$(RESET)"

restart-web: ## Restart frontend dev server (web-dev)
	@echo "$(BLUE)Restarting web-dev...$(RESET)"
	$(COMPOSE) -f docker-compose.yml -f docker-compose.override.yml restart web-dev
	@echo "$(GREEN)web-dev restarted$(RESET)"

restart-api: ## Restart API dev server
	@echo "$(BLUE)Restarting api...$(RESET)"
	$(COMPOSE) -f docker-compose.yml -f docker-compose.override.yml restart api
	@echo "$(GREEN)api restarted$(RESET)"

restart-dev: ## Restart API, web-dev, and proxy
	@echo "$(BLUE)Restarting dev services (api, web-dev, proxy)...$(RESET)"
	$(COMPOSE) -f docker-compose.yml -f docker-compose.override.yml restart api web-dev proxy
	@echo "$(GREEN)Dev services restarted$(RESET)"

logs-web: ## Tail web-dev logs
	$(COMPOSE) -f docker-compose.yml -f docker-compose.override.yml logs -f web-dev

logs-proxy: ## Tail proxy logs
	$(COMPOSE) -f docker-compose.yml -f docker-compose.override.yml logs -f proxy

logs-api: ## Tail api logs
	$(COMPOSE) -f docker-compose.yml -f docker-compose.override.yml logs -f api

down: ## Stop all services
	@echo "$(BLUE)Stopping Raido...$(RESET)"
	$(COMPOSE) down
	@echo "$(GREEN)All services stopped$(RESET)"

stop: ## Stop services but keep containers
	@echo "$(BLUE)Pausing Raido...$(RESET)"
	$(COMPOSE) stop
	@echo "$(GREEN)Services paused$(RESET)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting Raido...$(RESET)"
	$(COMPOSE) restart
	@echo "$(GREEN)Services restarted$(RESET)"

logs: ## Show logs from all services
	 $(COMPOSE) logs -f

logs-api: ## Show API service logs
	$(COMPOSE) logs -f api

logs-dj: ## Show DJ worker logs
	$(COMPOSE) logs -f dj-worker

logs-liquidsoap: ## Show Liquidsoap logs
	$(COMPOSE) logs -f liquidsoap

logs-web: ## Show web frontend logs
	$(COMPOSE) logs -f web

logs-xtts: ## Show XTTS server logs
	$(COMPOSE) logs -f xtts-server

shell-api: ## Open shell in API container
	$(COMPOSE) exec api bash

shell-dj: ## Open shell in DJ worker container
	$(COMPOSE) exec dj-worker bash

shell-db: ## Open PostgreSQL shell
	$(COMPOSE) exec db psql -U raido -d raido

clean: ## Clean up containers, volumes, and images
	@echo "$(YELLOW)Cleaning up Docker resources...$(RESET)"
	$(COMPOSE) down -v --remove-orphans
	$(COMPOSE) rm -f
	docker volume prune -f
	docker image prune -f
	@echo "$(GREEN)Cleanup complete$(RESET)"

clean-all: ## Nuclear cleanup - remove everything including images
	@echo "$(RED)⚠️  Nuclear cleanup - this will remove ALL Raido data!$(RESET)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(COMPOSE) down -v --remove-orphans --rmi all; \
		docker volume rm $$(docker volume ls -q | grep raido) 2>/dev/null || true; \
		rm -rf music/* shared/* || true; \
		echo "$(GREEN)Nuclear cleanup complete$(RESET)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(RESET)"; \
	fi

disk-usage: ## Show largest items in repo
	@echo "$(BLUE)Top-level disk usage:$(RESET)"
	@du -sh . .git 2>/dev/null || true
	@du -sh * .[^.]* 2>/dev/null | sort -hr | head -n 20 || true

clean-caches: ## Remove caches, build artifacts, logs (safe)
	@echo "$(BLUE)Cleaning caches, build artifacts, and logs...$(RESET)"
	@bash scripts/cleanup.sh --caches --logs --report --yes

clean-dev: ## Remove caches, logs, TTS, node_modules, and .venv (destructive)
	@echo "$(RED)⚠️  This will remove node_modules and .venv.$(RESET)"
	@read -p "Proceed with developer cleanup? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		FORCE=1 bash scripts/cleanup.sh --caches --logs --tts --node --venv --report; \
	else \
		echo "$(YELLOW)Developer cleanup cancelled$(RESET)"; \
	fi

status: ## Show status of all services
	@echo "$(BLUE)Raido Service Status:$(RESET)"
	@$(COMPOSE) ps

health: ## Check health of all services
	@echo "$(BLUE)Health Check:$(RESET)"
	@echo -n "API: "
	@curl -s http://localhost:8001/health | grep -o '"status":"[^"]*"' || echo "$(RED)❌ Down$(RESET)"
	@echo -n "Web: "
	@curl -s http://localhost:3000/health >/dev/null && echo "$(GREEN)✅ Up$(RESET)" || echo "$(RED)❌ Down$(RESET)"
	@echo -n "Stream: "
		@curl -s --fail -r 0-0 http://localhost:8000/raido.mp3 -o /dev/null && echo "$(GREEN)✅ Live$(RESET)" || echo "$(RED)❌ Offline$(RESET)"

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(RESET)"
	$(COMPOSE) exec api alembic upgrade head
	@echo "$(GREEN)Migrations complete$(RESET)"

migrate-create: ## Create a new migration (usage: make migrate-create name=migration_name)
	@if [ -z "$(name)" ]; then \
		echo "$(RED)Error: Please provide a migration name$(RESET)"; \
		echo "Usage: make migrate-create name=migration_name"; \
		exit 1; \
	fi
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(name)"

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(RESET)"
	@$(MAKE) test-backend
	@$(MAKE) test-frontend
	@echo "$(GREEN)All tests completed!$(RESET)"

test-backend: ## Run backend tests (API + DJ Worker)
	@echo "$(BLUE)Running backend tests...$(RESET)"
	@$(MAKE) test-api
	@$(MAKE) test-dj-worker

test-api: ## Run API service tests
	@echo "$(BLUE)Running API tests...$(RESET)"
	@if [ -d "services/api/tests" ]; then \
		$(COMPOSE) exec api pytest tests/ -v --cov=app --cov-report=term-missing || \
		docker run --rm -v $(PWD)/services/api:/app -w /app python:3.11 bash -c "pip install -q -r requirements.txt -r requirements-dev.txt && pytest tests/ -v"; \
	else \
		echo "$(YELLOW)No API tests found$(RESET)"; \
	fi

test-dj-worker: ## Run DJ Worker tests
	@echo "$(BLUE)Running DJ Worker tests...$(RESET)"
	@if [ -d "services/dj-worker/tests" ]; then \
		$(COMPOSE) exec dj-worker pytest tests/ -v --cov=app --cov-report=term-missing || \
		docker run --rm -v $(PWD)/services/dj-worker:/app -w /app python:3.11 bash -c "pip install -q -r requirements.txt -r requirements-dev.txt && pytest tests/ -v"; \
	else \
		echo "$(YELLOW)No DJ Worker tests found$(RESET)"; \
	fi

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(RESET)"
	@if [ -d "web/src/__tests__" ]; then \
		cd web && npm run test || echo "$(RED)Frontend tests failed$(RESET)"; \
	else \
		echo "$(YELLOW)No frontend tests found$(RESET)"; \
	fi

test-integration: ## Run integration tests (requires running services)
	@echo "$(BLUE)Running integration tests...$(RESET)"
	@echo "$(YELLOW)Ensure services are running (make up-dev)$(RESET)"
	@if [ -d "tests" ]; then \
		python -m pytest tests/ -v -m integration || \
		echo "$(RED)Integration tests failed or skipped$(RESET)"; \
	else \
		echo "$(YELLOW)No integration tests found$(RESET)"; \
	fi

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(RESET)"
	@if [ -d "services/api/tests" ]; then \
		$(COMPOSE) exec api pytest tests/ -v -m unit --cov=app || true; \
	fi
	@if [ -d "services/dj-worker/tests" ]; then \
		$(COMPOSE) exec dj-worker pytest tests/ -v -m unit --cov=app || true; \
	fi
	@cd web && npm run test -- --run || true

test-coverage: ## Generate test coverage reports
	@echo "$(BLUE)Generating test coverage reports...$(RESET)"
	@mkdir -p coverage
	@$(COMPOSE) exec api pytest tests/ --cov=app --cov-report=html --cov-report=xml || true
	@$(COMPOSE) exec dj-worker pytest tests/ --cov=app --cov-report=html --cov-report=xml || true
	@echo "$(GREEN)Coverage reports generated in htmlcov/ directories$(RESET)"

test-watch: ## Run frontend tests in watch mode
	@echo "$(BLUE)Running frontend tests in watch mode...$(RESET)"
	@cd web && npm run test:watch

lint: ## Run linting
	@echo "$(BLUE)Running linters...$(RESET)"
	# Backend linting
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check services/api/app services/dj-worker/app; \
	else \
		echo "$(YELLOW)Ruff not installed, skipping Python linting$(RESET)"; \
	fi
	# Frontend linting
	@if [ -d "web/node_modules" ]; then \
		cd web && npm run lint; \
	else \
		echo "$(YELLOW)Node modules not found, skipping frontend linting$(RESET)"; \
	fi

format: ## Format code
	@echo "$(BLUE)Formatting code...$(RESET)"
	# Backend formatting
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format services/api/app services/dj-worker/app; \
	fi
	# Frontend formatting
	@if [ -d "web/node_modules" ]; then \
		cd web && npm run lint:fix; \
	fi

backup-db: ## Backup database
	@echo "$(BLUE)Creating database backup...$(RESET)"
	@mkdir -p backups
	@$(COMPOSE) exec -T db pg_dump -U raido raido | gzip > backups/raido_backup_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)Database backup created in backups/ directory$(RESET)"

restore-db: ## Restore database from backup (usage: make restore-db file=backup_file.sql.gz)
	@if [ -z "$(file)" ]; then \
		echo "$(RED)Error: Please provide a backup file$(RESET)"; \
		echo "Usage: make restore-db file=backup_file.sql.gz"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restoring database from $(file)...$(RESET)"
	@gunzip -c $(file) | $(COMPOSE) exec -T db psql -U raido -d raido
	@echo "$(GREEN)Database restored$(RESET)"

install-music: ## Add sample music files (for development)
	@echo "$(BLUE)Setting up sample music...$(RESET)"
	@mkdir -p music
	@echo "$(YELLOW)Please add your music files to the ./music directory$(RESET)"
	@echo "$(YELLOW)Supported formats: MP3, FLAC, OGG, WAV$(RESET)"

monitoring: ## Show resource usage
	@echo "$(BLUE)Resource Usage:$(RESET)"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

update: ## Update all services
	@echo "$(BLUE)Updating Raido...$(RESET)"
	git pull
	$(COMPOSE) pull
	$(COMPOSE) build --pull
	$(MAKE) migrate
	@echo "$(GREEN)Update complete!$(RESET)"

dev-setup: ## Complete development setup
	$(MAKE) setup
	$(MAKE) build
	$(MAKE) up-dev
	$(MAKE) migrate
	@echo "$(GREEN)🏴‍☠️ Development environment ready!$(RESET)"
	@echo "$(YELLOW)Don't forget to add music files to ./music directory$(RESET)"

production-setup: ## Production deployment setup
	@echo "$(BLUE)Setting up production environment...$(RESET)"
	$(MAKE) setup
	@echo "$(YELLOW)Please configure production values in .env$(RESET)"
	@echo "$(YELLOW)Set secure passwords and API keys!$(RESET)"
	$(MAKE) build
	$(MAKE) up
	$(MAKE) migrate
	@echo "$(GREEN)Production setup complete!$(RESET)"
