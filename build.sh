#!/usr/bin/env bash
# Render build script - runs once per deploy before the service starts.
set -o errexit

pip install -r requirements/production.txt
python manage.py collectstatic --no-input
python manage.py migrate
