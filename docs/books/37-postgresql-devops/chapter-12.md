# Глава 12: Диагностика — алгоритм разбора инцидентов

## Что вы узнаете

- системный подход к диагностике инцидентов PostgreSQL: не паниковать, а идти по алгоритму;
- три типовых сценария: PostgreSQL не отвечает, работает медленно, отстала репликация;
- где искать информацию: pg_stat_activity, pg_stat_bgwriter, pg_stat_replication, pg_log;
- что собрать для передачи DBA или разработчику.

**Цель:** при инциденте вы ставите диагноз за 5-10 минут и знаете, что делать дальше.

---

## Алгоритм первичной диагностики

```mermaid
flowchart TD
    A[Проблема с PostgreSQL] --> B{PostgreSQL отвечает?}
    B -->|Нет| C[pg_isready / systemctl status]
    C --> C1{Причина}
    C1 -->|Disk full| D[df -h /var/lib/postgresql]
    C1 -->|OOM| E[dmesg | grep -i 'oom\\|killed']
    C1 -->|Crash| F[journalctl -u postgresql --since '1h ago']
    B -->|Да| G{Медленно или ошибки?}
    G -->|Медленно| H[pg_stat_activity: active + waiting]
    H --> H1{Есть ожидающие?}
    H1 -->|Lock wait| I[pg_blocking_pids -> убить блокирующий]
    H1 -->|Нет| J[pg_stat_statements: топ медленных запросов]
    G -->|Ошибки| K[Логи приложения + pg_log]
    K --> K1{Тип ошибки}
    K1 -->|connection refused| L[max_connections исчерпан? ss -tnp]
    K1 -->|too many clients| M[PgBouncer не настроен?]
    K1 -->|deadlock| N[pg_log: deadlock detail]
```

Алгоритм один для любого инцидента: проверить доступность, найти симптом, определить причину, устранить. Никогда не перезапускайте PostgreSQL первым делом — вы потеряете информацию о состоянии.

---

## Сценарий 1: PostgreSQL не принимает соединения

Приложение пишет `connection refused` или `could not connect to server`.

### Быстрые проверки (30 секунд)

```bash
pg_isready -h localhost -p 5432       # отвечает?
systemctl status postgresql            # запущен?
df -h /var/lib/postgresql/16/main     # диск не заполнен?
journalctl -u postgresql -n 50        # последние ошибки
```

### Причина: диск заполнен

WAL-файлы могут заполнить диск, если `wal_keep_size` слишком велик или архивация не настроена.

```bash
du -sh /var/lib/postgresql/16/main/pg_wal/   # WAL занимает много?

# Экстренно: принудительный checkpoint (освободить WAL)
sudo -u postgres psql -c "CHECKPOINT;"

# Проверить, освободилось ли место
df -h /var/lib/postgresql/16/main

# Для постоянного решения: настроить архивацию WAL (глава 5)
# или уменьшить wal_keep_size:
# wal_keep_size = 1GB
```

### Причина: max_connections исчерпан

```bash
# Сколько соединений сейчас
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Сколько всего разрешено
sudo -u postgres psql -c "SHOW max_connections;"

# Убить idle-соединения старше 10 минут
sudo -u postgres psql -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND state_change < now() - interval '10 minutes';"
```

Если это повторяется — настройте PgBouncer (глава 8). 500 соединений от приложения убивают PostgreSQL, PgBouncer сводит их к 20.

### Причина: OOM killer

```bash
dmesg | grep -i 'oom\|killed'
# [221428.456123] oom-kill: task=postgres: pid=12345 ...
```

Что делать: проверить `work_mem × max_connections` — не превышает ли RAM? Настроить PgBouncer, уменьшить `work_mem` или добавить памяти серверу.

---

## Сценарий 2: Всё работает, но медленно

PostgreSQL отвечает, но запросы выполняются дольше обычного.

### Диагностика за 2 минуты

