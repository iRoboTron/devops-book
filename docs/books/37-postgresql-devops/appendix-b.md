# Приложение B: Важные системные представления (pg_stat_*)

## pg_stat_activity

| Свойство | Описание |
|----------|----------|
| Что показывает | Все соединения к PostgreSQL: pid, пользователь, состояние, запрос, длительность, ожидания |
| Когда использовать | Первым делом при диагностике: кто подключен, что выполняет, есть ли блокировки |
| Важные колонки | `pid`, `state`, `wait_event_type`, `wait_event`, `query_start`, `xact_start`, `query`, `application_name` |

```sql
SELECT pid, usename, state, wait_event_type, wait_event,
       now() - query_start AS duration, left(query, 80) AS query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

---

## pg_stat_user_tables

| Свойство | Описание |
|----------|----------|
| Что показывает | Статистика по таблицам: количество живых и dead-строк, время последнего vacuum/analyze |
| Когда использовать | Диагностика bloat: найти таблицы с большим числом dead tuples или давно не чищенные |
| Важные колонки | `n_live_tup`, `n_dead_tup`, `last_autovacuum`, `last_autoanalyze`, `seq_scan`, `idx_scan` |

```sql
SELECT relname, n_live_tup, n_dead_tup,
       round(n_dead_tup * 100.0 / (n_live_tup + n_dead_tup + 1), 1) AS dead_pct,
       last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY dead_pct DESC
LIMIT 10;
```

---

## pg_stat_user_indexes

| Свойство | Описание |
|----------|----------|
| Что показывает | Статистика использования индексов: сколько раз каждый индекс использован (idx_scan) |
| Когда использовать | Найти неиспользуемые индексы (`idx_scan = 0`), которые занимают место и замедляют запись |
| Важные колонки | `idx_scan`, `idx_tup_read`, `idx_tup_fetch` |

```sql
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;
```

> **Осторожно:** не удаляйте индексы сразу, даже если `idx_scan = 0`. Проверьте, что индекс не используется в уникальных ограничениях (UNIQUE, PK) или в FOREIGN KEY.

---

## pg_stat_replication

| Свойство | Описание |
|----------|----------|
| Что показывает | Состояние streaming репликации: подключенные реплики, отправленные и применённые WAL-позиции |
| Когда использовать | Мониторинг replication lag: `write_lag`, `flush_lag`, `replay_lag` |
| Важные колонки | `client_addr`, `state`, `sent_lsn`, `write_lsn`, `flush_lsn`, `replay_lsn`, `write_lag`, `replay_lag` |

```sql
SELECT client_addr, state,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes,
       replay_lag
FROM pg_stat_replication;
```

---

## pg_stat_bgwriter

| Свойство | Описание |
|----------|----------|
| Что показывает | Статистика фоновых процессов: checkpoint, буферы |
| Когда использовать | Диагностика I/O проблем: слишком частые checkpoint (checkpoints_req высок) |
| Важные колонки | `checkpoints_timed`, `checkpoints_req`, `buffers_checkpoint`, `buffers_clean`, `buffers_alloc`, `maxwritten_clean` |

```sql
SELECT checkpoints_timed, checkpoints_req,
       round(buffers_checkpoint / (buffers_checkpoint + buffers_clean + buffers_alloc + 1) * 100, 1) AS checkpoint_buf_pct,
       maxwritten_clean
FROM pg_stat_bgwriter;
```

---

## pg_stat_database

| Свойство | Описание |
|----------|----------|
| Что показывает | Статистика по каждой БД: размер, cache hit ratio, дедлоки, конфликты репликации |
| Когда использовать | Общая оценка здоровья БД: cache hit ratio < 95% — проблема |
| Важные колонки | `datname`, `blks_hit`, `blks_read`, `xact_commit`, `xact_rollback`, `deadlocks`, `temp_files`, `temp_bytes` |

```sql
SELECT datname,
       round(blks_hit * 100.0 / (blks_hit + blks_read + 1), 2) AS hit_ratio,
       xact_commit, xact_rollback,
       deadlocks, temp_files,
       pg_size_pretty(temp_bytes) AS temp_size
FROM pg_stat_database
WHERE datname IS NOT NULL
  AND datname NOT IN ('template0', 'template1');
```

---

## pg_locks

| Свойство | Описание |
|----------|----------|
| Что показывает | Все блокировки в системе: какие транзакции какие блокировки держат и ждут |
| Когда использовать | Глубокая диагностика взаимоблокировок. Обычно хватает `pg_stat_activity` + `pg_blocking_pids()` |
| Важные колонки | `locktype`, `relation`, `pid`, `mode`, `granted`, `page`, `tuple` |

```sql
SELECT locktype, relation::regclass AS relation_name,
       pid, mode, granted,
       CASE WHEN NOT granted THEN 'waiting' ELSE 'granted' END AS status
FROM pg_locks
WHERE locktype = 'relation'
  AND relation IS NOT NULL
ORDER BY relation, pid;
```

---

## pg_stat_statements

| Свойство | Описание |
|----------|----------|
| Что показывает | Статистика выполнения запросов: количество вызовов, общее и среднее время, количество строк |
| Когда использовать | Найти самые ресурсоёмкие запросы для оптимизации |
| Важные колонки | `query`, `calls`, `total_exec_time`, `mean_exec_time`, `rows`, `stddev_exec_time`, `shared_blks_hit` |

```sql
-- Топ-10 по общему времени
SELECT substring(query, 1, 80) AS query, calls,
       round(total_exec_time::numeric, 2) AS total_ms,
       round(mean_exec_time::numeric, 2) AS avg_ms,
       rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- Топ-10 по среднему времени (часто выполняемые)
SELECT substring(query, 1, 80) AS query, calls,
       round(mean_exec_time::numeric, 2) AS avg_ms
FROM pg_stat_statements
WHERE calls > 100
ORDER BY mean_exec_time DESC
LIMIT 10;
```

> **Важно:** для использования `pg_stat_statements` необходимо включить расширение: `CREATE EXTENSION IF NOT EXISTS pg_stat_statements` и добавить `shared_preload_libraries = 'pg_stat_statements'` в `postgresql.conf` (требует перезапуска).
