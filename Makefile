# Makefile for ServiceNow Knowledge MCP Server (Python)

.PHONY: help install install-dev test test-cov lint format type-check clean run debug setup-env

# Default target
help:
	@echo "ServiceNow Knowledge MCP Server - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  setup-env     Create virtual environment and install dependencies"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  run           Run the MCP server"
	@echo "  debug         Run with debug logging"
	@echo "  test          Run tests"
	@echo "  test-cov      Run tests with coverage"
	@echo "  lint          Run all linters"
	@echo "  format        Format code"
	@echo "  type-check    Run type checking"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean         Clean build artifacts"

# Environment setup
setup-env:
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  (Linux/macOS)"
	@echo "  venv\\Scripts\\activate     (Windows)"
	@echo "Then run: make install-dev"

install:
	pip install -r requirements.txt

install-dev:
	pip install -e ".[dev]"

# Running
run:
	python -m servicenow_mcp_server.main

debug:
	LOG_LEVEL=debug python -m servicenow_mcp_server.main

# Testing
test:
	pytest

test-cov:
	pytest --cov=servicenow_mcp_server --cov-report=html --cov-report=term

test-watch:
	pytest-watch

# Code quality
lint: flake8 mypy

format:
	black servicenow_mcp_server/ tests/
	isort servicenow_mcp_server/ tests/

format-check:
	black --check servicenow_mcp_server/ tests/
	isort --check-only servicenow_mcp_server/ tests/

flake8:
	flake8 servicenow_mcp_server/ tests/

mypy:
	mypy servicenow_mcp_server/

type-check: mypy

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build
build:
	python -m build

# Security
security-check:
	safety check
	bandit -r servicenow_mcp_server/

# Documentation
docs:
	@echo "Documentation files:"
	@echo "  README_PYTHON.md      - Main Python documentation"
	@echo "  QUICKSTART_PYTHON.md  - Quick start guide"
	@echo "  README.md             - Original TypeScript documentation"

# Development workflow
dev-setup: setup-env install-dev
	@echo "Development environment ready!"
	@echo "Don't forget to:"
	@echo "1. Activate virtual environment"
	@echo "2. Copy .env.example to .env"
	@echo "3. Configure your environment variables"

check-all: format-check lint test
	@echo "All checks passed!"

# CI/CD helpers
ci-install:
	pip install -r requirements.txt
	pip install -e ".[dev]"

ci-test: test-cov lint
	@echo "CI tests completed"

# Quick commands for common workflows
quick-test: format test

quick-check: format lint type-check

# Container commands (if using Docker)
docker-build:
	docker build -t servicenow-mcp-server .

docker-run:
	docker run --env-file .env servicenow-mcp-server
