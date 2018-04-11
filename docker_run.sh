#!/usr/bin/env bash
set -o errexit

source environment.sh

if [ -z "$@" ]; then
    $OPT_SUDO docker run \
      --name $CONTAINER_NAME \
      --detach \
      --publish $PORT:80 \
      --env INPUT_JSON="$(cat fixtures/fake-input.json)" \
      $IMAGE
else
    echo "Will mount command line arguments: $@"
    VOLS=''
    I=0
    IN_CONTAINER_ARGS=''
    for ARG in "$@"; do
        ((I++))
        ABSOLUTE_PATH=`realpath $ARG`
        IN_CONTAINER_PATH=/tmp/$I.txt
        VOLS="$VOLS --volume $ABSOLUTE_PATH:$IN_CONTAINER_PATH"
        IN_CONTAINER_ARGS="$IN_CONTAINER_ARGS $IN_CONTAINER_PATH"
    done
    echo "$VOLS"
    echo "$IN_CONTAINER_ARGS"
    $OPT_SUDO docker run \
      --name $CONTAINER_NAME \
      --detach \
      --publish $PORT:80 \
      $VOLS \
      $IMAGE ../on_startup.sh $IN_CONTAINER_ARGS
fi
echo "Visit http://localhost:$PORT"