# Makefile for fastapi_ddd_template (full, Dockerfile in repo root)
# Usage examples:
#   make build                      # локальная сборка (--load)
#   make LOAD_LOCAL=false build     # CI: сборка с пушем
#   make push-ghcr                  # buildx push + сохранение digest
#   make up ENV_FILE=.env.dev       # docker compose with env file
#
# Override variables via env or cli:
#   make IMAGE=myimage TAG=1.2.3 COMPOSE_FILE=docker-compose.yml

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# -----------------------
# Configurable variables
# -----------------------

APP_DIR ?= app

# Image / build settings
IMAGE ?= fastapi_ddd_template_app
TAG ?= dev
FULL_IMAGE ?= $(IMAGE):$(TAG)

# GHCR (override GITHUB_USER or set env)
GITHUB_USER ?=
GHCR_REPO ?= ghcr.io/$(GITHUB_USER)/$(IMAGE)
GHCR_TAG ?= staging-$(shell git rev-parse --short HEAD 2>/dev/null || echo local)
GHCR_IMAGE ?= $(GHCR_REPO):$(GHCR_TAG)

# buildx settings
BUILDX ?= docker buildx build
BUILD_PLATFORMS ?= linux/amd64
# LOAD_LOCAL=true  -> use --load (local dev)
# LOAD_LOCAL=false -> use --push (CI)
LOAD_LOCAL ?= true

# docker-compose / env
COMPOSE_FILE ?= ./dev/docker-compose.yml
ENV_FILE ?= ./dev/env.dev

# Tests
PYTEST ?= pytest
TEST_DIR ?= tests

# Utilities
JQ ?= jq

# -----------------------
# Phony targets
# -----------------------
.PHONY: help build push-ghcr compose-build up down restart logs ps db-up db-down \
        bootstrap run test itest lint pull-ghcr clean images rm-image

# -----------------------
# Help
# -----------------------
help:
	@printf "\nMakefile targets:\n\n"
	@printf "  build            Build the application image (buildx). Use LOAD_LOCAL=true to --load.\n"
	@printf "  push-ghcr        Build & push app image to GHCR and save digest to image_digest.txt\n"
	@printf "  compose-build    Build services via docker compose (if compose build contexts exist)\n"
	@printf "  up               docker compose up (uses --env-file $(ENV_FILE))\n"
	@printf "  down             docker compose down\n"
	@printf "  restart          down then up\n"
	@printf "  logs             docker compose logs -f\n"
	@printf "  ps               docker compose ps\n"
	@printf "  db-up            start only db service (compose)\n"
	@printf "  db-down          stop/remove db service\n"
	@printf "  bootstrap        run db-bootstrap one-shot service (compose)\n"
	@printf "  run              run app locally via uvicorn (requires local python env)\n"
	@printf "  test             run unit tests (pytest in $(TEST_DIR))\n"
	@printf "  itest            integration tests placeholder (stub)\n"
	@printf "  lint             run linters if installed (black/ruff/isort/mypy)\n"
	@printf "  pull-ghcr        pull image from GHCR for debug\n"
	@printf "  clean            remove compose containers and local image $(FULL_IMAGE)\n"
	@printf "  images           list local images for $(IMAGE)\n"
	@printf "  rm-image         remove specific image by TAG (usage: make rm-image TAG=...)\n\n"

# -----------------------
# Build targets
# -----------------------

# Build app image using buildx. Context is repo root (Dockerfile in repo root).
# Local: make LOAD_LOCAL=true build  -> --load into local docker
# CI:    make LOAD_LOCAL=false build -> --push to registry (if configured)
build:
ifeq ($(LOAD_LOCAL),true)
	@echo "Building (local load) $(FULL_IMAGE) from . (Dockerfile in repo root)..."
	$(BUILDX) --platform=$(BUILD_PLATFORMS) -t $(FULL_IMAGE) --load .
else
	@echo "Building and pushing $(FULL_IMAGE) from . (Dockerfile in repo root)..."
	$(BUILDX) --platform=$(BUILD_PLATFORMS) -t $(FULL_IMAGE) --push .
endif

# Build all images defined in compose (if compose has build contexts)
compose-build:
	@if [ -f "$(COMPOSE_FILE)" ]; then \
	  echo "Building compose services from $(COMPOSE_FILE)..."; \
	  docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) build; \
	else \
	  echo "Compose file $(COMPOSE_FILE) not found"; exit 1; \
	fi

# Build & push to GHCR, then save digest to image_digest.txt
# Requires: docker login to GHCR or GHCR_PAT available to docker login
push-ghcr:
	@echo "Building & pushing to GHCR: $(GHCR_IMAGE)"
	$(BUILDX) --platform=$(BUILD_PLATFORMS) -t $(GHCR_IMAGE) --push .
	@echo "Inspecting image digest for $(GHCR_IMAGE)..."
	@{ \
		D=$$(docker buildx imagetools inspect $(GHCR_IMAGE) --raw 2>/dev/null | $(JQ) -r '.manifests[0].digest' 2>/dev/null || true); \
		if [ -z "$$D" ]; then \
		  D=$$(docker manifest inspect $(GHCR_IMAGE) 2>/dev/null | $(JQ) -r '.[0].digest' 2>/dev/null || true); \
		fi; \
		if [ -z "$$D" ]; then \
		   echo "Warning: could not obtain digest via imagetools or manifest; trying docker inspect..."; \
		   D=$$(docker inspect --format='{{index .RepoDigests 0}}' $(GHCR_IMAGE) 2>/dev/null || true); \
		fi; \
		if [ -z "$$D" ]; then echo "ERROR: failed to obtain digest for $(GHCR_IMAGE)"; exit 1; fi; \
		echo "APP_DIGEST=$$D" | tee image_digest.txt; \
	}

