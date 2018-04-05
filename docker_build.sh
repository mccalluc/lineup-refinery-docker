#!/usr/bin/env bash
set -o errexit

source environment.sh

echo "REPO: $REPO"
echo "IMAGE: $IMAGE"

$OPT_SUDO docker pull $REPO
$OPT_SUDO docker build \
                 --cache-from $REPO \
                 --tag $IMAGE \
                 context