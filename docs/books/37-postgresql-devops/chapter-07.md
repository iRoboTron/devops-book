# Глава 7: Медленные запросы — pg_stat_statements и EXPLAIN

## Что вы узнаете

- как включить `pg_stat_statements` и найти самые медленные запросы;
- как читать вывод `EXPLAIN ANALYZE` — три главных сигнала проблемы;
- когда добавить индекс и как это сделать без блокировки;
- полезные расширения PostgreSQL для DevOps.

## pg_stat_statements: найти медленный запрос

### Включение расширения

`pg_stat_statements` — расширение которое собирает статистику по всем выполняемым запросам. Нужно знать какие запросы самые частые, самые медленные и какие генерируют больше всего данных.

```sql
-- Включить расширение (один раз)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

Для сбора статистики при старте PostgreSQL нужно добавить модуль в `shared_preload_libraries`:

```ini
# postgresql.conf — требует restart PostgreSQL
shared_preload_libraries = 'pg_stat_statements'
```

После перезапуска расширение автоматически собирает статистику по всем запросам с начала работы сервера.

### Топ запросов по суммарному времени

Самый типичный запрос: найти запросы которые проводят в базе больше всего времени.

```sql
-- Топ-10 запросов по суммарному времени выполнения
SELECT
    substring(query, 1, 100) AS query,
    calls,
    round(total_exec_time::numeric, 2) AS total_ms,
    round(mean_exec_time::numeric, 2) AS avg_ms,
    round(stddev_exec_time::numeric, 2) AS stddev_ms,
    rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

`total_exec_time` — суммарное время всех выполнений. Запрос может быть средним по скорости (50ms) но вызываться миллион раз — в сумме наберётся больше всех.

### Топ запросов по среднему времени

Запросы с высоким `mean_exec_time` — самые медленные в каждом отдельном выполнении.

```sql
-- Топ-10 по среднему времени выполнения
SELECT
    substring(query, 1, 100) AS query,
    calls,
    round(mean_exec_time::numeric, 2) AS avg_ms,
    round(stddev_exec_time::numeric, 2) AS stddev_ms
FROM pg_stat_statements
WHERE calls > 100   -- только часто выполняемые
ORDER BY mean_exec_time DESC
LIMIT 10;
```

Фильтр `calls > 100` исключает редко выполняемые запросы (одноразовые отчёты, миграции) — они могут быть медленными но не влияют на общую производительность.

### stddev_exec_time: нестабильные запросы

Стандартное отклонение (`stddev_exec_time`) показывает вариативность времени выполнения. Если `stddev` больше `mean` — запрос то быстрый (из кэша), то медленный (с диска). Это сигнал что `shared_buffers` мал или данные не помещаются в память.

```sql
-- Запросы с высокой вариативностью (stddev > mean)
SELECT
    substring(query, 1, 80) AS query,
    calls,
    round(mean_exec_time::numeric, 2) AS avg_ms,
    round(stddev_exec_time::numeric, 2) AS stddev_ms
FROM pg_stat_statements
WHERE calls > 100 AND stddev_exec_time > mean_exec_time
ORDER BY stddev_exec_time DESC
LIMIT 10;
```

### Сброс статистики

```sql
SELECT pg_stat_statements_reset();
```

Полезно сбросить после деплоя новой версии приложения или после миграции — чтобы видеть статистику только по новой версии.

> ☠️ **Осторожно:** `pg_stat_statements_reset()` сбрасывает всю накопленную статистику без возможности восстановления. Выполнять только когда точно нужно, например, перед A/B тестированием изменений.

## EXPLAIN ANALYZE: читаем план запроса

`EXPLAIN ANALYZE` показывает как PostgreSQL собирается выполнить запрос (план) и сколько времени каждый шаг занял в реальности.

### Структура вывода

```sql
EXPLAIN ANALYZE
SELECT u.name, count(o.id)
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE u.created_at > '2026-01-01'
GROUP BY u.name;
```

Вывод:

