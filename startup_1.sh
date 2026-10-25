#!/bin/bash
# Startup command do Azure App Service (Linux, Python 3.11/3.12)
gunicorn --bind=0.0.0.0:${PORT:-8000} --workers=2 --threads=4 --timeout=120 --access-logfile - app:app