# -----------------------
# Compose / runtime targets
# -----------------------

up:
	@if [ -f "$(COMPOSE_FILE)" ]; then \
	  echo "docker compose up using env $(ENV_FILE) ..."; \
	  docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) up -d; \
	else \
	  echo "Compose file $(COMPOSE_FILE) not found"; exit 1; \
	fi

down:
	@if [ -f "$(COMPOSE_FILE)" ]; then \
	  echo "docker compose down..."; \
	  docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) down; \
	else \
	  echo "Compose file $(COMPOSE_FILE) not found"; exit 1; \
	fi

restart: down up

logs:
	@if [ -f "$(COMPOSE_FILE)" ]; then \
	  docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) logs -f; \
	else \
	  echo "Compose file $(COMPOSE_FILE) not found"; exit 1; \
	fi

ps:
	@if [ -f "$(COMPOSE_FILE)" ]; then \
	  docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) ps; \
	else \
	  echo "Compose file $(COMPOSE_FILE) not found"; exit 1; \
	fi

# Start only DB service (compose 'db')
db-up:
	@if [ -f "$(COMPOSE_FILE)" ]; then \
	  docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) up -d db; \
	else \
	  echo "Compose file $(COMPOSE_FILE) not found"; exit 1; \
	fi

db-down:
	@if [ -f "$(COMPOSE_FILE)" ]; then \
	  docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) stop db || true; \
	  docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) rm -f db || true; \
	else \
	  echo "Compose file $(COMPOSE_FILE) not found"; exit 1; \
	fi

# Run DB bootstrap one-shot (compose 'db-bootstrap')
bootstrap:
	@if [ -f "$(COMPOSE_FILE)" ]; then \
	  docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) up --abort-on-container-exit db-bootstrap; \
	  RC=$$?; echo "db-bootstrap exit code: $$RC"; exit $$RC; \
	else \
	  echo "Compose file $(COMPOSE_FILE) not found"; exit 1; \
	fi

# Local dev run (requires python env)
run:
	@echo "Run uvicorn (dev). Activate venv and ensure dependencies are installed."
	uvicorn app.interface.http.main:app --reload  --env-file $(ENV_FILE) --host 0.0.0.0 --port 8000

# -----------------------
# Tests / lint
# -----------------------

test-unit:
	@echo "Running unit tests via pytest in $(TEST_DIR)..."
	$(PYTEST) $(TEST_DIR) --envfile=$(ENV_FILE) -q

# CI integration tests placeholder (stub)
test-int-ci:
	@echo "Fast CI integration tests placeholder - implement actual integration suite."

# Staging integration tests placeholder (stub)
test-int-staging:
	@echo "Staging integration tests placeholder - implement actual integration suite."

# Smoke tests placeholder (stub)
test-smoke:
	@echo "Smoke tests placeholder - implement actual smoke suite."

# e2e tests placeholder (stub)
test-e2e:
	@echo "e2e tests placeholder - implement actual e2e suite."

lint:
	@echo "Running linters (if installed)..."

	@echo "Running black"
	@if command -v black >/dev/null 2>&1; then \
		black --check $(APP_DIR) || true; \
	elif command -v poetry >/dev/null 2>&1; then \
		poetry run black --check $(APP_DIR) || true; \
	else \
		echo "black not installed, skipping"; \
	fi

	@echo "Running ruff"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check $(APP_DIR) || true; \
	elif command -v poetry >/dev/null 2>&1; then \
		poetry run ruff check $(APP_DIR) || true; \
	else \
		echo "ruff not installed, skipping"; \
	fi

	@echo "Running isort"
	@if command -v isort >/dev/null 2>&1; then \
		isort --check $(APP_DIR) || true; \
	elif command -v poetry >/dev/null 2>&1; then \
		poetry run isort --check $(APP_DIR) || true; \
	else \
		echo "isort not installed, skipping"; \
	fi

	@echo "Running mypy"
	@if command -v mypy >/dev/null 2>&1; then \
		mypy $(APP_DIR) || true; \
	elif command -v poetry >/dev/null 2>&1; then \
		poetry run mypy $(APP_DIR) || true; \
	else \
		echo "mypy not installed, skipping"; \
	fi

# -----------------------
# Registry helpers
# -----------------------

pull-ghcr:
	@echo "Pulling $(GHCR_IMAGE)..."
	docker pull $(GHCR_IMAGE) || echo "Pull failed (image may not exist)"

# -----------------------
# Cleanup
# -----------------------

clean:
	@echo "Cleaning compose containers and local image $(FULL_IMAGE) ..."
	-docker compose --env-file $(ENV_FILE) -f $(COMPOSE_FILE) down --remove-orphans --volumes 2>/dev/null || true
	-docker rm -f app db db-bootstrap 2>/dev/null || true
	-docker rmi $(FULL_IMAGE) 2>/dev/null || true
	-rm -f image_digest.txt 2>/dev/null || true

images:
	@docker images | grep $(IMAGE) || true

rm-image:
	@if [ -z "$(TAG)" ]; then echo "Usage: make rm-image TAG=..."; exit 1; fi
	-docker rmi $(IMAGE):$(TAG) || true

# -----------------------
# End of Makefile
# -----------------------
