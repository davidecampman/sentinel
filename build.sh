#!/usr/bin/env bash
# build.sh — Build and push Sentinel images to Docker Hub
#
# Usage:
#   ./build.sh --branch main                  # builds base + run, tags :latest + :YYYYMMDD_HH_MM
#   ./build.sh --branch develop               # builds base + run, tags :develop + :YYYYMMDD_HH_MM
#   ./build.sh --branch main --skip-base      # skip base rebuild, only rebuild run image
#   ./build.sh --branch main --no-cache       # forces full rebuild
#   ./build.sh --branch main --builder cloud-<org>-<name>  # use Docker Build Cloud
#
# Branch -> image tag mapping:
#   main    -> decdevelopment/sentinel:latest
#   develop -> decdevelopment/sentinel:develop
#   <other> -> decdevelopment/sentinel:<branch>
#
# Pull and run after pushing:
#   AGENT_ZERO_IMAGE=decdevelopment/sentinel:latest ./run.sh

set -euo pipefail

DOCKER_USER="decdevelopment"
DATE_TAG="$(date +%Y%m%d_%H_%M)"
NO_CACHE=""
BRANCH=""
SKIP_BASE=false
BUILDER="${DOCKER_BUILDER:-}"

for arg in "$@"; do
  case $arg in
    --no-cache)  NO_CACHE="--no-cache" ;;
    --skip-base) SKIP_BASE=true ;;
    --branch)    : ;;
    --builder)   : ;;
    *)
      [ "${PREV_ARG:-}" = "--branch" ]  && BRANCH="$arg"
      [ "${PREV_ARG:-}" = "--builder" ] && BUILDER="$arg"
      ;;
  esac
  PREV_ARG="$arg"
done

BUILDER_FLAG=""
[ -n "$BUILDER" ] && BUILDER_FLAG="--builder $BUILDER"

if [ -z "$BRANCH" ]; then
  echo "ERROR: --branch is required."
  echo "Usage: ./build.sh --branch <branch-name> [--skip-base] [--no-cache]"
  exit 1
fi

# Map branch name to image tag
case "$BRANCH" in
  main)    IMAGE_TAG="latest" ;;
  *)       IMAGE_TAG="$BRANCH" ;;
esac

BASE_IMAGE="$DOCKER_USER/sentinel-base:latest"
RUN_IMAGE="$DOCKER_USER/sentinel:$IMAGE_TAG"
RUN_DATE_IMAGE="$DOCKER_USER/sentinel:$DATE_TAG"
CACHE_DATE="$(date +%Y-%m-%d:%H:%M:%S)"
PLATFORM="linux/amd64,linux/arm64"

if ! $SKIP_BASE; then
  echo "==> [1/2] Building base image -> $BASE_IMAGE ..."
  docker buildx build \
    $BUILDER_FLAG \
    --platform "$PLATFORM" \
    -f docker/base/Dockerfile \
    -t "$BASE_IMAGE" \
    --build-arg CACHE_DATE="$CACHE_DATE" \
    $NO_CACHE \
    --push \
    ./docker/base
  echo "Pushed: $BASE_IMAGE"
  echo ""
else
  echo "==> [1/2] Skipping base build (--skip-base)"
  echo ""
fi

echo "==> [2/2] Building run image (branch: $BRANCH) -> $RUN_IMAGE, $RUN_DATE_IMAGE ..."
docker buildx build \
  $BUILDER_FLAG \
  --platform "$PLATFORM" \
  -f docker/run/Dockerfile \
  -t "$RUN_IMAGE" \
  -t "$RUN_DATE_IMAGE" \
  --build-arg BRANCH="$BRANCH" \
  --build-arg CACHE_DATE="$CACHE_DATE" \
  $NO_CACHE \
  --push \
  ./docker/run

echo ""
echo "Pushed: $RUN_IMAGE"
echo "Pushed: $RUN_DATE_IMAGE"
echo ""
echo "To run:"
echo "  AGENT_ZERO_IMAGE=$RUN_IMAGE ./run.sh"
