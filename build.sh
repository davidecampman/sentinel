#!/usr/bin/env bash
# build.sh — Build the Sentinel image
#
# Usage:
#   ./build.sh                          # builds sentinel:YYYYMMDD locally (arm64)
#   ./build.sh --latest                 # also updates sentinel:latest locally
#   ./build.sh --push dockerhub-user    # multi-arch build (amd64+arm64) + push to Docker Hub
#   ./build.sh --no-cache               # forces full rebuild
#
# To test the new build without touching prod:
#   AGENT_ZERO_IMAGE=sentinel:YYYYMMDD ./run.sh
#
# To promote to prod, update AGENT_ZERO_IMAGE in your .env

set -euo pipefail

DATE_TAG="$(date +%Y%m%d)"
LOCAL_IMAGE="sentinel:$DATE_TAG"
NO_CACHE=""
PUSH=false
TAG_LATEST=false
DOCKER_USER=""

for arg in "$@"; do
  case $arg in
    --no-cache)     NO_CACHE="--no-cache" ;;
    --push)         PUSH=true ;;
    --latest)       TAG_LATEST=true ;;
    *)              if $PUSH && [ -z "$DOCKER_USER" ]; then DOCKER_USER="$arg"; fi ;;
  esac
done

if $PUSH; then
  if [ -z "$DOCKER_USER" ]; then
    echo "ERROR: --push requires a Docker Hub username."
    echo "Usage: ./build.sh --push your-dockerhub-username"
    exit 1
  fi

  REMOTE_DATE_TAG="$DOCKER_USER/sentinel:$DATE_TAG"
  TAGS="-t $REMOTE_DATE_TAG"
  if $TAG_LATEST; then
    TAGS="$TAGS -t $DOCKER_USER/sentinel:latest"
  fi

  echo "==> Building multi-arch (linux/amd64,linux/arm64) and pushing to Docker Hub ..."
  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -f DockerfileLocal \
    $TAGS \
    --build-arg CACHE_DATE="$(date +%Y-%m-%d:%H:%M:%S)" \
    $NO_CACHE \
    --push \
    .

  echo ""
  echo "Pushed: $REMOTE_DATE_TAG"
  if $TAG_LATEST; then
    echo "Pushed: $DOCKER_USER/sentinel:latest"
  fi
  echo ""
  echo "To run from Docker Hub on any machine:"
  echo "  AGENT_ZERO_IMAGE=$REMOTE_DATE_TAG ./run.sh"
else
  echo "==> Building $LOCAL_IMAGE (arm64) ..."
  docker build \
    -f DockerfileLocal \
    -t "$LOCAL_IMAGE" \
    --build-arg CACHE_DATE="$(date +%Y-%m-%d:%H:%M:%S)" \
    $NO_CACHE \
    .

  echo ""
  echo "Build complete: $LOCAL_IMAGE"

  if $TAG_LATEST; then
    docker tag "$LOCAL_IMAGE" "sentinel:latest"
    echo "Tagged:  sentinel:latest -> $LOCAL_IMAGE"
  fi

  echo "Run with:  ./run.sh"
fi