```
Hash Join  (cost=142.50..3450.80 rows=1500 width=...
  Hash Cond: (o.user_id = u.id)
  ->  Seq Scan on orders o  (cost=0.00..2034.00 rows=100000 width=...)
  ->  Hash  (cost=140.00..140.00 rows=200 width=...)
        ->  Index Scan using idx_users_created_at on users u
              (cost=0.29..140.00 rows=200 width=...)
              Index Cond: (created_at > '2026-01-01'::date)
```

Каждый узел плана показывает:

- `cost` — оценка планировщика (первое число = старт, второе = общая стоимость);
- `rows` — ожидаемое количество строк;
- `width` — средняя ширина строки в байтах.

Когда добавляете `ANALYZE`, план дополняется реальными значениями:

```
(cost=... rows=...) (actual time=0.045..0.052 rows=10 loops=1)
```

- `actual time` — реальное время выполнения (первое = начало первого вызова, второе = конец последнего);
- `rows` — реальное количество строк;
- `loops` — сколько раз узел выполнялся.

## Три главных сигнала проблемы в EXPLAIN

Не нужно читать EXPLAIN как DBA на 4 страницы. DevOps-инженеру достаточно знать три паттерна которые всегда сигнализируют о проблеме.

### Сигнал 1: Seq Scan на большой таблице

```
Seq Scan on orders  (cost=0.00..45231.00 rows=1500000 width=...)
                      (actual time=0.012..125.432 rows=1500000 loops=1)
```

Полное сканирование таблицы на 1.5 млн строк. Каждый раз когда выполняется этот запрос, PostgreSQL читает всю таблицу с диска.

Что делать: добавить индекс на колонку из условия WHERE или JOIN.

```sql
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
```

После создания индекса план изменится на:

```
Index Scan using idx_orders_user_id on orders
  (cost=0.43..12.67 rows=150 width=...)
  (actual time=0.015..0.032 rows=47 loops=1)
```

Разница: вместо чтения 1.5 млн строк — чтение нескольких страниц индекса.

### Сигнал 2: rows estimation далеко от actual

Планировщик PostgreSQL оценивает количество строк чтобы выбрать оптимальную стратегию. Если оценка неверна — план будет неоптимальным.

```
Hash Join  (cost=... rows=10 width=...) (actual ... rows=150000 width=...)
                         ^ план думал 10 строк, а фактически 150 000
```

Планировщик выбрал Hash Join (хорош для маленького результата), но фактический результат в 15000 раз больше — на больших данных Hash Join может быть неэффективен.

Причины: устаревшая статистика, неравномерное распределение данных.

Что делать:

```sql
-- Обновить статистику
ANALYZE orders;
```

Если проблема повторяется — увеличить `default_statistics_target`:

```ini
# postgresql.conf
default_statistics_target = 500   ; default 100
```

Чем выше значение, тем детальнее статистика, но тем дольше выполняется ANALYZE.

### Сигнал 3: Nested Loop на большом dataset

```
Nested Loop  (cost=... rows=...) (actual time=... loops=1)
  ->  Seq Scan on users  (cost=... rows=50000 loops=1)
  ->  Index Scan using idx_orders_user_id on orders
        (cost=... rows=1 loops=50000)
```

`loops=50000` на внутреннем узле — Nested Loop выполняется для каждой строки из внешнего запроса. Это N+1 проблема на уровне базы данных: для каждого пользователя делается отдельный запрос в таблицу заказов.

На больших таблицах Nested Loop убивает производительность. PostgreSQL иногда выбирает этот план если планировщик недооценил количество внешних строк.

Что делать: переписать запрос с JOIN вместо подзапроса, или проверить наличие индекса на колонке JOIN. В крайнем случае — использовать `pg_hint_plan` (см. раздел расширений).

## Индексы: когда добавлять и когда нет

### Поиск таблиц где не хватает индексов

```sql
-- Таблицы где Seq Scan преобладает над Index Scan
SELECT schemaname, relname, seq_scan, idx_scan,
       n_live_tup,
       seq_scan - idx_scan AS seq_minus_idx
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
  AND n_live_tup > 10000
ORDER BY seq_scan - idx_scan DESC;
```

