#!/usr/bin/env bash
set -euo pipefail
# Run on the Dockge host to pull and restart stacks deterministically.
git -C "${STACKS_DIR:-/opt/stacks}" pull
docker compose -f "${COMPOSE:-docker-compose.yml}" pull
docker compose -f "${COMPOSE:-docker-compose.yml}" up -d
