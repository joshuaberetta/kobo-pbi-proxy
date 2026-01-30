#!/bin/sh
set -e

# Initialize DB: Ensure tables exist
echo "Initializing database..."
python -c "from src import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"

echo "Starting Gunicorn..."
exec gunicorn -w 4 -b 0.0.0.0:8000 run:app
