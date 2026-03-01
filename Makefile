.PHONY: help setup test test-verbose test-watch test-file clean lint format check

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Amplifier Module Connectors - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

setup: ## Set up development environment (venv, dependencies)
	@./scripts/setup.sh

test: ## Run all tests
	@./scripts/test.sh

test-verbose: ## Run tests with verbose output
	@./scripts/test.sh -vv

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@./scripts/test.sh --watch

test-file: ## Run tests for a specific file (usage: make test-file FILE=tests/test_project_manager.py)
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE not specified. Usage: make test-file FILE=tests/test_project_manager.py"; \
		exit 1; \
	fi
	@./scripts/test.sh $(FILE)

test-pattern: ## Run tests matching pattern (usage: make test-pattern PATTERN=project)
	@if [ -z "$(PATTERN)" ]; then \
		echo "Error: PATTERN not specified. Usage: make test-pattern PATTERN=project"; \
		exit 1; \
	fi
	@./scripts/test.sh -k $(PATTERN)

test-coverage: ## Run tests with coverage report
	@./scripts/test-coverage.sh

test-ci: ## Run tests in CI mode (JUnit XML output)
	@./scripts/test-ci.sh

clean: ## Clean up generated files
	@echo "Cleaning up..."
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned up"

lint: ## Run linting (requires ruff)
	@if command -v ruff &> /dev/null; then \
		echo "Running ruff..."; \
		ruff check src tests; \
	else \
		echo "Warning: ruff not installed. Install with: uv pip install ruff"; \
	fi

format: ## Format code (requires ruff)
	@if command -v ruff &> /dev/null; then \
		echo "Formatting code..."; \
		ruff format src tests; \
	else \
		echo "Warning: ruff not installed. Install with: uv pip install ruff"; \
	fi

check: lint test ## Run linting and tests

# Slack-specific targets
slack-start: ## Start Slack connector
	@source .venv/bin/activate && slack-connector start

slack-onboard: ## Run Slack onboarding
	@source .venv/bin/activate && slack-connector onboard

slack-daemon-start: ## Start Slack daemon
	@./manage-daemon.sh start

slack-daemon-stop: ## Stop Slack daemon
	@./manage-daemon.sh stop

slack-daemon-restart: ## Restart Slack daemon
	@./restart-daemon.sh

slack-logs: ## Tail Slack daemon logs
	@./tail-logs.sh
