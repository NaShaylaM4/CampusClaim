#!/bin/sh
set -eu

: "${SECRET_KEY:?SECRET_KEY must be set in the container environment}"
: "${DATABASE_PATH:=/app/database/campusclaim.db}"
export DATABASE_PATH

mkdir -p "$(dirname "$DATABASE_PATH")"
python database/init_db.py
python database/migrate_add_return_instructions.py
python database/migrate_add_lost_item_id.py
python database/migrate_add_messages.py

exec gunicorn --bind "0.0.0.0:${PORT:-8000}" app:app