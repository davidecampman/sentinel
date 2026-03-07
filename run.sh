#!/usr/bin/env bash
# run.sh — Start Agent Zero Corporate Edition
# Usage: ./run.sh

set -euo pipefail

ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found."
  echo "Copy .env.example to .env and fill in your credentials:"
  echo "  cp .env.example .env && $EDITOR .env"
  exit 1
fi

cd docker/run
docker compose \
  --env-file "../../.env" \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up -d

echo ""
echo "Agent Zero is running at http://127.0.0.1:50080"
echo "Logs: docker logs -f agent-zero"
echo "Stop: ./stop.sh"
