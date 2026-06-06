# Глава 4: Бэкапы — pg_dump и pg_basebackup

## Что вы узнаете

- три инструмента бэкапа и когда что использовать;
- `pg_dump`: логический бэкап одной БД;
- `pg_basebackup`: физический бэкап всего кластера;
- pgBackRest: промышленный backup-менеджер для крупных инсталляций;
- как тестировать восстановление (самое важное в этой главе);
- автоматизация бэкапов через cron.

**Цель главы:** настроить ежедневный бэкап, который реально работает. Не «бэкап есть», а «я восстановился из него и проверил данные».

---

## 1. Стратегия бэкапов: когда что использовать

Не существует одного инструмента на все случаи. Стратегия — комбинация:

```
                  ┌─────────────────────────────────────┐
                  │       Стратегия бэкапов PostgreSQL    │
                  ├─────────────┬───────────┬────────────┤
                  │  pg_dump    │ pg_base-  │ pgBackRest │
                  │             │ backup    │ / WAL-G    │
                  ├─────────────┼───────────┼────────────┤
│ Тип     │ Логический │Физический│ Физический │
│ Уровень  │ Одна БД   │ Кластер  │ Кластер     │
│ PITR     │ Нет       │ + WAL    │ Да (built-  │
│          │           │ архивом  │ in)         │
│ Скорость │ Медленно  │ Быстро   │ Быстро      │
│ восст.   │ на        │          │             │
│          │ больших   │          │             │
│          │ БД        │          │             │
│ Выборка  │ Да (—t,   │ Нет      │ Нет         │
│ таблиц   │ —list)    │          │             │
│ Сжатие   │ Встроено  │ -z флаг │ zstd/gzip   │
│          │ (custom)  │          │             │
├─────────────┼─────────────┼───────────┼────────────┤
│ Частота  │ Ежедневно  │ Ежедневно │ Полный     │
│          │            │           │ раз в       │
│          │            │           │ неделю +    │
│          │            │           │ инкременты  │
│          │            │           │ каждый час  │
└─────────────┴─────────────┴───────────┴────────────┘
```

**Когда что использовать:**

| Сценарий | Инструмент |
|----------|-----------|
| Бэкап одной БД для разработки | `pg_dump -F c` |
| Перенос БД на другой сервер | `pg_dump` + `pg_restore` |
| Полный бэкап кластера без PITR | `pg_basebackup` |
| Production: PITR + инкременты | pgBackRest или WAL-G |
| Бэкап глобальных объектов (роли) | `pg_dumpall -g` |

**Золотое правило:** `pg_dump` для одной БД, `pg_basebackup` или pgBackRest для всего кластера. Комбинировать: ежедневный `pg_dump` + ежечасная WAL-архивация для PITR.

---

## 2. pg_dump — логический бэкап

`pg_dump` выгружает одну БД в SQL-команды или бинарный формат. Работает на работающем сервере без остановки.

### 2.1. Форматы вывода (-F)

| Флаг | Формат | Когда использовать |
|------|--------|-------------------|
| `-F p` | plain SQL | Миграции, маленькие БД, читаемый дамп |
| `-F c` | custom | Стандартный выбор — сжатый, гибкий restore |
| `-F d` | directory | Большие БД — параллельный дамп и restore |
| `-F t` | tar | Редко, почти не используется |

### 2.2. Основные команды

```bash
# Custom-формат (рекомендуется) — сжатый, можно pg_restore
pg_dump -U postgres -d myapp -F c -f /backup/myapp_$(date +%Y%m%d_%H%M).dump

# Plain SQL — читаемый, большой, без pg_restore
pg_dump -U postgres -d myapp -F p -f /backup/myapp_$(date +%Y%m%d).sql

# Directory format — параллельный дамп (4 потока)
pg_dump -U postgres -d myapp -F d -j 4 -f /backup/myapp_$(date +%Y%m%d)

# Только схема (без данных)
pg_dump -U postgres -d myapp -s -F p -f /backup/myapp_schema.sql

# Только данные (без схемы)
pg_dump -U postgres -d myapp -a -F c -f /backup/myapp_data.dump

# Конкретная таблица
pg_dump -U postgres -d myapp -t users -F c -f /backup/users.dump

# Несколько таблиц по маске
pg_dump -U postgres -d myapp -t 'orders_*' -F c -f /backup/orders.dump
```

