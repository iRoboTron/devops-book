# Приложение C: Типичные проблемы

---

## C.1 Диск переполнен

### Симптом

```bash
df -h
/dev/sda1  50G  48G  2G  96% /
```

### Решение

```bash
# 1. Docker мусор
docker system prune -a -f

# 2. Старые логи
find /var/log -name "*.gz" -mtime +30 -delete

# 3. Старые бэкапы
ls -la /var/backups/myapp/
# Удалить старые вручную если ротация не сработала

# 4. Большие файлы
find / -size +100M -type f 2>/dev/null | head -10
```

### Профилактика

- Cron для docker-prune
- Ротация логов Docker (daemon.json)
- Ротация бэкапов в backup.sh

---

## C.2 Бэкап нулевого размера

### Симптом

```bash
ls -la /var/backups/myapp/2026-04-11/db.sql.gz
-rw-r--r-- 1 deploy deploy 0 Apr 11 03:00 db.sql.gz
```

### Причины

| Причина | Решение |
|---------|---------|
| `pg_dump` упал тихо | `set -euo pipefail` в скрипте |
| Docker compose не запущен | Проверить `docker compose ps` |
| Неправильный пользователь | Проверить `POSTGRES_USER` в `.env` |
| Нет места на диске | `df -h` |

### Диагностика

```bash
# Запустить pg_dump вручную
docker compose exec -T db pg_dump -U myapp myapp_prod | wc -c
# Должно быть > 0

# Проверить логи
grep ERROR /var/log/myapp-backup.log
```

---

## C.3 Восстановление: "database already exists"

### Симптом

```
ERROR: database "myapp_prod" already exists
```

### Решение

```bash
# Удалить и пересоздать
docker compose exec db psql -U postgres -c "DROP DATABASE myapp_prod;"
docker compose exec db psql -U postgres -c "CREATE DATABASE myapp_prod OWNER myapp;"

# Восстановить
gunzip -c db.sql.gz | docker compose exec -T db psql -U myapp myapp_prod
```

---

## C.4 PostgreSQL не стартует

### Симптом

```bash
docker compose ps
myapp-db-1  Exit 1
```

### Диагностика

```bash
# Логи
docker compose logs db

# Частые причины:
# 1. Неправильный postgresql.conf
# 2. Нет места для WAL
# 3. Неправильные права на pgdata

# Проверить конфиг
docker compose run --rm db postgres -c config_file=/etc/postgresql/postgresql.conf
```

### Решение

```bash
# Временный запуск без кастомного конфига
docker compose up -d db
# Потом постепенно добавляй параметры
```

---

## C.5 Бэкап в облако не работает

### Симптом

```
rclone copy "$BACKUP_PATH" "remote:bucket/"
Failed to create file system: didn't find section in config file
```

### Решение

```bash
# Проверить конфиг rclone
cat ~/.config/rclone/rclone.conf

# Протестировать подключение
rclone ls remote:bucket/

# Перенастроить
rclone config
```

---

## C.6 Cron не запускает скрипт

### Симптом

```bash
# Скрипт работает вручную но не по cron
```

### Причины

| Причина | Решение |
|---------|---------|
| Неполный PATH в cron | Полный путь: `/usr/local/bin/docker compose` |
| Неправильный пользователь | Проверить поле пользователя в cron |
| Нет `.env` в окружении cron | `source /opt/myapp/.env` в скрипте |
| Скрипт не executable | `chmod +x script.sh` |

### Диагностика

```bash
# Проверить cron работает
systemctl status cron

# Проверить логи
grep CRON /var/log/syslog | tail

# Проверить файл cron
cat /etc/cron.d/myapp-backup
```

---

## C.7 Health check постоянно failing

### Симптом

```bash
docker inspect --format='{{.State.Health.Status}}' myapp-db-1
unhealthy
```

### Причины

| Причина | Решение |
|---------|---------|
| PostgreSQL ещё запускается | Увеличь `start_period` |
| Неправильный пользователь в pg_isready | `pg_isready -U myapp` (не postgres) |
| Порт не слушает | `docker compose logs db` |
| Таймаут слишком маленький | Увеличь `timeout` |

### Решение

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U myapp -d myapp_prod"]
  interval: 10s
  timeout: 10s       # увеличить
  retries: 5         # увеличить
  start_period: 60s  # увеличить для медленного старта
```