```sql
-- 1. Самые долгие активные запросы
SELECT pid, now() - query_start AS duration, left(query, 80) AS query, state
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC
LIMIT 10;

-- 2. Есть ли блокировки?
SELECT count(*) AS blocked_queries
FROM pg_stat_activity
WHERE wait_event_type = 'Lock';

-- 3. Кто кого блокирует?
SELECT blocked.pid AS blocked_pid,
       blocked.query AS blocked_query,
       blocking.pid AS blocking_pid,
       blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE cardinality(pg_blocking_pids(blocked.pid)) > 0;

-- 4. Частота checkpoint (норма: < 1/min)
SELECT checkpoints_timed, checkpoints_req,
       checkpoints_req * 100.0 / (checkpoints_timed + checkpoints_req + 1) AS req_pct
FROM pg_stat_bgwriter;
-- checkpoints_req > 10% от общего числа = нагрузка на WAL

-- 5. Cache hit ratio (норма: > 95%)
SELECT datname,
       round(blks_hit * 100.0 / (blks_hit + blks_read + 1), 2) AS hit_ratio
FROM pg_stat_database
WHERE datname = current_database();
-- < 90%: увеличить shared_buffers
-- < 95%: обратить внимание
```

### Что делать по результатам

| Симптом | Вероятная причина | Действие |
|---------|------------------|----------|
| Много `wait_event_type = 'Lock'` | Конкуренция за строки/таблицы | Найти блокирующий pid, решить с разработчиком |
| `checkpoints_req` > 20% | WAL-нагрузка, частые checkpoint | Увеличить `checkpoint_completion_target`, `max_wal_size` |
| Cache hit ratio < 90% | Мало `shared_buffers` | Увеличить до 25% RAM |
| Один запрос висит минутами | Медленный запрос, нет индекса | `EXPLAIN ANALYZE`, передать разработчику |
| `idle in transaction` > 10 | Открытые транзакции не закрываются | Найти и закрыть, проверить код приложения |

---

## Vacuum troubleshooting

Dead tuples накапливаются при UPDATE/DELETE. Без vacuum — bloat таблиц и индексов, падение производительности. Autovacuum включён по умолчанию, но может не успевать.

```sql
-- Доля dead tuples по таблицам
SELECT relname,
       n_live_tup, n_dead_tup,
       round(n_dead_tup * 100.0 / (n_live_tup + n_dead_tup + 1), 1) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY dead_pct DESC;

-- Таблицы, где autovacuum не запускался давно
SELECT relname, last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
WHERE last_autovacuum IS NULL
   OR last_autovacuum < now() - interval '1 day';
```

### Почему autovacuum может не успевать

```sql
-- Причина 1: long-running транзакция держит xmin
SELECT pid, now() - xact_start AS age, state, left(query, 60) AS query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY age DESC
LIMIT 5;

-- Причина 2: слишком высокая интенсивность обновлений
-- Решение: настроить autovacuum (см. главу 13, раздел "Autovacuum tuning")
```

### Экстренные меры

```sql
-- Ручной VACUUM (не блокирует таблицу)
VACUUM users;

-- VACUUM ANALYZE (очистка + обновление статистики)
VACUUM ANALYZE users;

-- VACUUM FULL (блокирует таблицу! только в окно обслуживания)
-- VACUUM FULL users;
```

> **Осторожно:** `VACUUM FULL` блокирует таблицу на запись на всё время выполнения. Для production — только в запланированное окно обслуживания. Обычный `VACUUM` не блокирует.

Подробнее о настройке autovacuum — в главе 13, раздел "Тюнинг autovacuum".

---

## Сценарий 3: Репликация отстала

### Быстрая диагностика

```sql
-- На primary: lag в секундах
SELECT client_addr, state,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- На primary: lag в байтах
SELECT client_addr,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes
FROM pg_stat_replication;

-- На replica: lag по времени
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

### Причины отставания

| Причина | Как проверить | Решение |
|---------|--------------|---------|
| Сеть между primary и replica | `ping`, `iperf`, `tcptraceroute` | Проверить bandwidth, latency |
| Replica не справляется с apply | `top`, `iostat` на replica | Увеличить CPU/IO replica |
| Long-running query на primary | `pg_stat_activity` возраст > 5 мин | Оптимизировать или убить запрос |
| `max_wal_senders` мал | `SELECT count(*) FROM pg_stat_replication;` | Увеличить `max_wal_senders` |

### Что делать при критическом lag

1. Убедиться, что replica жива: `pg_isready -h replica-host`.
2. Проверить network latency.
3. Если lag растёт — временно снизить нагрузку на primary или отключить неключевые reads с replica.
4. Если replica полностью отстала и WAL уже удалён — пересоздать через `pg_basebackup`.

---

## pgbench: измеряем производительность

`pgbench` — встроенный инструмент нагрузочного тестирования. Позволяет измерить TPS (транзакции/сек) и latency.

```bash
# Инициализация тестовой БД (масштаб 50 = ~750MB)
pgbench -U postgres -i -s 50 testbench

