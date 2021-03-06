# Gūnáhà

On-line Tsuut'ina Dictionary

## Setup

You will need:

 - Python 3.8+
 - [ffmpeg](https://ffmpeg.org/) (`sudo apt install ffmpeg`/`brew install ffmpeg`)
 - [Poetry]

To install all the Python dependencies, do the following:

    poetry install

[Poetry]: https://python-poetry.org/

You must create an `.env` file to store secrets and configuration.
This will generate the `.env` file for the first time:

    make .env

## Deployment on `altlab-itw`

As of 2020-12-01 this app is very JANKILY deployed on `altlab-itw`. Let
me walk you through it (my dignity will not survive this):

 1. On pushes to the default branch, [a GitHub action][action] builds
    a Docker image of the code used in production.
 2. The Docker image is published to the local registry as
    [gunaha:latest][]
 3. Okay, this is the shameful part. Please don't tell the police or my
    family about the next steps.
 4. I login via SSH into `altlab-itw` and start a root shell (`sudo
    -i`).
 5. I pull [gunaha:latest] from the registry:

        docker pull docker.pkg.github.com/ualbertaaltlab/gunaha/gunaha:latest


 6. Okay, this is where it starts getting real bad.
    I stop the running Docker container 🙈

        docker stop gunaha && docker rm gunaha

 7. I then start up a shell inside the new
    container using a script located in `/root`:

        ./open-gunaha-docker-container

 8. Within the container, I run whatever management commands I need to
    run at the given deploy. This may be zero or all of the following
    commands, depending on the code change. These include:

     1. migrate the database schema

            # ./manage.py migrate

     2. import the dictionary content, from scratch!

            # ./manage.py importdictionary --purge

     3. import the recordings

            # ./manage.py importrecordings

     4. update or rebuild the search indices

            # ./manage.py rebuild_indexes

 9. I log out of the shell within the container.
10. Back at the root shell, I start up the container, this time to
      serve the site:

        ./startup-gunaha-docker-container


---

🤮 so... that can be improved. Part of it is that I've been too lazy to
improve it, or I just haven't learned enough about how to improve it.
I think a way I can improve it is to use `docker-compose`, but I haven't
tried it.

[action]: https://github.com/UAlbertaALTLab/gunaha/blob/master/.github/workflows/test-and-publish.yml
[gunaha:latest]: https://github.com/UAlbertaALTLab/gunaha/packages/246109

## Network setup

The Docker container assumes the following setup:

altlab-gw
: nginx: reverse proxy <https://gunaha.altlab.dev> → http://altlab-itw:8000 (terminate SSL)
: nginx: host static files at <https://static.altlab.app/gunaha> from `altlab-gw//export/data/static.altlab.app/gunaha`
: nfs: export `/export/data`
altlab-itw:
: mounted `altlab-gw//export/data` as `/data/`
