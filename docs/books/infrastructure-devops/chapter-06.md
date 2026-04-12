# Глава 6: Автоматические бэкапы

> **Запомни:** Ручной бэкап = бэкап который не делается. Скрипт + cron = бэкап который работает пока ты спишь.

---

## 6.1 Бэкап PostgreSQL: `pg_dump`

### Базовый дамп

```bash
docker compose exec -T db pg_dump -U myapp myapp_prod > db_backup.sql
```

`-T` = без tty (нужно для пайпов и скриптов).

### Сжатый дамп

```bash
docker compose exec -T db pg_dump -U myapp myapp_prod | gzip > db_backup.sql.gz
```

### Custom формат (быстрее восстанавливается)

```bash
docker compose exec -T db pg_dump -U myapp -Fc myapp_prod > db_backup.dump
```

`-Fc` = custom format. Сжатый + быстрее `pg_restore`.

> **Совет:** Custom формат для больших баз (> 1 ГБ).
> gzip — для маленьких.

---

## 6.2 Бэкап файлов

```bash
tar -czf uploads_backup.tar.gz -C /opt/myapp uploads/
```

`-C /opt/myapp` = перейти в директорию перед архивацией.
Результат: `uploads/` внутри архива (не `/opt/myapp/uploads/`).

---

## 6.3 Полный скрипт `backup.sh`

Создай `/opt/myapp/scripts/backup.sh`:

```bash
#!/bin/bash
# Бэкап: база данных + файлы + конфиги
# Запуск: /opt/myapp/scripts/backup.sh

set -euo pipefail

# Загружаем переменные из .env
source /opt/myapp/.env

# Дата для имени файлов
BACKUP_DATE=$(date +%Y-%m-%d)
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_DATE}"

# Создаём директорию бэкапа
mkdir -p "$BACKUP_PATH"

echo "[$(date)] Starting backup to $BACKUP_PATH"

# === База данных ===
echo "  Dumping database..."
docker compose -f /opt/myapp/docker-compose.yml exec -T db \
    pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
    | gzip > "${BACKUP_PATH}/db.sql.gz"

if [ ! -s "${BACKUP_PATH}/db.sql.gz" ]; then
    echo "ERROR: Database backup is empty!"
    exit 1
fi
echo "  Database: $(du -h "${BACKUP_PATH}/db.sql.gz" | cut -f1)"

# === Файлы ===
if [ -d "/opt/myapp/uploads" ]; then
    echo "  Backing up uploads..."
    tar -czf "${BACKUP_PATH}/uploads.tar.gz" -C /opt/myapp uploads/
    echo "  Uploads: $(du -h "${BACKUP_PATH}/uploads.tar.gz" | cut -f1)"
fi

# === Конфиги ===
echo "  Backing up configs..."
cp /opt/myapp/.env "${BACKUP_PATH}/env.backup"
cp /opt/myapp/docker-compose.yml "${BACKUP_PATH}/docker-compose.yml"
cp -r /opt/myapp/nginx "${BACKUP_PATH}/nginx" 2>/dev/null || true

# === Отправка в облако (если настроен rclone) ===
if command -v rclone &> /dev/null && [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    echo "  Uploading to cloud..."
    rclone copy "$BACKUP_PATH" "remote:${BACKUP_S3_BUCKET}/${BACKUP_DATE}/"
    echo "  Cloud upload: OK"
fi

# === Удалить старые бэкапы ===
echo "  Cleaning old backups (>${BACKUP_RETENTION_DAYS:-7} days)..."
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +"${BACKUP_RETENTION_DAYS:-7}" \
    -exec rm -rf {} +

echo "[$(date)] Backup completed successfully"
```

### Разбор каждой строки

```bash
#!/bin/bash
```
Shebang — запускать через bash.

```bash
set -euo pipefail
```
- `-e` — остановить при ошибке
- `-u` — ошибка если переменная не определена
- `-o pipefail` — ошибка в пайпе = ошибка скрипта

> **Запомни:** `set -euo pipefail` в КАЖДОМ скрипте бэкапа.
> Без этого pg_dump может упасть тихо, и бэкап будет пустым.

```bash
source /opt/myapp/.env
```
Загружаем все переменные (POSTGRES_USER, BACKUP_DIR, ...).

```bash
BACKUP_DATE=$(date +%Y-%m-%d)
```
Дата в формате `2026-04-11`.

```bash
if [ ! -s "${BACKUP_PATH}/db.sql.gz" ]; then
    echo "ERROR: Database backup is empty!"
    exit 1
fi
```
Проверка: файл существует И не пустой.
`-s` = файл существует и размер > 0.

```bash
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +
```
Найти директории старше 7 дней и удалить.

---

