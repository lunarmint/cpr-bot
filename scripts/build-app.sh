#!/bin/bash

printf "[1] Stopping cpr and mongo...\n"
docker stop cpr mongo

printf "\n[2] Removing cpr and mongo...\n"
docker rm cpr mongo

printf "\n[3] Pruning any dangling Docker images and volumes...\n"
docker image prune -f
docker volume prune -f

printf "\n[4] Pulling the latest Docker image...\n"
docker-compose pull

printf "\n[5] Starting the updated instance...\n"
docker-compose up -d
