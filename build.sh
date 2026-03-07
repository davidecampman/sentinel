#!/usr/bin/env bash
# build.sh — Build the Agent Zero Corporate Edition image
#
# Usage:
#   ./build.sh                          # builds agent-zero-hardened:latest
#   ./build.sh --push dockerhub-user    # builds + tags + pushes to Docker Hub
#   ./build.sh --no-cache               # forces full rebuild

set -euo pipefail

LOCAL_IMAGE="agent-zero-hardened:latest"
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

if $PUSH; then
  if [ -z "$DOCKER_USER" ]; then
    echo "ERROR: --push requires a Docker Hub username."
    echo "Usage: ./build.sh --push your-dockerhub-username"
    exit 1
  fi

  HUB_IMAGE="$DOCKER_USER/agent-zero-hardened:latest"
  DATE_TAG="$DOCKER_USER/agent-zero-hardened:$(date +%Y%m%d)"

  echo "==> Tagging as $HUB_IMAGE"
  docker tag "$LOCAL_IMAGE" "$HUB_IMAGE"
  docker tag "$LOCAL_IMAGE" "$DATE_TAG"

  echo "==> Pushing to Docker Hub ..."
  docker push "$HUB_IMAGE"
  docker push "$DATE_TAG"

  echo ""
  echo "Pushed: $HUB_IMAGE"
  echo "Pushed: $DATE_TAG"
  echo ""
  echo "To run from Docker Hub on any machine:"
  echo "  AGENT_ZERO_IMAGE=$HUB_IMAGE ./run.sh"
else
  echo "Run with:  ./run.sh"
fi
