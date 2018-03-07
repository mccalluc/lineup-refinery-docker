#!/usr/bin/env bash

OWNER=mccalluc # TODO: gehlenborglab
export IMAGE=lineup_refinery
export REPO=$OWNER/$IMAGE
export CONTAINER_NAME=$IMAGE-container

# We don't want to run the whole script under sudo on Travis,
# because then it gets the system python instead of the version
# we've specified.
OPT_SUDO=''
if [ ! -z "$TRAVIS" ]; then
  OPT_SUDO='sudo'
fi
export OPT_SUDO
export PORT=8888