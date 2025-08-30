# Raido - AI Pirate Radio Makefile

.PHONY: help setup up down build clean logs shell test lint format

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
	docker-compose build

up: ## Start all services
	@echo "$(BLUE)🏴‍☠️ Starting Raido Pirate Radio...$(RESET)"
	docker-compose up -d
	@echo "$(GREEN)Raido is sailing! 🚢$(RESET)"
	@echo ""
	@echo "$(YELLOW)Services:$(RESET)"
	@echo "  • Web UI: http://localhost:3000"
	@echo "  • API: http://localhost:8000"
	@echo "  • Stream: http://localhost:8000/stream/raido.mp3"
	@echo "  • Icecast Admin: http://localhost:8000/admin/"
	@echo "  • Database Admin: http://localhost:8080"

up-dev: ## Start services in development mode with live reload
	@echo "$(BLUE)🏴‍☠️ Starting Raido in development mode...$(RESET)"
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
	@echo "$(GREEN)Development environment ready!$(RESET)"

down: ## Stop all services
	@echo "$(BLUE)Stopping Raido...$(RESET)"
	docker-compose down
	@echo "$(GREEN)All services stopped$(RESET)"

stop: ## Stop services but keep containers
	@echo "$(BLUE)Pausing Raido...$(RESET)"
	docker-compose stop
	@echo "$(GREEN)Services paused$(RESET)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting Raido...$(RESET)"
	docker-compose restart
	@echo "$(GREEN)Services restarted$(RESET)"

logs: ## Show logs from all services
	docker-compose logs -f

logs-api: ## Show API service logs
	docker-compose logs -f api

logs-dj: ## Show DJ worker logs
	docker-compose logs -f dj-worker

logs-liquidsoap: ## Show Liquidsoap logs
	docker-compose logs -f liquidsoap

logs-web: ## Show web frontend logs
	docker-compose logs -f web

shell-api: ## Open shell in API container
	docker-compose exec api bash

shell-dj: ## Open shell in DJ worker container
	docker-compose exec dj-worker bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec db psql -U raido -d raido

clean: ## Clean up containers, volumes, and images
	@echo "$(YELLOW)Cleaning up Docker resources...$(RESET)"
	docker-compose down -v --remove-orphans
	docker-compose rm -f
	docker volume prune -f
	docker image prune -f
	@echo "$(GREEN)Cleanup complete$(RESET)"

clean-all: ## Nuclear cleanup - remove everything including images
	@echo "$(RED)⚠️  Nuclear cleanup - this will remove ALL Raido data!$(RESET)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --remove-orphans --rmi all; \
		docker volume rm $$(docker volume ls -q | grep raido) 2>/dev/null || true; \
		rm -rf music/* shared/* || true; \
		echo "$(GREEN)Nuclear cleanup complete$(RESET)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(RESET)"; \
	fi

status: ## Show status of all services
	@echo "$(BLUE)Raido Service Status:$(RESET)"
	@docker-compose ps

health: ## Check health of all services
	@echo "$(BLUE)Health Check:$(RESET)"
	@echo -n "API: "
	@curl -s http://localhost:8001/health | grep -o '"status":"[^"]*"' || echo "$(RED)❌ Down$(RESET)"
	@echo -n "Web: "
	@curl -s http://localhost:3000/health >/dev/null && echo "$(GREEN)✅ Up$(RESET)" || echo "$(RED)❌ Down$(RESET)"
	@echo -n "Stream: "
	@curl -s --fail -r 0-0 http://localhost:8000/stream/raido.mp3 -o /dev/null && echo "$(GREEN)✅ Live$(RESET)" || echo "$(RED)❌ Offline$(RESET)"

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(RESET)"
	docker-compose exec api alembic upgrade head
	@echo "$(GREEN)Migrations complete$(RESET)"

migrate-create: ## Create a new migration (usage: make migrate-create name=migration_name)
	@if [ -z "$(name)" ]; then \
		echo "$(RED)Error: Please provide a migration name$(RESET)"; \
		echo "Usage: make migrate-create name=migration_name"; \
		exit 1; \
	fi
	docker-compose exec api alembic revision --autogenerate -m "$(name)"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(RESET)"
	# TODO: Add test commands once tests are implemented
	@echo "$(YELLOW)Tests not yet implemented$(RESET)"

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
	@docker-compose exec -T db pg_dump -U raido raido | gzip > backups/raido_backup_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)Database backup created in backups/ directory$(RESET)"

restore-db: ## Restore database from backup (usage: make restore-db file=backup_file.sql.gz)
	@if [ -z "$(file)" ]; then \
		echo "$(RED)Error: Please provide a backup file$(RESET)"; \
		echo "Usage: make restore-db file=backup_file.sql.gz"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restoring database from $(file)...$(RESET)"
	@gunzip -c $(file) | docker-compose exec -T db psql -U raido -d raido
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
	docker-compose pull
	docker-compose build --pull
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
