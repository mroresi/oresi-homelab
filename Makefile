.PHONY: help venv install lint type test format build docker-run dev compose up down pre-commit

VENV ?= ./.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
UVICORN := $(VENV)/bin/uvicorn

help:
	@echo "Targets:"
	@echo "  venv         - create local virtualenv"
	@echo "  install      - install ChatOps deps into venv"
	@echo "  lint         - run ruff on repo"
	@echo "  type         - run mypy on chatops"
	@echo "  test         - run pytest for chatops"
	@echo "  format       - ruff --fix"
	@echo "  build        - docker build chatops image"
	@echo "  docker-run   - run chatops image (port 8000)"
	@echo "  dev          - run uvicorn chatops locally"
	@echo "  compose      - run example compose (uses GHCR image)"
	@echo "  up/down      - docker compose up/down for example"
	@echo "  pre-commit   - install and run pre-commit hooks once"
	@echo "  security     - run Trivy filesystem scan via Docker"
	@echo "  bandit       - install and run Bandit on chatops/"
	@echo "  genkey       - generate secure API key and write to chatops/.env"

venv:
	python3 -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r chatops/requirements.txt

lint:
	$(RUFF) check .

type:
	$(MYPY) --install-types --non-interactive chatops

test:
	$(PYTEST) -q chatops

format:
	$(RUFF) check --fix .

build:
	docker build -t oresi-chatops:dev -f chatops/Dockerfile .

docker-run:
	docker run --rm -e CHATOPS_API_KEY=$${CHATOPS_API_KEY:-devkey} -p 8000:8000 oresi-chatops:dev

dev:
	CHATOPS_API_KEY=$${CHATOPS_API_KEY:-devkey} $(UVICORN) chatops.main:app --reload --port 8000

compose:
	cp -n chatops/.env.example chatops/.env || true
	docker compose -f chatops/docker-compose.example.yml up -d

up:
	docker compose -f chatops/docker-compose.example.yml up -d

down:
	docker compose -f chatops/docker-compose.example.yml down

pre-commit:
	$(PIP) install pre-commit
	pre-commit install
	pre-commit run --all-files || true

security:
	@docker run --rm -v $(PWD):/src:ro aquasec/trivy:latest fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --exit-code 0 /src || true

bandit:
	$(PIP) install bandit
	$(VENV)/bin/bandit -q -r chatops -ll || true

genkey:
	@KEY=$$(openssl rand -base64 32); \
	echo "CHATOPS_API_KEY=$$KEY" > chatops/.env; \
	echo "Generated API key written to chatops/.env"
