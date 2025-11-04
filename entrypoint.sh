#!/usr/bin/env sh
set -e

# Defaults
: "${DEBUG:=1}"
: "${ALLOWED_HOSTS:=127.0.0.1,localhost}"
: "${CSRF_TRUSTED_ORIGINS:=http://127.0.0.1:8000,http://localhost:8000}"

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

# Start server
python manage.py runserver 0.0.0.0:8000
