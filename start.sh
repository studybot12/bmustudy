#!/bin/sh
PORT=${PORT:-5000}
echo "Starting gunicorn on port $PORT"
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 wsgi:app