### 2.3. Сжатие custom-формата

Custom-формат (`-F c`) использует сжатие по умолчанию. Уровень сжатия:

```bash
# Уровень 1 (быстро, слабо) — уровень 9 (медленно, сильно)
pg_dump -U postgres -d myapp -F c -Z 9 -f /backup/myapp.dump

# Zstd-сжатие (PostgreSQL 17+, или через pipe)
pg_dump -U postgres -d myapp -F c | zstd -o /backup/myapp.dump.zst
```

### 2.4. pg_dumpall — весь кластер

`pg_dump` делает дамп **одной** БД. Роли, tablespaces и глобальные настройки он **не захватывает**.

```bash
# Только глобальные объекты (роли, tablespaces)
pg_dumpall -U postgres -g -f /backup/global_objects.sql

# Полный дамп всех БД (только plain SQL)
pg_dumpall -U postgres -f /backup/full_cluster.sql
```

> ☠️ **Осторожно:** `pg_dumpall` всегда создаёт plain SQL. Для больших БД это может быть гигабайтный файл. В production предпочитают `pg_dump` для каждой БД отдельно + `pg_dumpall -g` для ролей.

---

## 3. pg_restore — восстановление из дампа

`pg_restore` работает только с `-F c` и `-F d` форматами. Для `-F p` (plain SQL) используется `psql`:

```bash
psql -U postgres -d myapp -f /backup/myapp.sql
```

### 3.1. Основные команды

```bash
# Создать новую БД и восстановить
createdb -U postgres myapp_restored
pg_restore -U postgres -d myapp_restored /backup/myapp_20260601.dump

# Параллельное восстановление (4 потока — быстрее на больших БД)
pg_restore -U postgres -d myapp_restored -j 4 /backup/myapp_20260601.dump

# Восстановить поверх существующей БД (drop + create)
pg_restore -U postgres -d myapp --clean --if-exists /backup/myapp_20260601.dump
```

### 3.2. Селективное восстановление

Одно из главных преимуществ custom-формата — можно восстановить не всю БД, а только нужные объекты.

```bash
# Список объектов в дампе (без восстановления)
pg_restore -l /backup/myapp_20260601.dump
```

Вывод:

```
;
; Archive created at 2026-06-01 02:00:00
;     dbname: myapp
;     TOC Entries: 45
;
3344; 0 0  TABLE DATA public users postgres
3345; 0 0  TABLE DATA public orders postgres
3346; 0 0  TABLE DATA public products postgres
```

```bash
# Восстановить только таблицу users
pg_restore -U postgres -d myapp_restored -t users /backup/myapp_20260601.dump

# Восстановить несколько таблиц
pg_restore -U postgres -d myapp_restored -t users -t orders /backup/myapp_20260601.dump

# Восстановить все кроме одной таблицы (через список)
pg_restore -l /backup/myapp_20260601.dump > /tmp/toc.txt
# удалить строку с ненужной таблицей в /tmp/toc.txt
pg_restore -U postgres -d myapp_restored -L /tmp/toc.txt /backup/myapp_20260601.dump
```

> ☠️ **Осторожно:** `pg_restore --clean` удаляет существующие таблицы перед восстановлением. Использовать только если точно понимаешь последствия. На production — никогда без проверки на копии.

---

## 4. pg_basebackup — физический бэкап кластера

`pg_basebackup` создаёт бинарную копию всего кластера PostgreSQL — всех баз данных, ролей, конфигов. Работает на живом сервере без остановки.

### 4.1. Базовая команда

