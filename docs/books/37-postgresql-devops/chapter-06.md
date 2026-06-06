# Глава 6: Мониторинг — что смотреть и как

## Что вы узнаете

- ключевые системные представления (`pg_stat_*`) которые должен знать DevOps;
- метрики для Prometheus через `postgres_exporter`;
- минимальный набор метрик на дашборде с конкретными порогами;
- как найти активные запросы, заблокированные сессии и убить их;
- pgbench: нагрузочное тестирование и методология;
- vacuum troubleshooting: диагностика dead tuples и bloat.

## pg_stat_activity: кто сейчас в базе

Первое что вы делаете когда PostgreSQL «тормозит» — смотрите кто подключён и что делает. Основное представление для этого — `pg_stat_activity`.

```sql
-- Активные соединения, их статус и что выполняют
SELECT pid, usename, application_name, client_addr,
       state, wait_event_type, wait_event,
       now() - state_change AS duration,
       left(query, 80) AS query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

Колонка `state` принимает значения:

- `active` — запрос выполняется прямо сейчас;
- `idle` — соединение открыто, но ничего не делает;
- `idle in transaction` — открыта транзакция (`BEGIN;`), внутри ничего не делается;
- `idle in transaction (aborted)` — транзакция в состоянии ошибки, не завершена.

```sql
-- Быстрая сводка по состояниям
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
```

Если `idle in transaction` > 20 — это инцидент. Открытые транзакции держат блокировки, препятствуют очистке dead tuples, могут остановить весь сервер.

### Заблокированные сессии

```sql
-- Кто ждёт блокировку
SELECT pid, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE wait_event_type = 'Lock';
```

`wait_event_type = 'Lock'` с `wait_event = 'relation'` — запрос ждёт блокировки таблицы. Чаще всего одна долгая транзакция блокирует всех остальных.

```sql
-- Иерархия блокировок: кто кого заблокировал
SELECT blocked.pid AS blocked_pid,
       blocked.query AS blocked_query,
       blocking.pid AS blocking_pid,
       blocking.query AS blocking_query,
       now() - blocking.query_start AS blocking_duration
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE cardinality(pg_blocking_pids(blocked.pid)) > 0;
```

Функция `pg_blocking_pids(pid)` возвращает массив PID-ов которые блокируют указанный процесс. Это главный инструмент диагностики lock contention.

### Размеры базы данных

```sql
-- Размеры всех БД
SELECT datname,
       pg_size_pretty(pg_database_size(datname)) AS size
FROM pg_database
ORDER BY pg_database_size(datname) DESC;

-- Размеры таблиц (топ-20)
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total,
       pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_only,
       pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;
```

`pg_total_relation_size` включает размер таблицы + индексы + TOAST. Если `indexes` занимает больше `table_only` — возможно, лишние индексы.

### Статистика таблиц: vacuum и dead tuples

```sql
SELECT schemaname, relname,
       n_live_tup, n_dead_tup,
       round(n_dead_tup * 100.0 / (n_live_tup + n_dead_tup + 1), 1) AS dead_pct,
       last_vacuum, last_autovacuum,
       last_analyze, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 10;
```

Если `dead_pct > 20%` — автовакуум не справляется. Если `last_autovacuum IS NULL` для таблицы с изменениями — автовакуум ни разу не запускался.

## postgres_exporter: метрики в Prometheus

`postgres_exporter` — стандартный экспортёр метрик PostgreSQL для Prometheus. Запускается отдельным контейнером, подключается к PostgreSQL как обычный клиент и собирает метрики.

```yaml
# docker-compose.yml — postgres_exporter
services:
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: pg_exporter
    restart: unless-stopped
    environment:
      DATA_SOURCE_NAME: "postgresql://monitoring:MonitorPass@postgres:5432/postgres?sslmode=disable"
    ports:
      - "9187:9187"
    depends_on:
      postgres:
        condition: service_healthy
