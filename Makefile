SHELL := /bin/bash

COMPOSE ?= docker compose
FRONTEND_DIR := frontend
PYTEST_ARGS ?= tests/ -v

.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@echo "  install           Install backend dependencies with Poetry"
	@echo "  install-frontend  Install frontend dependencies with npm"
	@echo "  run               Run backend main module locally"
	@echo "  run-api           Run FastAPI locally with reload"
	@echo "  run-frontend      Run Next.js frontend locally"
	@echo "  test              Run backend tests locally with Poetry"
	@echo "  test-cov          Run backend tests with coverage locally"
	@echo "  test-smoke        Run smoke suite locally (pytest -m smoke)"
	@echo "  test-unit         Run non-smoke suite locally (pytest -m 'not smoke')"
	@echo "  test-docker       Run backend tests in Docker using backend-test"
	@echo "  test-smoke-docker Run smoke suite in Docker"
	@echo "  test-unit-docker  Run non-smoke suite in Docker"
	@echo "  lint              Run Ruff checks"
	@echo "  format            Run Ruff format and Black"
	@echo "  build             Build Docker images"
	@echo "  up                Start the Docker stack in background"
	@echo "  down              Stop the Docker stack"
	@echo "  restart           Restart the Docker stack"
	@echo "  ps                Show Docker Compose service status"
	@echo "  logs              Follow Docker Compose logs"
	@echo "  logs-backend      Follow backend logs"
	@echo "  up-test           Start the Docker stack and run backend tests"
	@echo "  clean             Remove Python cache files"

install:
	poetry install

install-frontend:
	cd $(FRONTEND_DIR) && npm install

run:
	poetry run python -m backend.src.main

run-api:
	poetry run uvicorn backend.src.api:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd $(FRONTEND_DIR) && npm run dev

test:
	poetry run pytest $(PYTEST_ARGS)

test-cov:
	poetry run pytest tests/ --cov=backend.src

test-smoke:
	poetry run pytest -m smoke -q

test-unit:
	poetry run pytest -m "not smoke" -q

test-docker:
	$(COMPOSE) --profile test run --rm -e PYTHONPATH=/app backend-test

test-smoke-docker:
	$(COMPOSE) --profile test run --rm -e PYTHONPATH=/app backend-test pytest -q -m smoke

test-unit-docker:
	$(COMPOSE) --profile test run --rm -e PYTHONPATH=/app backend-test pytest -q -m "not smoke"

lint:
	poetry run ruff check .

format:
	poetry run ruff format .
	poetry run black .

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart: down up

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

logs-backend:
	$(COMPOSE) logs -f backend

up-test: up test-docker

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +

.PHONY: help install install-frontend run run-api run-frontend test test-cov test-smoke test-unit test-docker test-smoke-docker test-unit-docker lint format build up down restart ps logs logs-backend up-test clean