```bash
pg_basebackup -U replicator -h localhost \
  -D /backup/basebackup_$(date +%Y%m%d) \
  -P -Xs -z
```

Результат: директория `/backup/basebackup_20260601/` — полная копия `$PGDATA`, готовая к запуску как standalone сервер.

### 4.2. Ключи

| Ключ | Назначение |
|------|-----------|
| `-D /path` | Куда сохранить бэкап |
| `-P` | Показывать прогресс (проценты) |
| `-Xs` | Включить WAL в бэкап (stream mode — без ожидания сегмента) |
| `-Xf` | Включить WAL через fetch (ждёт завершения сегмента — медленнее) |
| `-z` | Сжать бэкап gzip (на лету, по одному файлу) |
| `-Z 9` | Уровень сжатия (1-9) |
| `-R` | Создать standby.signal + postgresql.auto.conf для реплики |
| `--checkpoint=fast` | Быстрый checkpoint перед бэкапом (чуть больше I/O) |
| `--waldir=/path` | Сохранять WAL в отдельную директорию |

### 4.3. Требования

1. Пользователь с правом `REPLICATION`:

```sql
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'ReplPass123';
```

2. Правило в pg_hba.conf:

```text
host replication replicator 127.0.0.1/32 scram-sha-256
```

3. Параметры в postgresql.conf:

```ini
max_wal_senders = 5           # минимум 2 для бэкапа
wal_level = replica           # по умолчанию replica, но проверить
```

### 4.4. Проверка перед бэкапом

```bash
# Проверить что пользователь replicator может подключиться
psql -U replicator -h localhost -c "IDENTIFY_SYSTEM;" replication=1
```

### 4.5. Восстановление из pg_basebackup

```bash
# 1. Остановить PostgreSQL
systemctl stop postgresql

# 2. Сохранить старые данные (на всякий случай)
mv /var/lib/postgresql/16/main /var/lib/postgresql/16/main_old

# 3. Скопировать бэкап на место
cp -r /backup/basebackup_20260601 /var/lib/postgresql/16/main
chown -R postgres: /var/lib/postgresql/16/main

# 4. Запустить PostgreSQL
systemctl start postgresql

# 5. Проверить данные
psql -U postgres -c "SELECT count(*) FROM myapp.users;"
```

---

## 5. pgBackRest — промышленный backup-менеджер

pgBackRest — стандарт для крупных инсталляций PostgreSQL. Поддерживает параллельное сжатие, шифрование, дифференциальные и инкрементальные бэкапы, S3/GCS/Azure, проверку целостности.

### 5.1. Установка

```bash
# Ubuntu/Debian
sudo apt install pgbackrest

# Проверить установку
pgbackrest version
# pgBackRest 2.53
```

### 5.2. Конфигурация

```ini
# /etc/pgbackrest/pgbackrest.conf

[mydb]
pg1-path=/var/lib/postgresql/16/main
pg1-port=5432

[global]
repo1-path=/backup/pgbackrest
repo1-retention-full=7             # хранить 7 полных бэкапов
repo1-cipher-type=none             # aes-256-cbc для шифрования

compress-type=zst                  # zstd сжатие (быстрее gzip)
compress-level=3

# Для S3 (вместо локального репозитория):
# repo1-type=s3
# repo1-s3-bucket=my-pg-backup
# repo1-s3-region=eu-central-1
# repo1-s3-endpoint=s3.eu-central-1.amazonaws.com
```

### 5.3. Инициализация stanza

Stanza — это идентификатор одного кластера PostgreSQL:

```bash
pgbackrest --stanza=mydb stanza-create
```

### 5.4. Типы бэкапов

```bash
# Полный бэкап (копия всего кластера)
pgbackrest --stanza=mydb --type=full backup

# Дифференциальный (только изменения с последнего full)
pgbackrest --stanza=mydb --type=diff backup

# Инкрементальный (только изменения с последнего любого бэкапа)
pgbackrest --stanza=mydb --type=incr backup
```

