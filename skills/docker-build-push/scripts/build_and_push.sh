#!/usr/bin/env bash
# build_and_push.sh — Build Agent Zero Corporate Edition image
# Called by the docker-build-push skill

set -euo pipefail

REPO="/a0/usr/projects/agent_zero_corporate_edition/agentzero"
DOCKER_USER=""
DOCKER_TOKEN=""
PUSH=false
NO_CACHE=""
RUN_TESTS=false
LOCAL_IMAGE="agent-zero-hardened:latest"

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --repo)    REPO="$2";         shift 2 ;;
    --user)    DOCKER_USER="$2";  shift 2 ;;
    --token)   DOCKER_TOKEN="$2"; shift 2 ;;
    --push)    PUSH=true;          shift   ;;
    --no-cache) NO_CACHE="--no-cache"; shift ;;
    --test)    RUN_TESTS=true;     shift   ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "======================================"
echo " Agent Zero Corporate Edition Build"
echo "======================================"
echo "Repo    : $REPO"
echo "Push    : $PUSH"
echo "Tests   : $RUN_TESTS"
echo ""

# Check Docker is available
if ! docker info > /dev/null 2>&1; then
  echo "ERROR: Docker is not accessible."
  echo "The Docker socket must be mounted into the container:"
  echo "  volumes:"
  echo "    - /var/run/docker.sock:/var/run/docker.sock"
  exit 1
fi

# Pull latest code
echo "==> Pulling latest code..."
cd "$REPO"
git pull origin main
COMMIT=$(git rev-parse --short HEAD)
echo "HEAD: $COMMIT"
echo ""

# Run tests
if $RUN_TESTS; then
  echo "==> Running tests..."
  python -m pytest tests/ -q --tb=short
  echo "Tests passed!"
  echo ""
fi

# Build image
echo "==> Building $LOCAL_IMAGE ..."
docker build \
  -f DockerfileLocal \
  -t "$LOCAL_IMAGE" \
  --build-arg CACHE_DATE="$(date +%Y-%m-%d:%H:%M:%S)" \
  $NO_CACHE \
  .
echo "Build complete: $LOCAL_IMAGE"
echo ""

# Push to Docker Hub
if $PUSH; then
  if [ -z "$DOCKER_USER" ] || [ -z "$DOCKER_TOKEN" ]; then
    echo "ERROR: --push requires --user and --token"
    exit 1
  fi

  HUB_IMAGE="$DOCKER_USER/agent-zero-hardened:latest"
  DATE_TAG="$DOCKER_USER/agent-zero-hardened:$(date +%Y%m%d)-$COMMIT"

  echo "==> Logging in to Docker Hub..."
  echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USER" --password-stdin

  echo "==> Tagging and pushing..."
  docker tag "$LOCAL_IMAGE" "$HUB_IMAGE"
  docker tag "$LOCAL_IMAGE" "$DATE_TAG"
  docker push "$HUB_IMAGE"
  docker push "$DATE_TAG"

  echo ""
  echo "======================================"
  echo " Push Complete!"
  echo "======================================"
  echo "  $HUB_IMAGE"
  echo "  $DATE_TAG"
  echo ""
  echo "To deploy on any machine:"
  echo "  AGENT_ZERO_IMAGE=$HUB_IMAGE ./run.sh"
else
  echo "Build complete. Run ./run.sh to start."
fi
