# lineup-refinery-docker
This builds a Refinery visualization Docker image for Lineup.

For a preview, you can run the Docker container locally with your own data:
```
docker run \
      --detach \
      --publish 8888:80 \
      --volume /my/local/data.csv:/tmp/1.csv \
      ../on_startup.sh /tmp/1.csv
``

Change `/my/local/data.csv` to fit your needs, but the other paths are internal
to the container and will not be changed. The `docker_run.sh` provides a simpler
interface.


## Development
The heavy lifting is in the `lineup` code,
but to exercise just the docker build process,
checkout this repo, and then:

```bash
$ ./docker_build.sh
$ ./docker_run.sh
```

(`docker_run.sh` also accepts CSVs as command-line arguments.)

## Release
Successful Github tags and PRs will prompt Travis to push the built image to Dockerhub. For a new version number:
```
$ git tag v0.0.x && git push origin --tags
```