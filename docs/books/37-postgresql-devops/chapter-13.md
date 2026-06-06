# Глава 13: Тюнинг производительности — память, vacuum, pgbench

## Что вы узнаете

- как настроить память PostgreSQL под типичное веб-приложение с пониманием trade-off'ов;
- что такое vacuum, bloat и как настроить autovacuum для высоконагруженной БД;
- как использовать pgbench для измерения TPS и проверки влияния изменений конфигурации;
- как не навредить при тюнинге.

**Цель:** вы можете осмысленно настроить PostgreSQL под свою нагрузку, не копируя вслепую рекомендации из интернета. Понимаете, какой параметр за что отвечает и когда его увеличение бесполезно или опасно.

---

## Память: shared_buffers, work_mem, maintenance_work_mem, effective_cache_size

### Стартовые значения

| Параметр | Рекомендация | Что делает | Комментарий |
|----------|-------------|------------|-------------|
| `shared_buffers` | 25% RAM, макс. 8GB | Кэш страниц PostgreSQL | Больше 8GB не даёт прироста |
| `effective_cache_size` | 75% RAM | Подсказка планировщику | PostgreSQL знает, сколько кэша есть всего |
| `work_mem` | 16-64MB | На сортировку, hash-агрегацию | Умножить на max_connections! |
| `maintenance_work_mem` | 256-1024MB | Для VACUUM, CREATE INDEX, ADD FOREIGN KEY | Только один процесс обычно |
| `wal_buffers` | 64MB | Буфер WAL перед записью | 16MB по умолчанию |

### Trade-off'ы

**shared_buffers > 8GB:** PostgreSQL использует свой кэш страниц, но ОС тоже кэширует файлы. После 25-30% RAM PostgreSQL начинает конкурировать с OS page cache за одни и те же страницы. Правило: `shared_buffers` = 25% RAM, остальное отдать OS page cache. На сервере с 32GB RAM: `shared_buffers` = 8GB, 24GB оставить OS.

**work_mem × max_connections = OOM:** Если `work_mem = 256MB`, а `max_connections = 200`, то потенциально 200 × 256MB = 50GB RAM только на сортировки. При реальной RAM 32GB — OOM killer. Всегда считайте: `work_mem × max_connections × 0.5 ≤ (RAM - shared_buffers)`. Коэффициент 0.5 — потому что не все соединения сортируют одновременно, но worst case всё равно возможен.

**maintenance_work_mem можно ставить больше,** потому что VACUUM и CREATE INDEX обычно выполняются по одному. 1GB для `maintenance_work_mem` на сервере с 16GB RAM — нормально.

### Конфигурация для типичного веб-приложения

```ini
# postgresql.conf — стартовые значения
# Сервер: 8GB RAM, 4 vCPU

# Память
shared_buffers = 2GB              # 25% от 8GB
effective_cache_size = 6GB        # 75% от 8GB — подсказка планировщику
work_mem = 32MB                   # 32MB × 100 соединений = 3.2GB макс.
maintenance_work_mem = 512MB      # для VACUUM, CREATE INDEX
wal_buffers = 64MB

# Соединения
max_connections = 100             # если есть PgBouncer — хватит
superuser_reserved_connections = 3

# WAL и checkpoint
checkpoint_completion_target = 0.9
max_wal_size = 4GB
min_wal_size = 1GB
```

### Как подобрать для своего сервера

1. Узнать RAM сервера: `free -g`
2. `shared_buffers = RAM × 0.25` (но не > 8GB)
3. `effective_cache_size = RAM × 0.75`
4. `work_mem`: начать с 32MB, следить за `temp_files` в `pg_stat_database` — если много, увеличить
5. `maintenance_work_mem = min(RAM × 0.1, 1GB)`

---

## Тюнинг autovacuum

### Почему default autovacuum может не успевать

Настройки autovacuum по умолчанию рассчитаны на среднюю нагрузку. При высокоинтенсивной записи (обновление > 10% таблицы в день) дефолтные значения приводят к накоплению dead tuples, bloat таблиц и индексов, падению производительности.