```

> ☠️ **Осторожно:** `DATA_SOURCE_NAME` содержит пароль в открытом виде в docker-compose.yml. Для production используйте `DATA_SOURCE_NAME_FILE` или Docker secrets.

Пользователь для мониторинга с минимальными правами:

```sql
CREATE USER monitoring WITH PASSWORD 'MonitorPass';
GRANT pg_monitor TO monitoring;   -- PostgreSQL 10+: роль pg_monitor
```

Роль `pg_monitor` (доступна с PostgreSQL 10) даёт доступ ко всем `pg_stat_*` представлениям — ровно то что нужно экспортёру.

После запуска откройте `http://localhost:9187/metrics` — вы увидите сотни метрик с префиксами `pg_stat_*`, `pg_database_*`, `pg_locks_*`.

## Ключевые метрики: что смотреть на дашборде

Не все метрики одинаково полезны. Вот минимальный набор для дашборда с конкретными порогами тревоги:

| Метрика | Норма | Тревога |
|---|---|---|
| pg_up | 1 | 0 = PostgreSQL недоступен |
| Активные соединения | < 80% max_connections | > 90% max_connections |
| Idle in transaction | < 5 | > 20 (утечка транзакций) |
| Рост размера БД за день | < 5% | > 20% |
| Replication lag (секунды) | < 10s | > 60s |
| Checkpoint frequency | < 1/min | > 5/min (нагрузка на WAL) |
| Dead tuples (доля) | < 20% | > 50% (нужен VACUUM) |
| Cache hit ratio | > 95% | < 90% (мало shared_buffers) |
| TPS (транзакции/сек) | baseline +/- 20% | -50% от baseline |

### PromQL для ключевых метрик

```promql
# Cache hit ratio (ratio of buffer hits vs disk reads)
# Должен быть > 95%. Если < 90% — увеличить shared_buffers
rate(pg_stat_bgwriter_buffers_alloc_total[5m]) /
(
  rate(pg_stat_bgwriter_buffers_alloc_total[5m]) +
  rate(pg_stat_bgwriter_buffers_clean_total[5m])
)

# Доля dead tuples по таблице (грубо: bloat indicator)
# Если > 0.5 — автовакуум не справляется
pg_stat_user_tables_n_dead_tup / (pg_stat_user_tables_n_live_tup + 1)

# Активные соединения в процентах от max_connections
pg_stat_activity_count{state="active"} / pg_settings_max_connections * 100

# Idle in transaction (alert if > 20)
pg_stat_activity_count{state="idle in transaction"}

# Replication lag in bytes (для синхронной — alert если > 0)
pg_stat_replication_replay_lsn{}

# TPS rate
rate(pg_stat_database_xact_commit_total[1m]) +
rate(pg_stat_database_xact_rollback_total[1m])
```

### Cache hit ratio: почему это важно

Cache hit ratio показывает какой процент запросов данных удовлетворяется из `shared_buffers` (кэш PostgreSQL) без чтения с диска.

- > 99% — отлично, данные помещаются в кэш;
- 95-99% — хорошо, типичное значение для веб-приложения;
- < 90% — плохо, `shared_buffers` мал или нагрузка не кэшируется.

Первый шаг при cache hit ratio < 90% — увеличить `shared_buffers` до 25% RAM. Если не помогает — проверять индексы (Seq Scan вместо Index Scan).

## Убить зависший запрос

Когда запрос завис на блокировке или выполняется слишком долго:

```sql
-- Послать SIGTERM — запрос завершится после текущей операции
SELECT pg_cancel_backend(pid);

-- Послать SIGKILL — немедленное завершение
SELECT pg_terminate_backend(pid);
```

Разница: `pg_cancel_backend` просит запрос остановиться (запрос может не отреагировать мгновенно). `pg_terminate_backend` обрывает соединение принудительно.

```sql
-- Найти и убить все запросы дольше 5 минут
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state != 'idle'
  AND now() - query_start > interval '5 minutes'
  AND pid != pg_backend_pid();
```

