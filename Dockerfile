FROM python:3.8-slim-buster

ARG WSGI_USER=gunaha
# Choose an ID that will be consistent across all machines in the network
# To avoid overlap with user IDs, use an ID over
# /etc/login.defs:/UID_MAX/, which defaults to 60,000
ARG UID_GID=60001
RUN groupadd --system --gid ${UID_GID} ${WSGI_USER}   \
        && useradd --no-log-init --system --gid ${WSGI_USER} --uid ${UID_GID} ${WSGI_USER}


# Setup Python deps
ADD requirements.txt /app/requirements.txt

# Build dependencies, then remove the deps we needed just for building
RUN set -ex \
        && BUILD_DEPS=" \
        build-essential \
        " \
        && RUNTIME_DEPS=" \
        ffmpeg \
        " \
        && apt-get update \
        && apt-get install -y --no-install-recommends $BUILD_DEPS \
        && apt-get install -y --no-install-recommends $RUNTIME_DEPS \
        && pip install --no-cache-dir -r /app/requirements.txt \
        && pip install --no-cache-dir uwsgi \
        && apt-get purge -y --auto-remove -o APT::AutoRemove:RecommendsImportant=false $BUILD_DEPS \
        && rm -rf /var/lib/apt/lists/* \
        && mkdir /data/

# Copy our application. Make sure .dockerignore is setup properly!
WORKDIR /app/
ADD . /app/

# uWSGI will listen on this port:
EXPOSE 8000

# Put the static files in the right place:
# TODO: RUN python manage.py collectstatic --noinput

# Where to find the wsgi file:
ENV UWSGI_WSGI_FILE=gunahasite/wsgi.py

# Essential UWSGI config
ENV UWSGI_HTTP=:8000 UWSGI_MASTER=1 UWSGI_HTTP_KEEPALIVE=1 UWSGI_AUTO_CHUNKED=1 UWSGI_WSGI_ENV_BEHAVIOUR=holy

# uwsgi CANNOT run as root!
USER  ${WSGI_USER}:${WSGI_USER}
CMD ["uwsgi", "--show-config"]