# Простой тест: 10 клиентов, 30 секунд
pgbench -U postgres -c 10 -j 4 -T 30 testbench
# Результат:
# tps = 1523.45 (including connections establishing)
# tps = 1541.02 (excluding connections establishing)

# Тест с PgBouncer: 100 соединений через пул
pgbench -U appuser -h pgbouncer -p 6432 -c 100 -j 8 -T 60 testbench
```

Что измерять: TPS (чем выше — тем лучше), latency average и stddev, количество failed connections. Сравнивать до и после изменения конфигурации.

Методология тестирования описана в главе 13, раздел "pgbench: методология тестирования".

---

## Что собрать для DBA / разработчика

При передаче проблемы разработчику или DBA подготовьте:

1. **Временной диапазон инцидента** — когда началось, когда заметили, когда прошло.
2. **Вывод `pg_stat_activity`** в момент проблемы (не постфактум, а когда тормозило).
3. **Фрагмент pg_log** — последние 100-200 строк до инцидента:
   ```bash
   journalctl -u postgresql --since '2026-06-04 14:00' --until '2026-06-04 14:30' -n 200
   ```
4. **Результат `pg_stat_statements`** за период — топ-10 по total_time.
5. **Метрики из мониторинга**: TPS, connections, cache hit ratio, replication lag (если есть Prometheus/Grafana).
6. **Что изменилось перед инцидентом**: деплой, миграция, изменение конфигурации, рост нагрузки.

Шаблон сообщения:

```
Инцидент: медленные запросы в БД myapp
Время: 14:05 - 14:20 UTC 2026-06-04
Симптом: таймауты при POST /api/orders
pg_stat_activity: 3 запроса висят > 5 минут, wait_event_type = Lock
pg_log: deadlock detected
Что изменилось: за 10 минут до инцидента деплойнули миграцию с ALTER TABLE orders
```

---

## Типичные ошибки

- Перезапускать PostgreSQL как первый шаг диагностики — теряется `pg_stat_activity`, `pg_stat_statements`, информация о блокировках. Перезапуск — последнее средство.
- Убивать все соединения подряд — может прервать критические транзакции. Сначала идентифицировать виновника через `pg_blocking_pids`.
- Не логировать медленные запросы (`log_min_duration_statement`) — нет данных для анализа после инцидента.
- Смотреть только метрики сервера (CPU, RAM) и не заглядывать в pg_stat_activity — проблема может быть внутри PostgreSQL при здоровом сервере.

---

## Чек-лист для самопроверки

- [ ] Знаю 4 первых команды при недоступности PostgreSQL: `pg_isready`, `systemctl status`, `df -h`, `journalctl`
- [ ] Умею найти причину медленной работы за 2 минуты: активные запросы, блокировки, checkpoint, hit ratio
- [ ] Умею диагностировать bloat через `n_dead_tup`
- [ ] Знаю причины replication lag и как их проверить
- [ ] Знаю что собрать при передаче проблемы DBA
- [ ] Никогда не перезапускаю PostgreSQL как первый шаг диагностики

---

## Попробуйте сами

1. Создайте искусственную блокировку: в первой сессии `BEGIN; UPDATE users SET name='test' WHERE id=1;` (не коммитить), во второй — тот же UPDATE. Пройдите по алгоритму: найдите блокировку через `pg_stat_activity` + `pg_blocking_pids`, убейте блокирующий запрос через `pg_terminate_backend`.

2. Заполните диск WAL-файлами: выполните несколько больших транзакций без архивации WAL. Подождите, пока заполнение диска достигнет ~95%. Попробуйте подключиться — ошибка. Диагностируйте за 2 минуты по алгоритму.

3. Создайте нагрузку через `pgbench -c 20 -T 60`. В соседней сессии смотрите `pg_stat_activity`, `pg_stat_bgwriter`, cache hit ratio. Как меняются показатели под нагрузкой? Какие запросы pgbench выполняет?