**Стратегия для production:**

```
Воскресенье 03:00 — full
Пн-Сб 03:00        — diff
Каждый час 15 мин  — incr
```

### 5.5. Восстановление

```bash
# Восстановить последний бэкап
pgbackrest --stanza=mydb restore

# Восстановить на конкретный момент времени (PITR)
pgbackrest --stanza=mydb \
  --type=time \
  --target="2026-06-04 14:31:00+03" \
  restore

# Восстановить в другую директорию
pgbackrest --stanza=mydb \
  --db-path=/var/lib/postgresql/16/restored \
  --type=immediate \
  restore
```

### 5.6. Проверка целостности

```bash
# Проверить что все WAL на месте и конфиг корректен
pgbackrest --stanza=mydb check

# Успешный вывод:
# INFO: check command end: completed successfully
```

Если check выдаёт ошибки — WAL-архивация не работает, восстановление будет невозможно.

### 5.7. Интеграция с PostgreSQL

Добавить в `postgresql.conf`:

```ini
# /etc/postgresql/16/main/postgresql.conf

archive_mode = on
archive_command = 'pgbackrest --stanza=mydb archive-push %p'
```

И перезагрузить:

```bash
sudo systemctl reload postgresql
```

---

## 6. Тест восстановления — обязательно!

**Бэкап без теста восстановления — не бэкап.** Это самое важное правило в этой главе. Единственный способ узнать что бэкап работает — восстановиться из него.

### 6.1. Алгоритм тестирования (раз в месяц)

1. Создать тестовый PostgreSQL (или использовать изолированную среду)
2. Загрузить туда последний бэкап
3. Проверить что данные читаются
4. Проверить что схема корректна
5. Замерить время восстановления
6. Записать результат

### 6.2. Автоматический тест pg_dump через Docker

```bash
#!/bin/bash
# /opt/backup/test_restore.sh

BACKUP_FILE="/backup/myapp_latest.dump"
TEST_DB="test_restore_$(date +%s)"

echo "$(date): Starting restore test..."

docker run --rm \
  -v /backup:/backup \
  postgres:16-alpine \
  sh -c "
    createdb -U postgres $TEST_DB && \
    echo 'Restoring...' && \
    pg_restore -U postgres -d $TEST_DB /backup/$(basename $BACKUP_FILE) && \
    echo 'Checking data...' && \
    psql -U postgres -d $TEST_DB -c 'SELECT count(*) FROM users;' && \
    psql -U postgres -d $TEST_DB -c 'SELECT max(created_at) FROM orders;' && \
    echo 'RESTORE TEST: OK' && \
    dropdb -U postgres $TEST_DB
  "

echo "$(date): Restore test completed"
```

### 6.3. Автоматический тест pg_basebackup

```bash
#!/bin/bash
# /opt/backup/test_base_restore.sh

BACKUP_DIR="/backup/basebackup_$(date +%Y%m%d)"
TEST_DIR="/tmp/pg_test_restore"

# Распаковать бэкап в тестовую директорию
mkdir -p "$TEST_DIR"
tar -xzf "$BACKUP_DIR/base.tar.gz" -C "$TEST_DIR"

# Запустить тестовый PostgreSQL на другом порту
pg_ctl -D "$TEST_DIR" -o "-p 5444" start

# Проверить данные
psql -p 5444 -U postgres -c "SELECT count(*) FROM myapp.users;"
psql -p 5444 -U postgres -c "SELECT schemaname || '.' || tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema');"

# Остановить тестовый сервер
pg_ctl -D "$TEST_DIR" stop
rm -rf "$TEST_DIR"

echo "$(date): Base backup restore test completed"
```

### 6.4. Что проверять при тестировании

