#!/usr/bin/env bash
# build.sh — Build and push the Sentinel image to Docker Hub
#
# Usage:
#   ./build.sh <dockerhub-user>            # builds multi-arch + pushes date-tagged image
#   ./build.sh <dockerhub-user> --latest   # also pushes as :latest
#   ./build.sh <dockerhub-user> --no-cache # forces full rebuild
#
# To run after pushing:
#   AGENT_ZERO_IMAGE=<dockerhub-user>/sentinel:YYYYMMDD ./run.sh

set -euo pipefail

DOCKER_USER="${1:-}"
NO_CACHE=""
TAG_LATEST=false

if [ -z "$DOCKER_USER" ]; then
  echo "ERROR: Docker Hub username required."
  echo "Usage: ./build.sh <dockerhub-user> [--latest] [--no-cache]"
  exit 1
fi

shift
for arg in "$@"; do
  case $arg in
    --no-cache) NO_CACHE="--no-cache" ;;
    --latest)   TAG_LATEST=true ;;
  esac
done

DATE_TAG="$DOCKER_USER/sentinel:$(date +%Y%m%d)"
TAGS="-t $DATE_TAG"
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
echo "Pushed: $DATE_TAG"
if $TAG_LATEST; then
  echo "Pushed: $DOCKER_USER/sentinel:latest"
fi
echo ""
echo "To run on any machine:"
echo "  AGENT_ZERO_IMAGE=$DATE_TAG ./run.sh"
