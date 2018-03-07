#!/usr/bin/env bash
set -o errexit
source define_repo.sh
tag_push() { echo "Tagging into $2"; sudo docker tag $1 $2; sudo docker push $2; }
sudo docker login -u mccalluc -p $DOCKER_PASS
tag_push ${IMAGE}_build ${REPO}_build
tag_push $IMAGE $REPO
if [ "$TRAVIS_EVENT_TYPE" == "pull_request" ]; then
  echo "PR!";
  BRANCH=`echo ${TRAVIS_PULL_REQUEST_BRANCH:-$TRAVIS_BRANCH} | perl -pne 'chomp;s{.*/}{};s/\W/-/g'`;
  tag_push ${IMAGE}_build ${REPO}_build:$BRANCH;
  tag_push ${IMAGE}_build ${REPO}_build:latest-pr;
  tag_push $IMAGE $REPO:$BRANCH;
  tag_push $IMAGE $REPO:latest-pr;
fi
if [ ! -z "$TRAVIS_TAG" ]; then
  echo "Git tag!";
  tag_push ${IMAGE}_build ${REPO}_build:$TRAVIS_TAG;
  tag_push ${IMAGE}_build ${REPO}_build:latest;
  tag_push $IMAGE $REPO:$TRAVIS_TAG;
  tag_push $IMAGE $REPO:latest;
fi