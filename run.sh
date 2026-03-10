#!/usr/bin/env bash
# run.sh — Start Agent Zero Corporate Edition
#
# Usage:
#   ./run.sh              # start production instance  (port 50080)
#   ./run.sh --test       # start test instance        (port 50081, isolated volume)
#   AGENT_ZERO_IMAGE=myuser/agent-zero-hardened ./run.sh

set -euo pipefail

MODE="prod"
for arg in "$@"; do
  case $arg in
    --test) MODE="test" ;;
  esac
done

if [ "$MODE" = "test" ]; then
  AGENT_ZERO_IMAGE="${AGENT_ZERO_IMAGE:-agent-zero-hardened:latest}"
  COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-agentzero-test}"
  CONTAINER_NAME="${CONTAINER_NAME:-agent-zero-test}"
  PORT="${PORT:-50081}"
else
  AGENT_ZERO_IMAGE="${AGENT_ZERO_IMAGE:-agent-zero-hardened:latest}"
  COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-agentzero}"
  CONTAINER_NAME="${CONTAINER_NAME:-agent-zero}"
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
echo "Agent Zero [$MODE] running at http://127.0.0.1:$PORT"
echo "  Image     : $AGENT_ZERO_IMAGE"
echo "  Container : $CONTAINER_NAME"
echo "  Logs      : docker logs -f $CONTAINER_NAME"
if [ "$MODE" = "test" ]; then
  echo "  Stop      : ./stop.sh --test"
else
  echo "  Stop      : ./stop.sh"
fi
