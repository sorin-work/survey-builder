#!/bin/sh
set -e

flask db upgrade

if [ "${SEED_DEMO:-false}" = "true" ]; then
  flask seed-demo
fi

exec gunicorn --bind 0.0.0.0:8000 --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 30 --graceful-timeout 20 wsgi:app
