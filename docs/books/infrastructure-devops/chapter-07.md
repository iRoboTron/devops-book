# Глава 7: Восстановление из бэкапа

> **Запомни:** Эту главу нельзя просто прочитать. Закрой книгу и восстанови бэкап прямо сейчас. На тестовой машине. Не "потом". СЕЙЧАС.

---

## 7.1 Восстановление PostgreSQL

### Из gzip-дампа

```bash
gunzip -c db.sql.gz | docker compose exec -T db psql -U myapp myapp_prod
```

`gunzip -c` = распаковать в stdout.
`psql` = применить SQL команды.

### Из custom-формата (быстрее)

```bash
docker compose exec -T db pg_restore -U myapp -d myapp_prod < db.dump
```

`pg_restore` понимает custom format (`-Fc`).

### С удалением старых данных

```bash
# Удалить и пересоздать базу
docker compose exec -T db psql -U postgres -c "DROP DATABASE myapp_prod;"
docker compose exec -T db psql -U postgres -c "CREATE DATABASE myapp_prod OWNER myapp;"

# Восстановить
gunzip -c db.sql.gz | docker compose exec -T db psql -U myapp myapp_prod
```

> **Опасно:** `DROP DATABASE` удаляет ВСЁ. Убедись что бэкап валидный перед дропом.

---

## 7.2 Проверка целостности бэкапа

### gzip тест

```bash
gunzip -t db.sql.gz && echo "OK" || echo "CORRUPTED"
```

`-t` = test. Проверяет целостность без распаковки.

### Посмотреть что внутри

```bash
gunzip -c db.sql.gz | head -20
```

```sql
--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';

--
-- Name: users; Type: TABLE; Schema: public; Owner: myapp
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying(100),
    email character varying(200),
    ...
```

Видишь SQL команды? Бэкап валидный.

### Размер

```bash
ls -lh db.sql.gz
-rw-r--r-- 1 deploy deploy 15M Apr 11 03:00 db.sql.gz
```

15 МБ сжатый. Если 0 байт — что-то пошло не так.

---

## 7.3 Восстановление файлов

```bash
tar -xzf uploads.tar.gz -C /opt/myapp/
```

Проверь:

```bash
ls /opt/myapp/uploads/
```

---

## 7.4 Полный сценарий: "сервер умер, поднимаем с нуля"

### Шаг 1: Новый сервер

```bash
# Поднять Ubuntu Server
# Подключиться по SSH
ssh deploy@new-server
```

### Шаг 2: Установить Docker

```bash
# Из Модуля 3
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

### Шаг 3: Склонировать репозиторий

```bash
git clone https://github.com/user/myapp.git /opt/myapp
cd /opt/myapp
```

### Шаг 4: Восстановить `.env`

```bash
# Из бэкапа
cp /var/backups/myapp/2026-04-11/env.backup /opt/myapp/.env
chmod 600 /opt/myapp/.env
```

### Шаг 5: Поднять контейнеры

```bash
docker compose up -d
```

### Шаг 6: Восстановить базу данных

```bash
gunzip -c /var/backups/myapp/2026-04-11/db.sql.gz \
    | docker compose exec -T db psql -U myapp myapp_prod
```

### Шаг 7: Восстановить файлы

```bash
tar -xzf /var/backups/myapp/2026-04-11/uploads.tar.gz -C /opt/myapp/
```

### Шаг 8: Проверить

```bash
curl http://localhost/health
# {"status": "ok"}

curl http://localhost/users
# {"users": 42}  ← данные на месте!
```

---

## 7.5 Скрипт `restore.sh`

Создай `/opt/myapp/scripts/restore.sh`:

```bash
#!/bin/bash
# Восстановление из бэкапа
# Использование: ./restore.sh /var/backups/myapp/2026-04-11

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <backup_directory>"
    echo "Example: $0 /var/backups/myapp/2026-04-11"
    exit 1
fi

BACKUP_PATH="$1"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "ERROR: Directory not found: $BACKUP_PATH"
    exit 1
fi

source /opt/myapp/.env

echo "[$(date)] Restoring from $BACKUP_PATH"

