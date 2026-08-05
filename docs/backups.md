# Backups

Use PostgreSQL custom-format backups:

```sh
DATABASE_URL=postgresql://... BACKUP_DIR=/secure/backups sh scripts/backup_database.sh
BACKUP_FILE=/secure/backups/manyumbu.dump sh scripts/verify_backup.sh
DATABASE_URL=postgresql://... BACKUP_FILE=/secure/backups/manyumbu.dump sh scripts/restore_database.sh
```

Store backups encrypted in provider-managed storage or another access-controlled offsite store. Test restores on staging before restoring production.
