# lineup-refinery-docker
Builds a Refinery visualization Docker image for Lineup

## Development
The heavy lifting should be in the `lineup` repo,
but to exercise just the docker build process,
checkout this repo, and then:

```bash
$ ./docker_build.sh
$ ./docker_run.sh
```

## Release

Successful Github tags and PRs will prompt Travis to push the built image to Dockerhub. For a new version number:
```
$ git tag v0.0.x && git push origin --tags
```