# Проверить целостность
echo "  Checking backup integrity..."
if [ -f "${BACKUP_PATH}/db.sql.gz" ]; then
    gunzip -t "${BACKUP_PATH}/db.sql.gz" || {
        echo "ERROR: Database backup is corrupted!"
        exit 1
    }
    echo "  Database backup: OK"
fi

# Восстановить базу данных
if [ -f "${BACKUP_PATH}/db.sql.gz" ]; then
    echo "  Restoring database..."
    gunzip -c "${BACKUP_PATH}/db.sql.gz" \
        | docker compose -f /opt/myapp/docker-compose.yml exec -T db \
            psql -U "$POSTGRES_USER" "$POSTGRES_DB"
    echo "  Database restored"
fi

# Восстановить файлы
if [ -f "${BACKUP_PATH}/uploads.tar.gz" ]; then
    echo "  Restoring uploads..."
    tar -xzf "${BACKUP_PATH}/uploads.tar.gz" -C /opt/myapp/
    echo "  Uploads restored"
fi

# Восстановить конфиги
if [ -f "${BACKUP_PATH}/env.backup" ]; then
    cp "${BACKUP_PATH}/env.backup" /opt/myapp/.env
    chmod 600 /opt/myapp/.env
    echo "  Configs restored"
fi

echo "[$(date)] Restore completed"
echo ""
echo "IMPORTANT: Verify that the application works:"
echo "  curl http://localhost/health"
echo "  docker compose ps"
```

---

## 📝 Упражнения

### Упражнение 7.1: Проверить бэкап
**Задача:**
1. Проверь целостность: `gunzip -t /var/backups/myapp/latest/db.sql.gz`
2. Посмотри содержимое: `gunzip -c ... | head -20`
3. Размер правильный? `ls -lh ...`

### Упражнение 7.2: Восстановить на тестовом контейнере
**Задача (ОБЯЗАТЕЛЬНОЕ):**
1. Создай отдельный docker-compose для тестов:
   ```yaml
   # docker-compose.test.yml
   services:
     db:
       image: postgres:16
       environment:
         POSTGRES_USER: test
         POSTGRES_PASSWORD: test
         POSTGRES_DB: test_db
       ports:
         - "5433:5432"
   ```
2. Запусти: `docker compose -f docker-compose.test.yml up -d`
3. Восстанови бэкап:
   ```bash
   gunzip -c /var/backups/myapp/latest/db.sql.gz \
       | docker compose -f docker-compose.test.yml exec -T db \
           psql -U test test_db
   ```
4. Проверь данные:
   ```bash
   docker compose -f docker-compose.test.yml exec db psql -U test -d test_db -c "\dt"
   docker compose -f docker-compose.test.yml exec db psql -U test -d test_db -c "SELECT count(*) FROM users;"
   ```
5. Данные на месте? ✅
6. Удали тестовый контейнер: `docker compose -f docker-compose.test.yml down -v`

### Упражнение 7.3: restore.sh
**Задача:**
1. Создай `restore.sh` (как в 7.5)
2. Запусти: `./restore.sh /var/backups/myapp/latest/`
3. Проверь что всё восстановилось

### Упражнение 7.4: DevOps Think
**Задача:** «Восстановление прошло успешно но приложение выдаёт 500. Почему?»

Подсказки:
1. Миграции применены? (`alembic current`)
2. Версия PostgreSQL совпадает? (14 vs 16)
3. Пользователь БД существует? (`\du`)
4. Права на таблицы? (`GRANT ALL ON ALL TABLES...`)
5. `.env` восстановлен с правильными паролями?

---

## 📋 Чеклист главы 7

- [ ] Я могу восстановить БД из gzip-дампа
- [ ] Я могу восстановить БД из custom-формата
- [ ] Я проверяю целостность бэкапа перед восстановлением
- [ ] Я могу восстановить файлы из tar.gz
- [ ] Я знаю полный сценарий "сервер умер → поднимаем с нуля"
- [ ] Скрипт restore.sh создан
- [ ] Я ПРАКТИЧЕСКИ восстановил бэкап на тестовой машине (ОБЯЗАТЕЛЬНО!)
- [ ] Данные после восстановления доступны через приложение

**Всё отметил?** Переходи к Главе 8 — управление ресурсами и стабильность.