Если на таблице с 100 000 строк `seq_scan >> idx_scan» — скорее всего, не хватает индексов для типичных запросов. Но не спешите добавлять: если таблица маленькая (несколько тысяч строк), Seq Scan может быть быстрее Index Scan.

### Создание индекса без блокировки

```sql
-- Обычный CREATE INDEX — блокирует таблицу на запись
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- CREATE INDEX CONCURRENTLY — НЕ блокирует таблицу
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
```

> ☠️ **Осторожно:** `CREATE INDEX` (без CONCURRENTLY) блокирует всю таблицу до завершения. На таблице из 10 млн строк это минуты. В production всегда использовать `CREATE INDEX CONCURRENTLY`.

CONCURRENTLY работает дольше (создаёт индекс в фоне, не блокируя INSERT/UPDATE/DELETE), но это единственный безопасный способ для production.

```sql
-- Удаление индекса тоже может быть CONCURRENTLY
DROP INDEX CONCURRENTLY idx_orders_user_id;
```

### Неиспользуемые индексы

Индексы ускоряют чтение но замедляют запись (каждый INSERT/UPDATE/DELETE требует обновления индекса). Если индекс не используется — он только занимает место и замедляет запись.

```sql
-- Найти неиспользуемые индексы (idx_scan = 0)
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;
```

Прежде чем удалять индекс с `idx_scan = 0`, убедитесь что:
1. Статистика собиралась достаточно долго (хотя бы сутки production нагрузки).
2. Индекс не используется для UNIQUE-ограничений или foreign key (проверить в схеме БД).

```sql
-- Размер неиспользуемых индексов
SELECT
    schemaname, tablename, indexname, idx_scan,
    pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_relation_size(schemaname||'.'||indexname) DESC;
```

## Полезные расширения (extensions)

### pg_stat_statements (обязателен)

Сбор статистики запросов. Описан в этой главе. Включается в `shared_preload_libraries`. Должен быть включён на каждом production сервере PostgreSQL.

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### pg_partman — автоматическое партиционирование

Управление партициями (секциями) таблиц: автоматическое создание новых партиций по времени, удаление старых.

```sql
CREATE EXTENSION IF NOT EXISTS pg_partman;

-- Настроить ежедневное партиционирование
SELECT partman.create_parent(
    p_parent_table := 'public.orders',
    p_control := 'created_at',
    p_type := 'native',
    p_interval := '1 day',
    p_premake := 30
);
```

Когда использовать: таблицы с временными данными (логи, события, аудит), которые растут бесконечно и старые данные нужно удалять. Без партиционирования `DELETE FROM orders WHERE created_at < now() - interval '1 year'` создаст огромную нагрузку и bloat.

### pg_hint_plan — подсказки планировщику

Позволяет принудительно указать PostgreSQL какой план выполнения использовать. Только для крайних случаев, когда планировщик систематически ошибается.

```sql
CREATE EXTENSION IF NOT EXISTS pg_hint_plan;

/*+
    SeqScan(orders)
*/
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 42;
```

Подсказки: `SeqScan(table)`, `IndexScan(table index)`, `HashJoin(a b)`, `NestedLoop(a b)`.

> ☠️ **Осторожно:** **Использовать когда все остальные методы не помогли.** Подсказки планировщику — костыль. После изменения данных или версии PostgreSQL подсказка может стать неверной и ухудшить производительность.

### auto_explain — автологирование медленных запросов

Автоматически логирует EXPLAIN ANALYZE для запросов дольше указанного порога. Незаменимо для диагностики в production — вы видите не только что запрос был медленным, но и почему.

```ini
# postgresql.conf
shared_preload_libraries = 'pg_stat_statements, auto_explain'

