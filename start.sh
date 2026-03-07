#!/usr/bin/env bash
# start.sh — Start Agent Zero (prod or test instance)

set -euo pipefail

echo "What do you want to start?"
echo "  1) Prod  (port 50080, image from .env)"
echo "  2) Test  (port 50081, latest date-tagged image)"
echo ""
read -rp "Choice [1/2]: " choice

case "$choice" in
  1)
    COMPOSE_PROJECT_NAME="agent-zero"
    CONTAINER_NAME="agent-zero"
    PORT="50080"
    IMAGE="${AGENT_ZERO_IMAGE:-agent-zero-hardened:latest}"
    ;;
  2)
    COMPOSE_PROJECT_NAME="agent-zero-test"
    CONTAINER_NAME="agent-zero-test"
    PORT="50081"
    IMAGE=$(docker images --format "{{.Repository}}:{{.Tag}}" agent-zero-hardened \
      | grep -v latest | sort -r | head -1)
    if [ -z "$IMAGE" ]; then
      echo "ERROR: No date-tagged agent-zero-hardened image found. Run ./build.sh first."
      exit 1
    fi
    ;;
  *)
    echo "Invalid choice."
    exit 1
    ;;
esac

export AGENT_ZERO_IMAGE="$IMAGE"
export CONTAINER_NAME
export PORT
export COMPOSE_PROJECT_NAME

echo ""
echo "==> Starting $COMPOSE_PROJECT_NAME ..."
echo "  Image : $IMAGE"
echo "  Port  : $PORT"
echo ""

cd docker/run
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up -d

echo ""
echo "Running at http://127.0.0.1:$PORT"
echo "  Logs : docker logs -f $CONTAINER_NAME"
echo "  Stop : docker compose -p $COMPOSE_PROJECT_NAME down"
