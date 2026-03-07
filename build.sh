#!/usr/bin/env bash
# build.sh — Build the Agent Zero Corporate Edition image
# Usage: ./build.sh [--no-cache]

set -euo pipefail

IMAGE="agent-zero-hardened:latest"
NO_CACHE=""

for arg in "$@"; do
  case $arg in
    --no-cache) NO_CACHE="--no-cache" ;;
  esac
done

echo "Building $IMAGE ..."
docker build \
  -f DockerfileLocal \
  -t "$IMAGE" \
  --build-arg CACHE_DATE="$(date +%Y-%m-%d:%H:%M:%S)" \
  $NO_CACHE \
  .

echo ""
echo "Build complete: $IMAGE"
echo "Run with:  ./run.sh"
