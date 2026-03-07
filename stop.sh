#!/usr/bin/env bash
# stop.sh - Stop Sentinel
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
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-sentinel-test}"
else
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-sentinel}"
fi

cd docker/run
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
echo "Sentinel [$MODE] stopped."
