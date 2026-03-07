---
name: "docker-build-push"
description: "Build the Agent Zero Corporate Edition Docker image from the local repo and optionally push to Docker Hub. Use when asked to build, rebuild, or publish the Docker image."
version: "1.0.0"
author: "David Campman"
tags: ["docker", "build", "deploy", "devops", "corporate"]
trigger_patterns:
  - "build docker"
  - "build image"
  - "push to docker hub"
  - "build and push"
  - "rebuild container"
  - "publish image"
---

# Docker Build & Push Skill

Builds the Agent Zero Corporate Edition image from the local repo and optionally
pushes it to Docker Hub.

## Prerequisites

The Agent Zero container must have the Docker socket mounted to run Docker
commands. Add this to `docker/run/docker-compose.dev.yml`:

```yaml
services:
  agent-zero:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

Without this, Docker commands will fail inside the container.

## Required Secrets / Variables

| Variable | Description |
|----------|-------------|
| `DOCKER_HUB_USER` | Docker Hub username |
| `DOCKER_HUB_TOKEN` | Docker Hub access token or password |

Set these in **Settings → Secrets** before running.

## Process

### Step 1 — Confirm Prerequisites
Before running, verify:
- Docker socket is mounted (`ls /var/run/docker.sock`)
- Secrets `DOCKER_HUB_USER` and `DOCKER_HUB_TOKEN` are set
- Repo is at `/a0/usr/projects/agent_zero_corporate_edition/agentzero`

### Step 2 — Run the build script
Use `code_execution_tool` with `runtime: terminal` to execute:

```bash
bash /a0/usr/skills/active/custom/docker-build-push/scripts/build_and_push.sh   --repo /a0/usr/projects/agent_zero_corporate_edition/agentzero   --user <DOCKER_HUB_USER>   --token <DOCKER_HUB_TOKEN>   [--push]   [--no-cache]   [--test]
```

### Step 3 — Report Results
Report:
- Git commit hash that was built
- Image tag(s) pushed
- Test results (if --test was used)
- Any errors

## Flags

| Flag | Description |
|------|-------------|
| `--push` | Push to Docker Hub after build |
| `--no-cache` | Force full rebuild (no Docker layer cache) |
| `--test` | Run `python -m pytest tests/` before building |

## Example Interactions

**Build only:**
> "Build the docker image"
→ Runs build without push

**Build and push:**
> "Build and push to Docker Hub"
→ Runs build + push using stored secrets

**Full release:**
> "Run tests, build and push to Docker Hub"
→ Runs tests first, fails fast if tests fail, then builds and pushes
