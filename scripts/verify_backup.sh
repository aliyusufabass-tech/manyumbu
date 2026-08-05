#!/usr/bin/env sh
set -eu
: "${BACKUP_FILE:?BACKUP_FILE is required}"
pg_restore --list "$BACKUP_FILE" >/dev/null
printf 'Backup archive is readable: %s\n' "$BACKUP_FILE"
