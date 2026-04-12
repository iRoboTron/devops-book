# Приложение B: Готовые скрипты

---

## B.1 backup.sh

```bash
#!/bin/bash
# Бэкап: база данных + файлы + конфиги
set -euo pipefail

source /opt/myapp/.env

BACKUP_DATE=$(date +%Y-%m-%d)
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_DATE}"

mkdir -p "$BACKUP_PATH"

echo "[$(date)] Starting backup to $BACKUP_PATH"

# База данных
echo "  Dumping database..."
docker compose -f /opt/myapp/docker-compose.yml exec -T db \
    pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
    | gzip > "${BACKUP_PATH}/db.sql.gz"

if [ ! -s "${BACKUP_PATH}/db.sql.gz" ]; then
    echo "ERROR: Database backup is empty!"
    exit 1
fi
echo "  Database: $(du -h "${BACKUP_PATH}/db.sql.gz" | cut -f1)"

# Файлы
if [ -d "/opt/myapp/uploads" ]; then
    echo "  Backing up uploads..."
    tar -czf "${BACKUP_PATH}/uploads.tar.gz" -C /opt/myapp uploads/
    echo "  Uploads: $(du -h "${BACKUP_PATH}/uploads.tar.gz" | cut -f1)"
fi

# Конфиги
echo "  Backing up configs..."
cp /opt/myapp/.env "${BACKUP_PATH}/env.backup"
cp /opt/myapp/docker-compose.yml "${BACKUP_PATH}/docker-compose.yml"

# Облако
if command -v rclone &> /dev/null && [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    echo "  Uploading to cloud..."
    rclone copy "$BACKUP_PATH" "remote:${BACKUP_S3_BUCKET}/${BACKUP_DATE}/"
fi

# Ротация
echo "  Cleaning old backups (>${BACKUP_RETENTION_DAYS:-7} days)..."
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +"${BACKUP_RETENTION_DAYS:-7}" \
    -exec rm -rf {} +

echo "[$(date)] Backup completed successfully"
```

---

## B.2 restore.sh

```bash
#!/bin/bash
# Восстановление из бэкапа
# Usage: ./restore.sh /var/backups/myapp/2026-04-11
set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

BACKUP_PATH="$1"
source /opt/myapp/.env

echo "[$(date)] Restoring from $BACKUP_PATH"

# Проверка целостности
if [ -f "${BACKUP_PATH}/db.sql.gz" ]; then
    gunzip -t "${BACKUP_PATH}/db.sql.gz" || {
        echo "ERROR: Database backup corrupted!"
        exit 1
    }
fi

# База данных
if [ -f "${BACKUP_PATH}/db.sql.gz" ]; then
    echo "  Restoring database..."
    gunzip -c "${BACKUP_PATH}/db.sql.gz" \
        | docker compose -f /opt/myapp/docker-compose.yml exec -T db \
            psql -U "$POSTGRES_USER" "$POSTGRES_DB"
fi

# Файлы
if [ -f "${BACKUP_PATH}/uploads.tar.gz" ]; then
    echo "  Restoring uploads..."
    tar -xzf "${BACKUP_PATH}/uploads.tar.gz" -C /opt/myapp/
fi

# Конфиги
if [ -f "${BACKUP_PATH}/env.backup" ]; then
    cp "${BACKUP_PATH}/env.backup" /opt/myapp/.env
    chmod 600 /opt/myapp/.env
fi

echo "[$(date)] Restore completed"
echo "Verify: curl http://localhost/health"
```

---

## B.3 health-check.sh

```bash
#!/bin/bash
set -euo pipefail
ERRORS=0

if ! docker compose ps | grep -q "Up"; then
    echo "❌ Container not running"
    ERRORS=$((ERRORS + 1))
fi

DB_STATUS=$(docker inspect --format='{{.State.Health.Status}}' myapp-db-1 2>/dev/null || echo "unknown")
if [ "$DB_STATUS" != "healthy" ]; then
    echo "❌ Database not healthy: $DB_STATUS"
    ERRORS=$((ERRORS + 1))
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    echo "❌ App health check failed: $HTTP_CODE"
    ERRORS=$((ERRORS + 1))
fi

DISK_USE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USE" -gt 85 ]; then
    echo "❌ Disk usage: ${DISK_USE}%"
    ERRORS=$((ERRORS + 1))
fi

ENV_PERMS=$(stat -c "%a" /opt/myapp/.env 2>/dev/null || echo "000")
if [ "$ENV_PERMS" != "600" ]; then
    echo "❌ .env permissions: $ENV_PERMS"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
    echo "✅ All checks passed"
else
    echo "⚠️ $ERRORS check(s) failed"
    exit 1
fi
```

---

## B.4 /etc/cron.d/myapp-backup

```bash
# Ежедневный бэкап в 3:00
0 3 * * * deploy /opt/myapp/scripts/backup.sh >> /var/log/myapp-backup.log 2>&1
```

---

## B.5 /etc/cron.d/docker-prune

```bash
# Еженедельная очистка Docker в 4:00 воскресенье
0 4 * * 0 root docker system prune -f >> /var/log/docker-prune.log 2>&1
```

---

## B.6 /etc/cron.d/myapp-health

```bash
# Проверка здоровья каждые 15 минут
*/15 * * * * deploy /opt/myapp/scripts/health-check.sh >> /var/log/myapp-health.log 2>&1
```
