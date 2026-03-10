#!/usr/bin/env bash
# stop.sh — Stop Agent Zero Corporate Edition
#
# Usage:
#   ./stop.sh           # stop production instance
#   ./stop.sh --test    # stop test instance

set -euo pipefail

MODE="prod"
for arg in "$@"; do
  case $arg in
    --test) MODE="test" ;;
  esac
done

if [ "$MODE" = "test" ]; then
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-agentzero-test}"
else
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-agentzero}"
fi

cd docker/run
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
echo "Agent Zero [$MODE] stopped."
