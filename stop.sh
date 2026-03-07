#!/usr/bin/env bash
# stop.sh — Stop Agent Zero Corporate Edition
cd docker/run
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
