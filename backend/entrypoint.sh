#!/bin/sh
set -eu

# The container starts as root only to fix ownership of mounted volumes,
# then immediately drops privileges to the unprivileged "app" user.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /data /app/media /app/staticfiles
    chown -R app:app /data /app/media /app/staticfiles
    exec gosu app "$0" "$@"
fi

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

attempt=1
until python manage.py migrate --noinput; do
    if [ "$attempt" -ge 10 ]; then
        echo "Database migrations failed after ${attempt} attempts." >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    sleep 3
done

python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application -c /app/gunicorn.conf.py
