FROM python:3.8-slim-buster

ADD requirements.txt /app/requirements.txt

# Build dependencies, then remove the deps we needed just for building
RUN set -ex \
        && BUILD_DEPS=" \
        build-essential \
        " \
        && apt-get update \
        && apt-get install -y --no-install-recommends $BUILD_DEPS \
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

# TODO: Set appropriate environment variables...
ARG DJANGO_SECRET_KEY
ENV SECRET_KEY=$DJANGO_SECRET_KEY DATA_DIR=/data/

# Put the static files in the right place:
#RUN python manage.py collectstatic --noinput

# Where to find the wsgi file:
ENV UWSGI_WSGI_FILE=gunahasite/wsgi.py

CMD ["uwsgi", "--show-config"]
