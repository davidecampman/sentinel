#!/usr/bin/env bash
# run.sh — Start Agent Zero Corporate Edition
#
# Usage:
#   ./run.sh                                           # uses agent-zero-hardened:latest
#   AGENT_ZERO_IMAGE=myuser/agent-zero-hardened ./run.sh  # uses Docker Hub image

set -euo pipefail

ENV_FILE=".env"
AGENT_ZERO_IMAGE="${AGENT_ZERO_IMAGE:-agent-zero-hardened:latest}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found."
  echo "Copy .env.example to .env and set your credentials:"
  echo "  cp .env.example .env"
  exit 1
fi

export AGENT_ZERO_IMAGE

cd docker/run
docker compose \
  --env-file "../../.env" \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up -d

echo ""
echo "Agent Zero running at http://127.0.0.1:50080"
echo "  Image : $AGENT_ZERO_IMAGE"
echo "  Logs  : docker logs -f agent-zero"
echo "  Stop  : ./stop.sh"
