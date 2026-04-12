# Приложение A: Шпаргалка команд PostgreSQL

---

## Подключение

```bash
# К контейнеру
docker compose exec db psql -U myapp -d myapp_prod

# К хосту
psql -U myapp -d myapp_prod

# С паролем
PGPASSWORD=secret psql -U myapp -d myapp_prod
```

---

## psql команды (`\`)

| Команда | Что делает |
|---------|-----------|
| `\l` | Список баз |
| `\c dbname` | Подключиться к базе |
| `\dt` | Список таблиц |
| `\d tablename` | Описание таблицы |
| `\du` | Список пользователей |
| `\dp tablename` | Права на таблицу |
| `\conninfo` | Информация о подключении |
| `\q` | Выйти |
| `\i file.sql` | Выполнить файл SQL |

---

## SQL команды

```sql
-- Список баз
SELECT datname FROM pg_database;

-- Размер базы
SELECT pg_size_pretty(pg_database_size('myapp_prod'));

-- Размер таблиц
SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size DESC;

-- Активные подключения
SELECT count(*) FROM pg_stat_activity;

-- Кто подключен
SELECT usename, client_addr, state, query FROM pg_stat_activity;

-- Долгие запросы
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC;

-- Блокировки
SELECT blocked_locks.pid AS blocked_pid, blocking_locks.pid AS blocking_pid
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
WHERE NOT blocked_locks.granted;
```

---

## Бэкап

```bash
# Дамп одной базы (gzip)
pg_dump -U myapp myapp_prod | gzip > db.sql.gz

# Дамп одной базы (custom)
pg_dump -U myapp -Fc myapp_prod > db.dump

# Все базы + пользователи
pg_dumpall -U postgres > all.sql

# Только схема (без данных)
pg_dump -U myapp -s myapp_prod > schema.sql

# Только данные (без схемы)
pg_dump -U myapp -a myapp_prod > data.sql
```

---

## Восстановление

```bash
# Из gzip
gunzip -c db.sql.gz | psql -U myapp myapp_prod

# Из SQL
psql -U myapp myapp_prod < db.sql

# Из custom (быстрее)
pg_restore -U myapp -d myapp_prod db.dump

# Все базы
psql -U postgres < all.sql

# Удалить и пересоздать
pg_dump -U myapp -c myapp_prod | gzip > db.sql.gz
```

`-c` = добавить DROP перед CREATE.

---

## Мониторинг

```bash
# pg_activity (как htop для PostgreSQL)
pg_activity -U myapp -d myapp_prod

# pg_stat_statements (нужно включить в postgresql.conf)
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;
```
