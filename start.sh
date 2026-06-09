#!/usr/bin/env bash
set -e
: "${WEB_CONCURRENCY:=1}"
: "${WEB_THREADS:=2}"
: "${WEB_TIMEOUT:=3600}"
: "${WEB_GRACEFUL_TIMEOUT:=3600}"

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers "$WEB_CONCURRENCY" \
  --worker-class gthread \
  --threads "$WEB_THREADS" \
  --timeout "$WEB_TIMEOUT" \
  --graceful-timeout "$WEB_GRACEFUL_TIMEOUT" \
  --access-logfile - \
  --error-logfile -