> ☠️ **Осторожно:** `pg_terminate_backend` обрывает соединение принудительно. Текущая транзакция откатывается. Если убить запрос который держит блокировку — блокировка снимается, но другие транзакции могут получить неконсистентные данные если не обрабатывают ошибки правильно.

## Vacuum troubleshooting: диагностика и решение

### Почему vacuum нужен

PostgreSQL использует MVCC (Multiversion Concurrency Control) для изоляции транзакций. Когда вы делаете UPDATE или DELETE, старые версии строк не удаляются сразу — они помечаются как "dead tuples". VACUUM очищает эти dead tuples и возвращает место для новых записей.

Без vacuum:
- таблицы и индексы раздуваются (bloat);
- производительность деградирует (приходится читать больше страниц);
- запросы становятся медленнее.

### Диагностика dead tuples

```sql
-- Доля dead tuples по всем таблицам
SELECT relname,
       n_live_tup, n_dead_tup,
       round(n_dead_tup * 100.0 / (n_live_tup + n_dead_tup + 1), 1) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY dead_pct DESC
LIMIT 20;
```

Если `dead_pct > 20%` — проблема. Если > 50% — срочный VACUUM.

```sql
-- Последний автовакуум по таблицам
SELECT relname, last_autovacuum, last_autoanalyze,
       autovacuum_count, autoanalyze_count
FROM pg_stat_user_tables
WHERE last_autovacuum IS NULL
   OR last_autovacuum < now() - interval '1 day'
ORDER BY last_autovacuum NULLS FIRST;
```

Если `last_autovacuum IS NULL` — автовакуум ни разу не запускался. Это красный флаг.

### Почему autovacuum отстаёт

Три основные причины:

**1. Long-running транзакции**

Долгие транзакции держат "старое" значение xmin — PostgreSQL не может очистить dead tuples которые были созданы после начала этой транзакции, даже если они уже не нужны.

```sql
-- Найти долгие транзакции
SELECT pid, now() - xact_start AS age, state, query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY age DESC
LIMIT 5;
```

Если есть транзакция старше 5 минут — это кандидат на завершение. Если старше часа — причина проблем с autovacuum.

**2. Интенсивная запись (больше 10% таблицы в день)**

Autovacuum запускается когда количество dead tuples превышает порог:
- `autovacuum_vacuum_threshold` + `autovacuum_vacuum_scale_factor × n_live_tup`

При scale_factor = 0.05 (default) и таблице 1 млн строк, autovacuum запустится только когда dead tuples превысят 1000 + 0.05 * 1000000 = 51000. При интенсивной записи это может накапливаться быстрее чем успевает autovacuum.

Решение: уменьшить `autovacuum_vacuum_scale_factor` для проблемных таблиц.

**3. Слишком мало autovacuum workers**

```ini
# postgresql.conf — тюнинг autovacuum для высоконагруженной БД
autovacuum_max_workers = 4           # увеличено с 3
autovacuum_vacuum_scale_factor = 0.01  # чаще vacuum (было 0.05)
autovacuum_vacuum_threshold = 1000     # минимальное число dead tuples для запуска
autovacuum_analyze_scale_factor = 0.01
autovacuum_vacuum_cost_delay = 2ms     # пауза между I/O операциями
autovacuum_vacuum_cost_limit = 1000    # лимит I/O за единицу времени
```

### Manual VACUUM

```sql
-- Обычный VACUUM (не блокирует чтение/запись)
VACUUM users;

-- VACUUM + обновление статистики
VACUUM ANALYZE users;

-- VACUUM конкретных колонок индекса
VACUUM VERBOSE ANALYZE users;
```

`VACUUM VERBOSE` показывает детальный лог: сколько dead tuples очищено, сколько страниц освобождено.

### VACUUM FULL — опасная операция

```sql
-- VACUUM FULL (блокирует таблицу!)
VACUUM FULL users;
```

> ☠️ **Осторожно:** `VACUUM FULL` блокирует таблицу на запись на всё время выполнения. Для production — только в запланированное окно обслуживания. Обычный `VACUUM` не блокирует. `VACUUM FULL` создаёт новую копию таблицы и заменяет старую — нужно вдвое больше места на диске.

