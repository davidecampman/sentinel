#!/usr/bin/env bash
# test.sh — Run a test instance alongside prod
#
# Usage:
#   ./test.sh                                    # runs latest date-built image
#   ./test.sh agent-zero-hardened:20260307       # runs a specific image tag
#   ./test.sh --stop                             # stops the test instance

set -euo pipefail

TEST_CONTAINER="agent-zero-test"
TEST_PORT="50081"
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found."
  echo "Copy .env.example to .env and set your credentials:"
  echo "  cp .env.example .env"
  exit 1
fi

if [ "${1:-}" = "--stop" ]; then
  echo "==> Stopping test instance ..."
  cd docker/run
  CONTAINER_NAME="$TEST_CONTAINER" PORT="$TEST_PORT" \
    docker compose --env-file "../../.env" -f docker-compose.yml -f docker-compose.dev.yml \
    down
  echo "Stopped."
  exit 0
fi

# Default to most recently built local date-tagged image
if [ -n "${1:-}" ]; then
  IMAGE="$1"
else
  IMAGE=$(docker images --format "{{.Repository}}:{{.Tag}}" agent-zero-hardened \
    | grep -v latest | sort -r | head -1)
  if [ -z "$IMAGE" ]; then
    echo "ERROR: No date-tagged agent-zero-hardened image found. Run ./build.sh first."
    exit 1
  fi
fi

export AGENT_ZERO_IMAGE="$IMAGE"
export CONTAINER_NAME="$TEST_CONTAINER"
export PORT="$TEST_PORT"

echo "==> Starting test instance ..."
echo "  Image : $IMAGE"
echo "  Port  : $TEST_PORT"
echo ""

cd docker/run
docker compose \
  --env-file "../../.env" \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up -d

echo ""
echo "Test instance running at http://127.0.0.1:$TEST_PORT"
echo "  Stop  : ./test.sh --stop"
