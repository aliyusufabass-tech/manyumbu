#!/usr/bin/env sh
set -eu
exec celery -A myproject worker -l "${CELERY_LOG_LEVEL:-info}"
