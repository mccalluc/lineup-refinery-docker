#!/usr/bin/env bash
set -o errexit

source environment.sh

echo "REPO: $REPO"
echo "IMAGE: $IMAGE"

# Folks are wondering if it should be easier to cache and reuse images
# from multi-stage builds, but there is no proposed fix right now.
# https://github.com/moby/moby/issues/34715

$OPT_SUDO docker pull ${REPO}_build
$OPT_SUDO docker build \
                 --cache-from ${REPO}_build \
                 --tag ${IMAGE}_build \
                 --target build \
                 context

$OPT_SUDO docker pull $REPO
$OPT_SUDO docker build \
                 --cache-from ${REPO}_build \
                 --cache-from $REPO \
                 --tag $IMAGE \
                 context