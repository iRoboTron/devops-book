# Приложение A: Шпаргалка команд

## psql команды

```sql
-- Справка
\?                           -- список всех команд psql
\h CREATE TABLE              -- справка по SQL-команде

-- Навигация
\l                           -- список БД
\c dbname                    -- подключиться к БД
\dt                          -- список таблиц
\dt schema.*                 -- таблицы в схеме
\d tablename                 -- описание таблицы (колонки, индексы, триггеры)
\di                          -- список индексов
\du                          -- список ролей/пользователей
\dn                          -- список схем
\dv                          -- список представлений

-- Информация
\conninfo                    -- информация о текущем подключении
\list                        -- то же что \l
\encoding                    -- кодировка
\timing                      -- включить замер времени выполнения

-- Выполнение
\i file.sql                  -- выполнить SQL из файла
\o output.txt                -- направить вывод в файл
\! command                   -- выполнить shell-команду
\watch 5                     -- повторять последний запрос каждые 5 сек
\pset border 2               -- формат вывода таблицы
\x auto                      -- включить expanded display (удобно для wide-запросов)

-- Завершение
\q                           -- выход из psql
```

## Администрирование

```bash
# Дамп / восстановление
pg_dump -U postgres -d myapp -F c -f backup.dump     # custom format (рекомендуется)
pg_dump -U postgres -d myapp -F p -f backup.sql      # plain SQL
pg_dump -U postgres -d myapp -s -F p -f schema.sql   # только схема
pg_dump -U postgres -d myapp -a -F c -f data.dump    # только данные
pg_dumpall -U postgres -f full_cluster.sql            # все БД + роли
pg_restore -U postgres -d myapp backup.dump           # восстановить
pg_restore -U postgres -d myapp -t users backup.dump  # одну таблицу
pg_restore -l backup.dump                              # посмотреть содержимое
pg_restore -U postgres -d myapp --clean backup.dump    # заменить существующие таблицы

# Физический бэкап (весь кластер)
pg_basebackup -U replicator -h localhost \
  -D /backup/basebackup -P -Xs -R -z

# Проверка доступности
pg_isready -h localhost -p 5432           # 0 = доступен
pg_isready -h localhost -d myapp -U app   # с проверкой БД
```

## Роли и права

```sql
-- Создание
CREATE USER appuser WITH PASSWORD 'StrongPass';
CREATE ROLE admin_role WITH CREATEDB CREATEROLE;

-- Права на БД
GRANT CONNECT ON DATABASE myapp TO appuser;
GRANT USAGE ON SCHEMA public TO appuser;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO appuser;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO appuser;

-- Права для будущих таблиц (обязательно!)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO appuser;

-- Read-only пользователь
CREATE USER readonly WITH PASSWORD 'ReadOnlyPass';
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO readonly;

-- Смена пароля
ALTER USER appuser WITH PASSWORD 'NewPass';

-- Удаление
DROP USER IF EXISTS appuser;
REASSIGN OWNED BY appuser TO postgres;   -- перед DROP, если есть объекты
DROP OWNED BY appuser;
```

## pg_stat_activity: частые запросы

```sql
-- Активные запросы (не idle)
SELECT pid, usename, application_name,
       now() - query_start AS duration,
       wait_event_type, wait_event,
       left(query, 100) AS query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Сводка по состояниям
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;

-- Блокировки: кто кого блокирует
SELECT blocked.pid AS blocked_id,
       blocking.pid AS blocking_id,
       blocked.query AS blocked_query,
       blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid));

-- Убить запрос
SELECT pg_cancel_backend(pid);       -- SIGTERM (мягко)
SELECT pg_terminate_backend(pid);    -- SIGKILL (жёстко)

-- Убить всё старше 5 минут
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state != 'idle' AND now() - query_start > interval '5 minutes'
  AND pid != pg_backend_pid();
```

## PgBouncer консоль

```bash
# Подключиться к консоли PgBouncer
psql -U pgbouncer_admin -h 127.0.0.1 -p 6432 pgbouncer
```

```sql
-- Состояние пулов
SHOW POOLS;
-- database | user | cl_active | cl_waiting | sv_active | sv_idle | maxwait
-- myapp    | app  | 45        | 0          | 20        | 5       | 0.2

-- Статистика
SHOW STATS;
SHOW DATABASES;

-- Список соединений
SHOW CLIENTS;   -- соединения от приложений к PgBouncer
SHOW SERVERS;   -- соединения от PgBouncer к PostgreSQL

-- Управление
PAUSE myapp;      -- приостановить пул
RESUME myapp;     -- возобновить
KILL myapp;       -- разорвать все соединения пула
RELOAD;           -- перечитать конфиг
```

## WAL и репликация

```sql
-- Состояние репликации (на primary)
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- Lag в байтах
SELECT client_addr,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes
FROM pg_stat_replication;

-- На replica: проверка
SELECT pg_is_in_recovery();                  -- true = реплика
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;

-- Продвинуть реплику в primary (failover)
SELECT pg_promote();                         -- PostgreSQL 12+

-- Размер WAL-файлов
SELECT count(*) || ' files, ' ||
       pg_size_pretty(sum(size)) AS wal_size
FROM pg_ls_waldir();
```

## Быстрая диагностика

```bash
# Первые команды при инциденте
pg_isready -h localhost                      # БД отвечает?
systemctl status postgresql                   # процесс жив?
df -h /var/lib/postgresql                     # диск не полон?
journalctl -u postgresql -n 50                # последние ошибки?
```
