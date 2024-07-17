#!/usr/bin/env bash

set -ex

python manage.py migrate

python manage.py collectstatic --noinput --clear

# The `|| true` is to avoid the script failing if the superuser is already set
python manage.py createsuperuser --noinput 2> /dev/null  || true

gunicorn orbis_am_tool.wsgi \
    --preload \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-2} \
    --timeout ${GUNICORN_TIMEOUT:-300}