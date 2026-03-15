#!/usr/bin/env bash
# build.sh — Build and push Sentinel Docker images to Docker Hub
#
# Builds two images in sequence:
#   1. sentinel-base  — Ubuntu base with system packages, Python, SearXNG
#   2. sentinel       — Application layer on top of base
#
# USAGE
#   ./build.sh --branch <branch> [OPTIONS]
#
# REQUIRED
#   --branch <name>       Branch to build. Controls the image tag (see tag mapping below).
#
# OPTIONS
#   --skip-base           Skip rebuilding the base image. Use when only application
#                         code has changed and the base is already up to date.
#   --no-cache            Disable Docker layer cache. Forces a full rebuild of all layers.
#   --builder <name>      Use a specific buildx builder (e.g. a Docker Build Cloud builder).
#                         Can also be set via the DOCKER_BUILDER environment variable.
#
# BRANCH -> IMAGE TAG MAPPING
#   main    -> decdevelopment/sentinel:latest
#   develop -> decdevelopment/sentinel:develop
#   <other> -> decdevelopment/sentinel:<branch>
#
#   All builds also produce a date-stamped tag: decdevelopment/sentinel:YYYYMMDD_HH_MM
#
# ENVIRONMENT VARIABLES
#   DOCKER_BUILDER        Default builder name, overridden by --builder if both are set.
#
# EXAMPLES
#   # Standard build from the main branch (tags :latest)
#   ./build.sh --branch main
#
#   # Build the develop branch (tags :develop)
#   ./build.sh --branch develop
#
#   # Build a feature branch (tags :my-feature)
#   ./build.sh --branch my-feature
#
#   # Skip base rebuild — faster when only app code changed
#   ./build.sh --branch develop --skip-base
#
#   # Force full rebuild with no layer cache
#   ./build.sh --branch main --no-cache
#
#   # Use Docker Build Cloud via flag
#   ./build.sh --branch main --builder cloud-decdevelopment-default
#
#   # Use Docker Build Cloud via environment variable
#   DOCKER_BUILDER=cloud-decdevelopment-default ./build.sh --branch main
#
#   # Combine: cloud builder, skip base, no cache
#   ./build.sh --branch develop --skip-base --no-cache --builder cloud-decdevelopment-default
#
# AFTER PUSHING
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
