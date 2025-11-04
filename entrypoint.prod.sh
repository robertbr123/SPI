#!/usr/bin/env sh
set -e

# Environment defaults (override in compose)
: "${DEBUG:=0}"
: "${ALLOWED_HOSTS:=*}"
: "${CSRF_TRUSTED_ORIGINS:=}"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Start Gunicorn
exec gunicorn spi.wsgi:application \
  --config gunicorn.conf.py \
  --bind 0.0.0.0:8000
