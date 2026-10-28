COMPOSE := docker compose --project-name prism-phase3-reference -f compose.yaml -f compose.phase3.yaml
PYTHON ?= .venv/bin/python
.DEFAULT_GOAL := help

.PHONY: help check-env build up dev status logs restart stop down test
help:
	@echo "PRISM: make up | status | logs | restart | stop | down | test"
	@echo "Application: http://127.0.0.1:5050 (Docker)"
	@echo "Local development: make dev (http://127.0.0.1:5051)"

check-env:
	@test -f .env || (echo "Copy .env.example to .env and set the three secrets first."; exit 1)

build: check-env
	$(COMPOSE) build web

up: build
	$(COMPOSE) up -d postgres redis neo4j
	$(COMPOSE) run --rm initialize
	$(COMPOSE) up -d --no-build web worker beat collector

dev: build
	$(COMPOSE) up -d postgres redis neo4j
	$(COMPOSE) run --rm initialize
	$(COMPOSE) up -d --no-build worker beat collector
	$(PYTHON) -m prism

status:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs --tail=100 -f web worker collector

restart: build
	$(COMPOSE) up -d --no-build --no-deps web

stop:
	$(COMPOSE) stop

down:
	$(COMPOSE) down

test:
	$(PYTHON) -m unittest discover -s tests -v
