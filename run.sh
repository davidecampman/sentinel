#!/usr/bin/env bash
# run.sh — Start Sentinel
#
# Usage:
#   ./run.sh                          # uses sentinel:latest
#   AGENT_ZERO_IMAGE=myuser/sentinel ./run.sh  # uses Docker Hub image

set -euo pipefail

AGENT_ZERO_IMAGE="${AGENT_ZERO_IMAGE:-sentinel:latest}"

export AGENT_ZERO_IMAGE
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-sentinel}"

cd docker/run
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up -d

echo ""
echo "Sentinel running at http://127.0.0.1:50080"
echo "  Image : $AGENT_ZERO_IMAGE"
echo "  Logs  : docker logs -f sentinel"
echo "  Stop  : ./stop.sh"