```sql
-- 1. Количество строк в ключевых таблицах
SELECT 'users', count(*) FROM users
UNION ALL
SELECT 'orders', count(*) FROM orders
UNION ALL
SELECT 'products', count(*) FROM products;

-- 2. Последние данные (свежесть бэкапа)
SELECT max(created_at) FROM orders;

-- 3. Целостность схемы
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- 4. Нет ли orphaned последовательностей
SELECT sequence_name FROM information_schema.sequences
WHERE sequence_schema = 'public'
AND sequence_name NOT IN (
  SELECT regexp_replace(column_default, '.*''(.*)''.*', '\1')
  FROM information_schema.columns
  WHERE column_default LIKE 'nextval%'
);
```

### 6.5. Запись результатов

Ведите лог тестирования:

```text
# /var/log/pg_restore_tests.log
2026-06-01 03:15: Backup myapp_20260601.dump, size 2.3GB, restore 4m12s, OK
2026-06-01 03:20: Base backup 20260601, size 5.1GB, restore 8m45s, OK
2026-07-01 03:10: Backup myapp_20260701.dump, size 2.4GB, RESTORE FAILED
  → ERROR: relation "orders" does not exist
  → Investigation: backup script had -t users flag, only users table was dumped
  → Fix: removed -t flag from backup script
```

---

## 7. Автоматизация бэкапов

### 7.1. Скрипт ежедневного дампа всех БД

```bash
#!/bin/bash
# /opt/backup/backup_postgres.sh

BACKUP_DIR="/backup/postgres"
PGUSER="postgres"
PGHOST="localhost"
RETENTION_DAYS=14
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/pg_backup.log"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup" >> "$LOG_FILE"

# Дамп глобальных объектов (роли) — раз в неделю
if [ $(date +%u) -eq 7 ]; then
    pg_dumpall -U "$PGUSER" -h "$PGHOST" -g \
        -f "$BACKUP_DIR/globals_$DATE.sql"
    echo "[$(date)] Global objects dumped" >> "$LOG_FILE"
fi

# Дамп каждой БД
DB_LIST=$(psql -U "$PGUSER" -h "$PGHOST" -At \
    -c "SELECT datname FROM pg_database WHERE datistemplate = false;")

for DB in $DB_LIST; do
    # Custom-формат с pg_restore
    pg_dump -U "$PGUSER" -h "$PGHOST" -d "$DB" -F c \
        -f "$BACKUP_DIR/${DB}_${DATE}.dump"

    # Проверить что дамп не пустой
    pg_restore -l "$BACKUP_DIR/${DB}_${DATE}.dump" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "[$(date)] Dumped $DB OK" >> "$LOG_FILE"
    else
        echo "[$(date)] Dump $DB FAILED" >> "$LOG_FILE"
    fi
done

# Создать symlink на последний дамп (для тестов восстановления)
rm -f "$BACKUP_DIR/$(hostname)_latest.dump"
ln -s "${DB}_${DATE}.dump" "$BACKUP_DIR/$(hostname)_latest.dump"

# Удалить старые бэкапы
find "$BACKUP_DIR" -name "*.dump" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.sql" -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Backup complete. Files in $BACKUP_DIR:" >> "$LOG_FILE"
ls -lh "$BACKUP_DIR" >> "$LOG_FILE"
```

### 7.2. Настройка cron

```bash
# Редактировать crontab от root
sudo crontab -e
```

```text
# Ежедневный бэкап в 2:00
0 2 * * * /opt/backup/backup_postgres.sh >> /var/log/pg_backup_cron.log 2>&1

# Тест восстановления — каждое воскресенье в 3:00
0 3 * * 0 /opt/backup/test_restore.sh >> /var/log/pg_restore_test.log 2>&1
```

Проверить что cron добавлен:

```bash
sudo crontab -l
```

### 7.3. Отправка бэкапов на удалённый сервер

```bash
#!/bin/bash
# /opt/backup/sync_backup.sh
# Запускать после backup_postgres.sh

# Rsync на backup-сервер
rsync -avz --delete /backup/postgres/ backup-server:/backup/postgres/

# Или в S3 через aws cli
aws s3 sync /backup/postgres/ s3://my-pg-backup/

# Или через restic
restic backup /backup/postgres/
```

