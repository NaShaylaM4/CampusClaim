#!/bin/sh
set -eu

: "${SECRET_KEY:?SECRET_KEY must be set in the container environment}"
if [ -z "${DATABASE_URL:-}" ]; then
	: "${DATABASE_PATH:=/app/database/campusclaim.db}"
	export DATABASE_PATH
	mkdir -p "$(dirname "$DATABASE_PATH")"
fi

python -m database.init_database

exec gunicorn --bind "0.0.0.0:${PORT:-8000}" app:app