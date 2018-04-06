#!/usr/bin/env bash
set -o errexit

source environment.sh

$OPT_SUDO docker run \
  --name $CONTAINER_NAME \
  --detach \
  --publish $PORT:80 \
  --env INPUT_JSON="$(cat fixtures/fake-input.json)" \
  $IMAGE
echo "Visit http://localhost:$PORT"