auto_explain.log_min_duration = 1000   ; логировать EXPLAIN для запросов > 1s
auto_explain.log_analyze = on          ; включать ANALYZE
auto_explain.log_buffers = on          ; показывать буферы
auto_explain.log_nested_statements = on; логировать вложенные запросы (функции)
```

После reload конфига все запросы дольше 1 секунды будут попадать в лог PostgreSQL с полным EXPLAIN ANALYZE.

```bash
# Смотреть в логе
tail -f /var/log/postgresql/postgresql-16-main.log | grep "duration"
```

### pg_permissions — аудит прав

Проверка и документирование прав на таблицы, схемы, базы данных.

```sql
CREATE EXTENSION IF NOT EXISTS pg_permissions;

-- Проверить что нет лишних прав
SELECT * FROM permissons_check();
```

Когда использовать: аудит безопасности, проверка что приложение не получило лишних прав после миграции.

### pg_cron — планировщик задач внутри PostgreSQL

Позволяет запускать SQL-функции по расписанию без внешнего cron.

```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- VACUUM каждый день в 3:00
SELECT cron.schedule('nightly-vacuum', '0 3 * * *', 'VACUUM');

-- Обновление статистики каждый час
SELECT cron.schedule('hourly-analyze', '0 * * * *', 'ANALYZE');

-- Удалить задачу
SELECT cron.unschedule('nightly-vacuum');
```

Когда использовать: вместо внешнего cron когда нужно выполнять SQL-операции по расписанию и внешний cron недоступен (например, облачный PostgreSQL).

## Типичные ошибки

- **Добавлять индекс на колонку с низкой кардинальностью** (boolean, status с 2-3 значениями). Планировщик всё равно выберет Seq Scan — индекс не поможет.
- **Смотреть только на `total_exec_time` в pg_stat_statements.** Важнее `mean_exec_time` и `calls`. Запрос с 100ms * 1000 calls хуже чем 10s * 10 calls.
- **Читать только `cost` в EXPLAIN без `actual time`.** cost — это оценка планировщика, actual — реальность. Если они сильно расходятся — проблема со статистикой.
- **Не забыть `CONCURRENTLY` при создании индекса в production.** Обычный CREATE INDEX блокирует таблицу. Вспоминают когда production падает.
- **Удалять неиспользуемые индексы без проверки назначения.** Индекс может быть нужен для UNIQUE-ограничения, foreign key или использоваться раз в сутки в отчёте.
- **Не сбрасывать `pg_stat_statements` после крупного деплоя.** Трудно отличить старые проблемы от новых.

## Чек-лист для самопроверки

- [ ] Включил `pg_stat_statements` в `shared_preload_libraries`
- [ ] Умею найти топ медленных запросов по `total_exec_time` и `mean_exec_time`
- [ ] Умею читать вывод `EXPLAIN ANALYZE` и найти три главных сигнала проблемы
- [ ] Знаю когда добавлять индекс и что использовать `CONCURRENTLY`
- [ ] Умею найти неиспользуемые индексы и оценить их размер
- [ ] Включил `auto_explain` для диагностики медленных запросов
- [ ] Знаю о `pg_partman`, `pg_hint_plan`, `pg_cron`, `pg_permissions` и когда их применять

## Попробуйте сами

1. Создайте таблицу со 100 000 строк (`INSERT INTO mytable SELECT generate_series(1, 100000), random()`). Выполните `EXPLAIN ANALYZE SELECT * FROM mytable WHERE id = 50000` — Seq Scan. Добавьте индекс. Повторите EXPLAIN — Index Scan. Разница в `actual time`?

2. Включите `pg_stat_statements`. Выполните несколько разных запросов 100+ раз каждый (можно скриптом на bash). Посмотрите `pg_stat_statements` — найдите самый медленный по `total_exec_time` и по `mean_exec_time`. Это разные запросы?

3. Найдите в вашей базе неиспользуемые индексы через `pg_stat_user_indexes`. Посмотрите сколько места они занимают. Если есть кандидаты — проверьте что они действительно не нужны (нет UNIQUE, нет FK). Удалите один такой индекс и замерьте производительность записи.

4. Включите `auto_explain` с порогом 500ms. Создайте запрос который выполняется дольше секунды (например, Seq Scan на большой таблице). Проверьте лог PostgreSQL — найдите EXPLAIN ANALYZE этого запроса.