`VACUUM FULL` нужен когда обычный VACUUM уже не помогает и таблица критически раздута (bloat > 50%). В повседневной работе достаточно обычного VACUUM.

### Принятие решений по vacuum

```
Есть ли dead tuples > 20%?
├── Нет → всё в порядке
├── Да → Autovacuum работает (last_autovacuum недавно)?
│   ├── Да → Подождать, возможно не успел очистить
│   ├── Нет → Есть ли long-running транзакции?
│   │   ├── Да → Завершить/убить долгую транзакцию
│   │   ├── Нет → Интенсивная запись?
│   │       ├── Да → Уменьшить scale_factor для этой таблицы
│   │       └── Нет → Ручной VACUUM ANALYZE
```
## pgbench: нагрузочное тестирование

pgbench — встроенный инструмент PostgreSQL для бенчмаркинга. Позволяет измерить TPS (транзакции/сек) и latency. Используется для проверки влияния изменений конфигурации.

### Установка

pgbench поставляется вместе с PostgreSQL в пакете `postgresql-contrib`:

```bash
# Ubuntu
sudo apt install postgresql-contrib-16

# Docker (уже включён в образ postgres)
docker exec postgres pgbench --version
```

### Инициализация тестовой БД

```bash
# Создать тестовую БД
createdb -U postgres testbench

# Инициализация (масштаб 50 = ~750MB, 5 млн строк)
pgbench -U postgres -i -s 50 testbench

# Ключи:
# -i  = инициализировать таблицы
# -s  = масштаб (1 = ~15MB, 10 = ~150MB, 50 = ~750MB)
```

pgbench создаёт 4 таблицы: `pgbench_accounts`, `pgbench_branches`, `pgbench_tellers`, `pgbench_history`. Стандартный сценарий — симуляция банковского приложения: UPDATE баланса, SELECT остатка, INSERT в историю.

### Запуск теста

```bash
# Простой тест: 10 клиентов, 4 потока, 30 секунд
pgbench -U postgres -c 10 -j 4 -T 30 testbench
```

Результат:

```
starting vacuum...end.
transaction type: <builtin: TPC-B (sort of)>
scaling factor: 50
query mode: simple
number of clients: 10
number of threads: 4
maximum number of tries: 1
number of transactions per client: 100
number of transactions actually processed: 1000/1000
number of failed transactions: 0 (0.000%)
latency average = 6.524 ms
latency stddev = 2.148 ms
initial connection time = 9.281 ms
tps = 1523.452020 (including connections establishing)
tps = 1541.012408 (excluding connections establishing)
```

Основные показатели:

- **tps** — транзакций в секунду (чем выше, тем лучше);
- **latency average** — среднее время выполнения транзакции (чем ниже, тем лучше);
- **latency stddev** — разброс latency (низкий stddev = стабильная производительность);
- **number of failed transactions** — должно быть 0.

### Методология тестирования

```text
Процедура тестирования:
1. Замерить baseline (текущая конфигурация)
2. Изменить ОДИН параметр
3. Перезагрузить/перезапустить PostgreSQL
4. Разогреть базу (warmup: pgbench -T 30 перед замером)
5. Замерить снова
6. Сравнить TPS и latency с baseline
```

Правила:

- **Менять по одному параметру за раз.** Если изменить два параметра и TPS вырос — непонятно что сработало.
- **Разогрев базы.** После перезапуска shared_buffers пуст. Нужно прогнать pgbench 30-60 секунд перед замером.
- **Минимум 3 замера** для каждого набора параметров. Брать среднее.
- **Условия одинаковы.** Нагрузка на сервер, время суток, версия PostgreSQL.

```bash
# Пример: сравнить shared_buffers = 256MB vs 512MB

# Baseline
pgbench -U postgres -c 20 -j 4 -T 60 testbench  # записать TPS

# Изменить shared_buffers
psql -U postgres -c "ALTER SYSTEM SET shared_buffers = '512MB';"
# restart требуется для shared_buffers

# Разогрев
pgbench -U postgres -c 20 -j 4 -T 30 testbench

# Замер
pgbench -U postgres -c 20 -j 4 -T 60 testbench  # сравнить TPS
```

