.DEFAULT_GOAL := help

.PHONY: help install lint format typecheck test test-cov run docker-up docker-down clean

help: ## Display available targets
	@awk 'BEGIN {FS = ":.*##"; printf "\n%-15s %s\n%-15s %s\n", "Target", "Description", "------", "-----------"} /^[a-zA-Z_-]+:.*##/ {printf "%-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: ## Install all dependencies
	pip install -r requirements.txt -r requirements-dev.txt

lint: ## Run ruff linter
	ruff check .

format: ## Format code with ruff
	ruff format .

typecheck: ## Run mypy type checker
	mypy app cli

test: ## Run tests with verbose output
	pytest -v

test-cov: ## Run tests with coverage report
	pytest --cov --cov-report=term-missing --cov-report=html

run: ## Start uvicorn dev server on port 9000
	uvicorn app.main:app --reload --port 9000

docker-up: ## Build and start containers
	docker compose up --build -d

docker-down: ## Stop containers and remove volumes
	docker compose down -v

clean: ## Remove build and cache artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
