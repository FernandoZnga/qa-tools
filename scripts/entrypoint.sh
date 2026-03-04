#!/usr/bin/env sh
set -e

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
echo "[entrypoint] applying migrations"
python manage.py makemigrations --noinput
python manage.py migrate --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.getenv("DJANGO_SUPERUSER_USERNAME")
email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

if username and password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"[entrypoint] superuser created: {username}")
PY
fi
fi

if [ "${RUN_COLLECTSTATIC:-true}" = "true" ]; then
echo "[entrypoint] collecting static files"
python manage.py collectstatic --noinput
fi

exec "$@"
