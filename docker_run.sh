#!/usr/bin/env bash
set -o errexit

source environment.sh

CONTAINER_NAME=$IMAGE-container
$OPT_SUDO docker run --name $CONTAINER_NAME --detach --publish $PORT:80 $IMAGE
echo "Visit http://localhost:$PORT"