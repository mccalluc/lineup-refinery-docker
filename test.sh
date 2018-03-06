#!/usr/bin/env bash
set -o errexit

# xtrace turned on only within the travis folds
start() { echo travis_fold':'start:$1; echo $1; set -v; }
end() { set +v; echo travis_fold':'end:$1; echo; echo; }
die() { set +v; echo "$*" 1>&2 ; exit 1; }
retry() {
    TRIES=1
    until curl --silent --fail http://localhost:$PORT/ > /dev/null; do
        echo "$TRIES: not up yet"
        if (( $TRIES > 10 )); then
            $OPT_SUDO docker logs $CONTAINER_NAME
            die "HTTP requests to app never succeeded"
        fi
        (( TRIES++ ))
        sleep 1
    done
}
PORT=8888


start docker_build
source define_repo.sh

# We don't want to run the whole script under sudo on Travis,
# because then it gets the system python instead of the version
# we've specified.
OPT_SUDO=''
if [ ! -z "$TRAVIS" ]; then
  OPT_SUDO='sudo'
fi

echo "REPO: $REPO"
echo "IMAGE: $IMAGE"

$OPT_SUDO docker pull $REPO
$OPT_SUDO docker build --cache-from $REPO --tag $IMAGE context
end docker_build


start docker_run
$OPT_SUDO docker run --name $CONTAINER_NAME --detach --publish $PORT:80 $IMAGE
retry
echo "docker is responsive"
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME
echo "container cleaned up"
end docker_run


# TODO:
#start cypress
#START SERVER
#node_modules/.bin/cypress run
#kill `jobs -p`
#end cypress