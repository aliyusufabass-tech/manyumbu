#!/usr/bin/env sh
set -eu
exec celery -A myproject beat -l "${CELERY_LOG_LEVEL:-info}"
