#!/bin/sh
set -eu

: "${SECRET_KEY:?SECRET_KEY must be set in the container environment}"

mkdir -p /app/database
python database/init_db.py
python database/migrate_add_return_instructions.py
python database/migrate_add_lost_item_id.py
python database/migrate_add_messages.py

exec gunicorn --bind 0.0.0.0:8000 app:app