### Тест с PgBouncer

```bash
# Сравнить TPS без PgBouncer и через PgBouncer
# Без PgBouncer (прямое подключение)
pgbench -U appuser -h localhost -p 5432 -c 100 -j 8 -T 60 testbench

# Через PgBouncer (transaction mode)
pgbench -U appuser -h pgbouncer -p 6432 -c 100 -j 8 -T 60 testbench
```

При большом числе клиентов (100+) TPS через PgBouncer обычно выше, потому что PostgreSQL не тратит ресурсы на форк процессов.

### Кастомный сценарий

```bash
# Симулировать нагрузку близкую к вашему приложению
# Создать файл сценария custom_bench.sql:
# \set aid random(1, 100000 * :scale)
# SELECT * FROM users WHERE id = :aid;
# UPDATE accounts SET balance = balance + 100 WHERE aid = :aid;

pgbench -U postgres -f custom_bench.sql -c 10 -T 60 testbench
```

## Типичные ошибки

- **Не мониторить `idle in transaction`** — открытые транзакции которые держат блокировки. При накоплении — весь сервер встаёт.
- **Cache hit ratio < 90% игнорируется** — первый признак что `shared_buffers` мал. Не индексы, не запросы — память.
- **Мониторить только `pg_up`** — узнаёшь о деградации производительности только от пользователей.
- **Не мониторить replication lag** — реплика могла отстать на часы, никто не знает.
- **Запускать VACUUM FULL как рутинную операцию** — блокирует таблицу. Обычный VACUUM достаточно в 95% случаев.
- **pgbench с одним замером** — результаты сильно варьируются. Нужно минимум 3 замера.
- **Не делать warmup перед pgbench** — замер на холодном кэше даёт заниженные TPS.
- **Менять несколько параметров одновременно** — невозможно определить что сработало.

## Чек-лист для самопроверки

- [ ] Умею найти активные запросы и зависшие транзакции через `pg_stat_activity`
- [ ] Умею найти что блокирует что через `pg_blocking_pids`
- [ ] Настроил `postgres_exporter` и вижу метрики в Prometheus
- [ ] Знаю 5 ключевых метрик и их пороги (cache hit ratio, TPS, dead tuples, idle in transaction, replication lag)
- [ ] Умею диагностировать проблемы с autovacuum: dead tuples, long-running транзакции
- [ ] Знаю разницу между VACUUM и VACUUM FULL
- [ ] Умею запустить pgbench и интерпретировать TPS/latency
- [ ] Знаю методологию тестирования: baseline -> одно изменение -> замер -> сравнение

## Попробуйте сами

1. Откройте транзакцию (`BEGIN;`) и не закрывайте её. В другом соединении запустите `SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction';` Нашли? Теперь закоммитьте и убедитесь что запись исчезла.

2. Создайте ситуацию блокировки: в первом соединении `BEGIN; UPDATE users SET name='test' WHERE id=1;` (не коммитить). Во втором: `UPDATE users SET name='other' WHERE id=1;` — завис. Найдите блокировку через `pg_blocking_pids`. Убейте блокирующий запрос через `pg_terminate_backend`.

3. Настройте `postgres_exporter` в Docker Compose. Откройте `http://localhost:9187/metrics` — найдите `pg_stat_activity_count` и `pg_database_size_bytes`.

4. Запустите pgbench на стандартной конфигурации PostgreSQL. Запишите TPS. Увеличьте `shared_buffers` в 2 раза. Перезапустите. Снова pgbench — изменился TPS? Почему?

5. Создайте таблицу с 1 млн строк. Сделайте UPDATE всех строк 10 раз. Посмотрите `n_dead_tup` через `pg_stat_user_tables`. Запустите VACUUM. Проверьте снова. Уменьшилось?