Диагностика bloat подробно описана в главе 12, раздел "Vacuum troubleshooting".

### Конфигурация для высоконагруженной БД

```ini
# postgresql.conf — autovacuum tuning для высоконагруженной БД

autovacuum = on                          # никогда не выключать
autovacuum_max_workers = 3               # по умолчанию 3; увеличить до 4-5 на SSD
autovacuum_vacuum_scale_factor = 0.01    # чаще vacuum (было 0.05)
autovacuum_vacuum_threshold = 1000       # минимальное число dead tuples
autovacuum_analyze_scale_factor = 0.01
autovacuum_vacuum_cost_delay = 2ms       # пауза между операциями I/O
autovacuum_vacuum_cost_limit = 1000      # лимит I/O в единицу времени
```

### Объяснение параметров

| Параметр | Default | Heavy-load | Зачем |
|----------|---------|------------|-------|
| `autovacuum_vacuum_scale_factor` | 0.05 | 0.01 | Запускать vacuum при 1% dead tuples, а не 5% |
| `autovacuum_vacuum_threshold` | 50 | 1000 | Не запускать vacuum из-за 50 строк на большой таблице |
| `autovacuum_max_workers` | 3 | 4-5 | Больше параллельных vacuum'ов (только на SSD!) |
| `autovacuum_vacuum_cost_delay` | 20ms | 2ms | Меньше пауза = агрессивнее чистит |
| `autovacuum_vacuum_cost_limit` | 200 | 1000 | Выше лимит I/O за единицу времени |

### Пер-табличные настройки (для горячих таблиц)

Если одна таблица обновляется намного чаще других, можно настроить autovacuum индивидуально:

```sql
ALTER TABLE orders SET (
    autovacuum_vacuum_scale_factor = 0.005,
    autovacuum_vacuum_threshold = 500,
    autovacuum_analyze_scale_factor = 0.005
);
```

### Когда ручной VACUUM нужен

```sql
-- Для особо заbloat'ившихся таблиц
VACUUM ANALYZE orders;

-- VACUUM FULL — только в окно обслуживания!
-- VACUUM FULL orders;
```

> **Осторожно:** `VACUUM FULL` блокирует таблицу на запись. В production — только в запланированное окно обслуживания. Обычный `VACUUM` не блокирует чтение и запись.

---

## pgbench: методология тестирования

### Процедура тестирования

Чтобы проверить, как изменение конфигурации влияет на производительность, используйте единую методологию:

```
1. Замерить baseline (текущая конфигурация)
2. Изменить ОДИН параметр
3. Перезагрузить или перезапустить PostgreSQL
4. Разогреть базу (warmup)
5. Замерить снова
6. Сравнить TPS и latency с baseline
```

### Важные правила

- **Менять по одному параметру за раз.** Если изменить `shared_buffers` и `work_mem` одновременно и TPS вырос — вы не узнаете, что именно сработало.
- **Warmup перед замером.** Первый запуск pgbench будет медленнее — данные не в кэше. Сделайте короткий прогон (10-15 секунд) перед основным замером.
- **Несколько замеров.** Один замер может быть случайным. Сделайте 3 прогона по 60 секунд и возьмите среднее.
- **Фиксируйте всё:** версия конфига, дату, TPS, latency, количество failed connections.

### Пример

```bash
# Шаг 1: инициализация тестовой БД
pgbench -U postgres -i -s 100 testbench

# Шаг 2: baseline
pgbench -U postgres -c 10 -j 4 -T 60 testbench
# tps = 1523

# Шаг 3: меняем shared_buffers с 256MB на 1GB
# postgresql.conf: shared_buffers = '1GB'
sudo systemctl restart postgresql

# Шаг 4: warmup
pgbench -U postgres -c 10 -j 4 -T 15 testbench

# Шаг 5: замер
pgbench -U postgres -c 10 -j 4 -T 60 testbench
# tps = 1876  (+23%)
```

### Типовые сценарии тестирования

