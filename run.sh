#!/usr/bin/env bash
# run.sh - Start Sentinel
#
# Usage:
#   ./run.sh              # start production instance  (port 50080)
#   ./run.sh --test       # start test instance        (port 50081, isolated volume)
#   AGENT_ZERO_IMAGE=myuser/sentinel ./run.sh

set -euo pipefail

MODE="prod"
for arg in "$@"; do
  case $arg in
    --test) MODE="test" ;;
  esac
done

if [ "$MODE" = "test" ]; then
  AGENT_ZERO_IMAGE="${AGENT_ZERO_IMAGE:-sentinel:latest}"
  COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-sentinel-test}"
  CONTAINER_NAME="${CONTAINER_NAME:-sentinel-test}"
  PORT="${PORT:-50081}"
else
  AGENT_ZERO_IMAGE="${AGENT_ZERO_IMAGE:-sentinel:latest}"
  COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-sentinel}"
  CONTAINER_NAME="${CONTAINER_NAME:-sentinel}"
  PORT="${PORT:-50080}"
fi

export AGENT_ZERO_IMAGE
export COMPOSE_PROJECT_NAME
export CONTAINER_NAME
export PORT

cd docker/run
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up -d

echo ""
echo "Sentinel [$MODE] running at http://127.0.0.1:$PORT"
echo "  Image     : $AGENT_ZERO_IMAGE"
echo "  Container : $CONTAINER_NAME"
echo "  Logs      : docker logs -f $CONTAINER_NAME"
if [ "$MODE" = "test" ]; then
  echo "  Stop      : ./stop.sh --test"
else
  echo "  Stop      : ./stop.sh"
fi
