#!/usr/bin/env bash
# build.sh — Build the Sentinel image
#
# Usage:
#   ./build.sh                                         # local dev build (DockerfileLocal, arm64)
#   ./build.sh --latest                                # also tags sentinel:latest locally
#   ./build.sh --push dockerhub-user                  # multi-arch local build + push to Docker Hub
#   ./build.sh --push dockerhub-user --branch main    # production: build base + run, multi-arch, push
#   ./build.sh --push dockerhub-user --branch main --skip-base  # skip base, only rebuild run image
#   ./build.sh --no-cache                             # forces full rebuild
#
# To test the new build without touching prod:
#   AGENT_ZERO_IMAGE=sentinel:YYYYMMDD_HH_MM ./run.sh
#
# To promote to prod, update AGENT_ZERO_IMAGE in your .env

set -euo pipefail

DATE_TAG="$(date +%Y%m%d_%H_%M)"
LOCAL_IMAGE="sentinel:$DATE_TAG"
NO_CACHE=""
PUSH=false
TAG_LATEST=false
DOCKER_USER=""
BRANCH=""
SKIP_BASE=false

for arg in "$@"; do
  case $arg in
    --no-cache)   NO_CACHE="--no-cache" ;;
    --push)       PUSH=true ;;
    --latest)     TAG_LATEST=true ;;
    --skip-base)  SKIP_BASE=true ;;
    --branch)     : ;;  # handled by next-arg logic below
    *)
      if [ "${PREV_ARG:-}" = "--branch" ]; then
        BRANCH="$arg"
      elif $PUSH && [ -z "$DOCKER_USER" ]; then
        DOCKER_USER="$arg"
      fi
      ;;
  esac
  PREV_ARG="$arg"
done

# ---------------------------------------------------------------------------
# Production two-stage build: docker/base + docker/run
# ---------------------------------------------------------------------------
if [ -n "$BRANCH" ]; then
  if ! $PUSH || [ -z "$DOCKER_USER" ]; then
    echo "ERROR: --branch requires --push <dockerhub-user>"
    echo "Usage: ./build.sh --push your-dockerhub-username --branch <branch-name>"
    exit 1
  fi

  BASE_IMAGE="$DOCKER_USER/sentinel-base:latest"
  RUN_DATE_TAG="$DOCKER_USER/sentinel:$DATE_TAG"
  RUN_TAGS="-t $RUN_DATE_TAG"
  if $TAG_LATEST; then
    RUN_TAGS="$RUN_TAGS -t $DOCKER_USER/sentinel:latest"
  fi

  CACHE_DATE="$(date +%Y-%m-%d:%H:%M:%S)"

  if ! $SKIP_BASE; then
    echo "==> [1/2] Building base image (linux/amd64,linux/arm64) -> $BASE_IMAGE ..."
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      -f docker/base/Dockerfile \
      -t "$BASE_IMAGE" \
      --build-arg CACHE_DATE="$CACHE_DATE" \
      $NO_CACHE \
      --push \
      ./docker/base
    echo "Pushed: $BASE_IMAGE"
    echo ""
  else
    echo "==> [1/2] Skipping base build (--skip-base), using existing $BASE_IMAGE"
    echo ""
  fi

  echo "==> [2/2] Building run image (linux/amd64,linux/arm64) -> $RUN_DATE_TAG (branch: $BRANCH) ..."
  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -f docker/run/Dockerfile \
    $RUN_TAGS \
    --build-arg BRANCH="$BRANCH" \
    --build-arg CACHE_DATE="$CACHE_DATE" \
    $NO_CACHE \
    --push \
    ./docker/run

  echo ""
  echo "Pushed: $RUN_DATE_TAG (branch: $BRANCH)"
  if $TAG_LATEST; then
    echo "Pushed: $DOCKER_USER/sentinel:latest"
  fi
  echo ""
  echo "To run from Docker Hub on any machine:"
  echo "  AGENT_ZERO_IMAGE=$RUN_DATE_TAG ./run.sh"
  exit 0
fi

# ---------------------------------------------------------------------------
# Local dev build: DockerfileLocal
# ---------------------------------------------------------------------------
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
