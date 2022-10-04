#!/bin/bash

set -e

printf "[1] Stopping cpr and mongo...\n"
docker stop cpr mongo

printf "\n[2] Removing cpr and mongo...\n"
docker rm cpr mongo

printf "\n[3] Pruning any dangling Docker images and volumes...\n"
docker image prune -f
docker volume prune -f

printf "\n[4] Pulling Docker image from ghcr.io/lunarmint/cpr:latest...\n"
docker-compose pull

printf "\n[5] Starting the containers...\n"
docker-compose up -d