## 6.4 Настройка cron

Создай `/etc/cron.d/myapp-backup`:

```bash
# Ежедневный бэкап в 3:00
0 3 * * * deploy /opt/myapp/scripts/backup.sh >> /var/log/myapp-backup.log 2>&1
```

| Поле | Значение |
|------|----------|
| `0 3` | В 3:00 |
| `* * *` | Каждый день |
| `deploy` | От имени пользователя deploy |
| `>>` | Дописать лог |
| `2>&1` | Ошибки тоже в лог |

### crontab формат

```
минута  час  день  месяц  день_недели  пользователь  команда
0       3    *     *      *            deploy        /path/to/script
```

### Проверить что cron работает

```bash
# Проверить cron запущен
systemctl status cron

# Посмотреть логи
grep CRON /var/log/syslog | tail

# Принудительно запустить
/opt/myapp/scripts/backup.sh
```

---

## 6.5 Отправка бэкапов в облако: `rclone`

### Установка

```bash
sudo apt install -y rclone
```

### Настройка Backblaze B2

```bash
rclone config
```

Интерактивно:

```
name> remote
Storage> b2 (Backblaze B2)
account> твой_account_id
key> твой_application_key
endpoint>
```

### Настройка AWS S3

```bash
rclone config
```

```
name> remote
Storage> s3 (Amazon S3)
provider> Other
env_auth> false
access_key_id> твой_ключ
secret_access_key> твой_секрет
region> eu-central-1
endpoint> https://s3.eu-central-1.amazonaws.com
```

### Использование в скрипте

```bash
# Копировать бэкап в облако
rclone copy "$BACKUP_PATH" "remote:myapp-backups/${BACKUP_DATE}/"

# Проверить что файлы в облаке
rclone ls remote:myapp-backups/
```

> **Совет:** Backblaze B2 дешевле S3 ($0.005/ГБ/мес vs $0.023/ГБ/мес).
> Для бэкапов — достаточно.

---

## 📝 Упражнения

### Упражнение 6.1: Ручной бэкап
**Задача:**
1. Создай директорию: `mkdir -p /var/backups/myapp/test`
2. Сделай дамп БД:
   ```bash
   docker compose exec -T db pg_dump -U myapp myapp_prod | gzip > /var/backups/myapp/test/db.sql.gz
   ```
3. Проверь что файл не пустой: `ls -la /var/backups/myapp/test/db.sql.gz`
4. Проверь содержимое: `gunzip -c /var/backups/myapp/test/db.sql.gz | head -20`

### Упражнение 6.2: backup.sh
**Задача:**
1. Создай `/opt/myapp/scripts/backup.sh` (как в 6.3)
2. Сделай выполняемым: `chmod +x /opt/myapp/scripts/backup.sh`
3. Убедись что `.env` имеет `BACKUP_DIR` и `BACKUP_RETENTION_DAYS`
4. Запусти вручную: `/opt/myapp/scripts/backup.sh`
5. Проверь: `ls -la /var/backups/myapp/` — бэкап создан?

### Упражнение 6.3: Cron
**Задача:**
1. Создай `/etc/cron.d/myapp-backup`
2. Проверь: `cat /etc/cron.d/myapp-backup`
3. Подожди или измени время на ближайшую минуту
4. Проверь лог: `tail /var/log/myapp-backup.log`

### Упражнение 6.4: rclone (если есть облако)
**Задача:**
1. Установи rclone: `sudo apt install -y rclone`
2. Настрой remote: `rclone config`
3. Протестируй: `rclone ls remote:bucket/`
4. Запусти backup.sh — бэкап ушёл в облако?

### Упражнение 6.5: DevOps Think
**Задача:** «backup.sh запускается по cron но бэкапы пустые. Как узнать почему?»

Подсказки:
1. `set -euo pipefail` стоит? (скрипт должен падать при ошибке)
2. Лог cron: `grep CRON /var/log/syslog`
3. Лог бэкапа: `cat /var/log/myapp-backup.log`
4. Docker compose работает из cron? (cron имеет минимальное окружение)
5. Полный путь к docker compose: `/usr/local/bin/docker compose`

---

## 📋 Чеклист главы 6

- [ ] Я могу сделать дамп БД через `pg_dump`
- [ ] Я понимаю `set -euo pipefail` и зачем каждая опция
- [ ] Скрипт backup.sh создан и работает
- [ ] Проверка что дамп не пустой (`-s`)
- [ ] Cron настроен на ежедневный бэкап
- [ ] Логи бэкапа пишутся и проверяются
- [ ] rclone настроен (или план настроить)
- [ ] Ротация старых бэкапов работает (find + rm)

**Всё отметил?** Переходи к Главе 7 — восстановление из бэкапа.
