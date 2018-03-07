#!/usr/bin/env bash
set -o errexit

# xtrace turned on only within the travis folds
start() { echo travis_fold':'start:$1; echo $1; set -v; }
end() { set +v; echo travis_fold':'end:$1; echo; echo; }
die() { set +v; echo "$*" 1>&2 ; exit 1; }
retry() {
    TRIES=1
    until curl --silent --fail http://localhost:$PORT/ > /tmp/response.txt; do
        echo "$TRIES: not up yet"
        if (( $TRIES > 10 )); then
            $OPT_SUDO docker logs $CONTAINER_NAME
            die "HTTP requests to app never succeeded"
        fi
        (( TRIES++ ))
        sleep 1
    done
    echo 'Container responded with:'
    head -n50 /tmp/response.txt
}
source environment.sh

start docker_build
./docker_build.sh
end docker_build


start docker_run
./docker_run.sh
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