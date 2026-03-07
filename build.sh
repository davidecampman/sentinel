#!/usr/bin/env bash
# build.sh — Build the Agent Zero Corporate Edition image
#
# Usage:
#   ./build.sh                          # builds agent-zero-hardened:YYYYMMDD
#   ./build.sh --push dockerhub-user    # builds + pushes date-tagged image to Docker Hub
#   ./build.sh --no-cache               # forces full rebuild
#
# To test the new build without touching prod:
#   AGENT_ZERO_IMAGE=agent-zero-hardened:YYYYMMDD ./run.sh
#
# To promote to prod, update AGENT_ZERO_IMAGE in your .env

set -euo pipefail

LOCAL_IMAGE="agent-zero-hardened:$(date +%Y%m%d)"
NO_CACHE=""
PUSH=false
DOCKER_USER=""

for arg in "$@"; do
  case $arg in
    --no-cache)     NO_CACHE="--no-cache" ;;
    --push)         PUSH=true ;;
    *)              if $PUSH && [ -z "$DOCKER_USER" ]; then DOCKER_USER="$arg"; fi ;;
  esac
done

echo "==> Building $LOCAL_IMAGE ..."
docker build \
  -f DockerfileLocal \
  -t "$LOCAL_IMAGE" \
  --build-arg CACHE_DATE="$(date +%Y-%m-%d:%H:%M:%S)" \
  $NO_CACHE \
  .

echo ""
echo "Build complete: $LOCAL_IMAGE"
docker tag "$LOCAL_IMAGE" "agent-zero-hardened:latest"
echo "Tagged:  agent-zero-hardened:latest -> $LOCAL_IMAGE"

if $PUSH; then
  if [ -z "$DOCKER_USER" ]; then
    echo "ERROR: --push requires a Docker Hub username."
    echo "Usage: ./build.sh --push your-dockerhub-username"
    exit 1
  fi

  DATE_TAG="$DOCKER_USER/agent-zero-hardened:$(date +%Y%m%d)"

  echo "==> Tagging as $DATE_TAG"
  docker tag "$LOCAL_IMAGE" "$DATE_TAG"

  echo "==> Pushing to Docker Hub ..."
  docker push "$DATE_TAG"

  echo ""
  echo "Pushed: $DATE_TAG"
  echo ""
  echo "To run from Docker Hub on any machine:"
  echo "  AGENT_ZERO_IMAGE=$DATE_TAG ./run.sh"
else
  echo "Run with:  ./run.sh"
fi
