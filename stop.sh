#!/usr/bin/env bash
# stop.sh — Stop Sentinel
cd docker/run
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
