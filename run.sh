#!/usr/bin/env bash
# run.sh — Start Agent Zero Corporate Edition
#
# Usage:
#   ./run.sh                                           # uses agent-zero-hardened:latest
#   AGENT_ZERO_IMAGE=myuser/agent-zero-hardened ./run.sh  # uses Docker Hub image

set -euo pipefail

ENV_FILE=".env"
AGENT_ZERO_IMAGE="${AGENT_ZERO_IMAGE:-agent-zero-hardened:latest}"

ENV_ARGS=""
if [ -f "$ENV_FILE" ]; then
  ENV_ARGS="--env-file ../../.env"
else
  echo "WARNING: .env not found — using defaults (admin/changeme). Configure credentials in the UI."
fi

export AGENT_ZERO_IMAGE
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-agent-zero}"

cd docker/run
docker compose \
  $ENV_ARGS \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up -d

echo ""
echo "Agent Zero running at http://127.0.0.1:50080"
echo "  Image : $AGENT_ZERO_IMAGE"
echo "  Logs  : docker logs -f agent-zero"
echo "  Stop  : ./stop.sh"