---

## 8. Стратегия retention

Сколько хранить бэкапы — зависит от требований к RPO и RTO.

| Частота | Retention | Место | Комментарий |
|---------|-----------|-------|-------------|
| Ежедневно | 14 дней | ~14 дампов | Текущий месяц |
| Еженедельно | 8 недель | ~8 дампов | Два месяца |
| Ежемесячно | 12 месяцев | ~12 дампов | Год |
| Ежегодно | Бессрочно | ~1 дамп | Архив |

Пример реализации для ежедневных бэкапов:

```bash
# В скрипте backup_postgres.sh — добавить:

# Ежедневные: 14 дней
find "$BACKUP_DIR" -name "*.dump" -mtime +14 -delete

# Еженедельные: копировать с другим именем
if [ $(date +%u) -eq 1 ]; then  # понедельник
    cp "$BACKUP_DIR/${DB}_${DATE}.dump" \
       "$BACKUP_DIR/weekly/${DB}_week_$(date +%Y%U).dump"
fi
```

---

## Типичные ошибки

- `pg_dump` блокирует таблицы на ACCESS SHARE — не влияет на чтение, но блокирует DROP TABLE. В целом безопасно, но на время дампа нельзя удалить таблицу.
- Бэкап на том же диске что и данные — сломался диск, потерял и данные и бэкап. Всегда копировать на удалённый сервер или S3.
- `pg_dump` не бэкапит роли (пользователей). Для полного восстановления нужен `pg_dumpall -g`. Или pgBackRest автоматически.
- Никогда не тестировать восстановление — узнаёте о проблеме только во время реального инцидента. Это самая дорогая ошибка.
- Использовать plain SQL (`-F p`) для больших БД — восстановление через psql медленнее, нет селективного restore, нет --list.
- `pg_basebackup` без ключа `-Xs` — WAL не включается в бэкап, восстановление может быть неконсистентным.
- Retention слишком короткий — обнаружили ошибку через 2 недели, а бэкап уже удалён. Минимум 30 дней для production.
- Забыть проверить `pgbackrest check` после настройки — WAL не архивируется, но никто не заметил.

---

## Чек-лист для самопроверки

- [ ] Умею сделать `pg_dump` в custom-формате и восстановить из него через `pg_restore`
- [ ] Понимаю разницу между `pg_dump` (одна БД) и `pg_basebackup` (весь кластер)
- [ ] Умею восстановить только одну таблицу из дампа через `-t`
- [ ] Настроил автоматический ежедневный бэкап через cron
- [ ] Провёл тест восстановления и знаю сколько времени это занимает
- [ ] Бэкап хранится на другом диске / сервере / в S3
- [ ] Настроен pgBackRest check — прошёл успешно
- [ ] Знаю retention policy для своих бэкапов

---

## Попробуйте сами

1. Сделайте `pg_dump` в custom-формат. Посмотрите что внутри через `pg_restore -l`. Восстановите только одну таблицу (не всю БД) — убедитесь что выборочное восстановление работает.

2. Создайте БД с тестовыми данными. Сделайте дамп. Дропните таблицу. Восстановите таблицу из дампа. Данные вернулись? Проверьте `SELECT count(*) FROM users;` до и после.

3. Настройте cron для ежедневного бэкапа. Проверьте через `sudo crontab -l` что задание добавлено. Запустите скрипт вручную и убедитесь что файлы создаются в нужном месте.

4. Выполните `pg_basebackup` с ключами `-P -Xs -z`. Замерьте сколько времени заняло. Проверьте размер полученного архива — он меньше чем `$PGDATA` без WAL?

5. (Продвинутое) Настройте pgBackRest на локальном репозитории. Сделайте полный бэкап. Проверьте `pgbackrest check`. Удалите таблицу. Восстановите из бэкапа.
