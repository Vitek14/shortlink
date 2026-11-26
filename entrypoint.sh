#!/bin/sh
# entrypoint.sh
set -e

# running migrations by default
if [ "$RUN_MIGRATIONS" != "false" ]; then
    python manage.py migrate
fi

exec "$@"