| Что меняем | Ожидаемый эффект | Измеряем |
|------------|-----------------|----------|
| `shared_buffers` 25% -> 40% RAM | TPS не растёт (конкуренция с OS cache) | TPS, cache hit ratio |
| `work_mem` 16MB -> 64MB | Снижение `temp_files`, рост TPS для сортировок | `temp_files` из `pg_stat_database` |
| `checkpoint_completion_target` 0.5 -> 0.9 | Меньше I/O spikes при checkpoint | checkpoints_timed/req из `pg_stat_bgwriter` |
| PgBouncer: 500 -> 20 соединений | TPS тех же, RAM сервера меньше | `top`, `free` на сервере |

### Кастомный сценарий

pgbench может выполнять ваш SQL-скрипт вместо встроенного:

```bash
# custom_bench.sql
BEGIN;
UPDATE users SET last_login = now() WHERE id = random() * 1000000 + 1;
SELECT count(*) FROM orders WHERE user_id = random() * 1000000 + 1;
COMMIT;

pgbench -U postgres -f custom_bench.sql -c 10 -T 60 testbench
```

---

## Cross-reference: что где смотреть

| Тема | Где в книге |
|------|-------------|
| Диагностика bloat и dead tuples | Глава 12, раздел "Vacuum troubleshooting" |
| pgbench: базовые команды | Глава 12, раздел "pgbench: измеряем производительность" |
| Мониторинг cache hit ratio, checkpoint | Глава 6, раздел "Ключевые метрики для дашборда" |
| EXPLAIN ANALYZE, медленные запросы | Глава 7 |
| Влияние `work_mem` на сортировки | Глава 7, раздел "EXPLAIN ANALYZE" |

---

## Типичные ошибки

- Копировать конфиг "для высоконагруженного PostgreSQL" из интернета — для вашей нагрузки может быть хуже. Тестируйте изменения.
- `shared_buffers > 8GB` — диминишинг ритёрн. Лучше отдать память OS page cache.
- Не пересчитывать `work_mem` после изменения `max_connections`. `work_mem = 256MB` + `max_connections = 500 = OOM`.
- Отключить autovacuum "чтобы не нагружал" — через месяц таблицы раздуты, индексы не работают. Autovacuum никогда не отключать.
- Менять несколько параметров одновременно и не знать, что именно сработало. Меняйте по одному.
- Не делать warmup перед pgbench — первый замер всегда медленнее, данные не в кэше.

---

## Чек-лист для самопроверки

- [ ] Умею рассчитать стартовые значения `shared_buffers`, `work_mem`, `maintenance_work_mem`, `effective_cache_size`
- [ ] Понимаю trade-off каждого параметра, не копирую вслепую
- [ ] Знаю, почему `shared_buffers > 8GB` неэффективно
- [ ] Понимаю, почему `work_mem × max_connections` может вызвать OOM
- [ ] Умею настроить autovacuum для высоконагруженной БД
- [ ] Знаю методологию pgbench: baseline -> одно изменение -> замер -> сравнение

---

## Попробуйте сами

1. Запустите pgbench на стандартной конфигурации PostgreSQL (`pgbench -i -s 50 testbench`, затем `pgbench -c 10 -j 4 -T 30`). Запишите TPS. Увеличьте `shared_buffers` в 2 раза (например, с 256MB до 512MB). Перезапустите PostgreSQL. Снова pgbench — изменился TPS? Почему? Сравните cache hit ratio до и после.

2. Создайте таблицу с 1 млн строк. Сделайте UPDATE всех строк 10 раз в цикле. Посмотрите `n_dead_tup` из `pg_stat_user_tables` — сколько dead tuples? Запустите `VACUUM`. Проверьте снова. Сколько dead tuples осталось?

3. Уменьшите `autovacuum_vacuum_scale_factor` до 0.01. Сгенерируйте UPDATE-нагрузку через pgbench (скрипт с UPDATE). Смотрите `last_autovacuum` в `pg_stat_user_tables` — запускается ли автовакуум чаще, чем до изменения?

4. Измените `work_mem` с 16MB на 64MB. Запустите pgbench с `-c 20`. Сравните TPS. Посмотрите `temp_files` в `pg_stat_database` — уменьшилось?
