# Глава 1: Запуск, конфигурация, важные файлы

**Цель главы:** ты запускаешь PostgreSQL, понимаешь, где живут данные и конфиги, и умеешь безопасно менять параметры.

---

## Что вы узнаете

- как запустить PostgreSQL в Docker и нативно на Ubuntu;
- структура PGDATA: что где лежит и зачем;
- ключевые параметры `postgresql.conf` со стартовыми значениями;
- как применять изменения конфигурации без перезапуска.

---

## Архитектура PostgreSQL: процессы и файлы

PostgreSQL — это не монолит. При каждом подключении порождается отдельный процесс. Это ключевое отличие от MySQL (где все соединения обслуживаются потоками одного процесса). Понимание этой схемы объясняет, почему 1000 соединений убивают PostgreSQL и почему нужен PgBouncer.

```
Клиент (psql / приложение)
        | TCP :5432
        v
  postmaster (главный процесс)
        | fork при каждом подключении
        v
  backend process (один на соединение)
        |
  +-----+--------------------------------------------------+
  |              Shared Memory                              |
  |  +----------------------+  +--------------------------+ |
  |  | Shared Buffers       |  |  WAL Buffers             | |
  |  | (кэш страниц)        |  |  (буфер журнала)         | |
  |  +----------------------+  +--------------------------+ |
  +---------------------------------------------------------+
        |                      |
        v                      v
  $PGDATA/base/          $PGDATA/pg_wal/
  (файлы таблиц)         (WAL-сегменты)
```

Каждый backend-process:

- занимает около 5-10 MB RAM (до первой операции — потом может расти);
- имеет выделенную память под `work_mem`, `hash_mem_multiplier`, `temp_buffers`;
- полностью изолирован от других backend-процессов.

Shared Memory — это область, которую разделяют все процессы PostgreSQL. Там лежит кэш страниц (`shared_buffers`) и буфер WAL (`wal_buffers`).

---

## Запуск в Docker

Самый быстрый способ поднять PostgreSQL для теста — Docker. Минимальная команда:

```bash
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_DB=myapp \
  -p 5432:5432 \
  postgres:16-alpine
```

Проверить, что работает:

```bash
docker exec -it postgres psql -U appuser -d myapp -c "SELECT version();"
```

Вывод:

```
                                                          version
---------------------------------------------------------------------------------------------------------------------------
 PostgreSQL 16.3 on x86_64-pc-linux-musl, compiled by gcc (Alpine 13.2.1_gcc20231014) 13.2.1, 64-bit
(1 row)
```

> Важно: контейнер без volume теряет все данные при удалении. Используй Docker Compose для персистентности.

---

## Docker Compose с персистентностью

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    restart: unless-stopped
    ports:
      - "127.0.0.1:5432:5432"   # только localhost, не наружу
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_USER: appuser
      POSTGRES_DB: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./init-scripts:/docker-entrypoint-initdb.d:ro
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    secrets:
      - postgres_password
    shm_size: '256mb'   # важно для сортировки и hash join
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d myapp"]
      interval: 10s
      retries: 5

volumes:
  pgdata:

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
```

Что здесь важно:

- `POSTGRES_PASSWORD_FILE` — пароль из файла, не в переменной окружения (чтобы не светился в `docker inspect`);
- `shm_size: '256mb'` — без этого `/dev/shm` будет 64 MB, а PostgreSQL использует shared memory для сортировок и hash-соединений;
- `restart: unless-stopped` — без этого при перезагрузке сервера PostgreSQL не поднимется сам;
- `command: postgres -c config_file=...` — использование собственного конфига, а не дефолтного из образа;
- `healthcheck` — чтобы оркестратор знал, что PostgreSQL готов принимать запросы;
- `init-scripts` — SQL-скрипты, которые выполняются при первом запуске (создание схем, пользователей).

---

## Нативная установка на Ubuntu 22.04

Если Docker не подходит или нужен PostgreSQL на bare-metal:

```bash
# Официальный репозиторий PostgreSQL (не apt из Ubuntu — там старые версии)
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh

sudo apt install -y postgresql-16
sudo systemctl enable --now postgresql
```

Проверить:

```bash
sudo -u postgres psql -c "SELECT version();"
sudo systemctl status postgresql
```

Вывод `systemctl status`:

```
● postgresql.service - PostgreSQL RDBMS
     Loaded: loaded (/lib/systemd/system/postgresql.service; enabled; vendor preset: enabled)
     Active: active (exited) since Thu 2026-06-04 10:00:00 UTC; 5min ago
```

Важно: `postgresql.service` — это wrapper, который запускает все кластеры. Конкретный кластер управляется через `systemctl postgresql@16-main`.

```bash
systemctl status postgresql@16-main
```

После установки PostgreSQL уже запущен и слушает на `localhost:5432`. Пользователь `postgres` создан автоматически — права ОС настраиваются через `peer`-аутентификацию (вход без пароля от пользователя `postgres`).

---

## Структура PGDATA

PGDATA — это корневая директория кластера PostgreSQL. В ней живут все данные, конфиги и журналы.

```
/var/lib/postgresql/16/main/    (дефолт на Ubuntu)
/var/lib/postgresql/data/       (дефолт в Docker)

$PGDATA/
  +-- base/                   <- данные каждой БД (по OID директории)
  |   +-- 1/                  <- template1
  |   +-- 16384/              <- ваша БД myapp (OID)
  |   +-- ...
  +-- global/                 <- глобальные объекты (роли, tablespaces)
  +-- pg_wal/                 <- WAL-сегменты (16MB файлы)
  +-- pg_hba.conf             <- правила аутентификации
  +-- postgresql.conf         <- основной конфиг
  +-- postgresql.auto.conf    <- переопределения через ALTER SYSTEM
  +-- PG_VERSION              <- версия PostgreSQL
  +-- postmaster.pid          <- PID главного процесса (если запущен)
```

> ☠️ **Осторожно:** не трогай файлы внутри `$PGDATA/base/` руками. Любое прямое изменение сломает БД. PostgreSQL сам управляет этими файлами через транзакции и WAL.

Чтобы узнать, где находится PGDATA в твоём PostgreSQL:

```bash
sudo -u postgres psql -c "SHOW data_directory;"
```

```
   data_directory
---------------------
 /var/lib/postgresql/16/main
(1 row)
```

Узнать OID своей базы:

```bash
sudo -u postgres psql -c "SELECT oid, datname FROM pg_database WHERE datname = 'myapp';"
```

```
  oid  | datname
-------+---------
 16384 | myapp
(1 row)
```

Директория `base/16384/` содержит файлы таблиц, индексов, последовательностей для БД `myapp`. Каждый файл — это relation (таблица или индекс), имя файла — это `relfilenode` из `pg_class`.

---

## Ключевые параметры postgresql.conf

Конфигурация PostgreSQL лежит в `$PGDATA/postgresql.conf`. Вот стартовые значения для типичного веб-приложения с комментариями — откуда берутся цифры и что будет, если поставить неверно.

```ini
# postgresql.conf — стартовые значения для типичного веб-приложения

# ============================================
# ПАМЯТЬ
# ============================================

shared_buffers = 256MB          # 25% RAM сервера (максимум 8GB)
                                # PostgreSQL кэш страниц в памяти
                                # > 8GB даёт diminishing returns:
                                # OS page cache эффективнее для больших объёмов

effective_cache_size = 1GB      # 75% RAM — подсказка планировщику
                                # Не выделяет память, только влияет на оценку
                                # стоимости Index Scan vs Seq Scan

work_mem = 16MB                 # RAM для каждой операции сортировки/hash
                                # Важно: умножить на max_connections × число
                                # одновременных сортировок
                                # work_mem × max_connections ≤ RAM
                                # Иначе: OOM при массовых сортировках

maintenance_work_mem = 256MB    # RAM для VACUUM, CREATE INDEX, ADD FOREIGN KEY
                                # Можно больше work_mem — обычно работает
                                # один VACUUM/INDEX одновременно

wal_buffers = 64MB              # Буфер WAL в shared memory
                                # 16MB по умолчанию — мало для write-heavy
                                # Увеличивать до 64MB при нагрузке на запись

# ============================================
# WAL И ПРОИЗВОДИТЕЛЬНОСТЬ ЗАПИСИ
# ============================================

wal_level = replica             # Нужно для репликации (по умолчанию)
                                # minimal — только для восстановления после сбоя
                                # replica — добавляет архивацию WAL
                                # logical — для logical replication

synchronous_commit = on         # Безопасно: подтверждение записи только после
                                # сброса WAL на диск
                                # off = быстрее, но риск потери ~200ms данных
                                # при сбое ОС/железа

checkpoint_completion_target = 0.9  # Размазать запись dirty buffers по 90%
                                    # интервала checkpoint
                                    # Меньше пиковая нагрузка на I/O
                                    # Но больше dirty buffers в памяти

# ============================================
# СОЕДИНЕНИЯ
# ============================================

max_connections = 100           # Для PgBouncer достаточно 20-50
                                # Без PgBouncer — по числу воркеров + запас
                                # Каждое соединение = ~5-10MB RAM

superuser_reserved_connections = 3  # Всегда зарезервировать для администратора
                                    # Даже при max_connections останется 3 слота

# ============================================
# ЛОГИРОВАНИЕ МЕДЛЕННЫХ ЗАПРОСОВ
# ============================================

log_min_duration_statement = 1000   # Логировать запросы дольше 1 секунды
                                    # 0 = логировать все запросы (только для
                                    # отладки — очень шумно)

log_line_prefix = '%t [%p] %u@%d ' # Время, PID, пользователь, БД
                                    # Пример: 2026-06-04 14:31:00 [1234] appuser@myapp

log_checkpoints = on                # Логировать checkpoint — увидишь если
                                    # checkpoint too frequent

log_connections = off               # Включать только для аудита — шумно
                                    # Каждое соединение пишет строку в лог

log_lock_waits = on                 # Логировать ожидания блокировок дольше
                                    # deadlock_timeout (1 сек по умолчанию)

# ============================================
# AUTOVACUUM
# ============================================

autovacuum = on                     # Никогда не выключать
                                    # Без autovacuum dead tuples накапливаются,
                                    # таблицы раздуваются, индексы деградируют

autovacuum_vacuum_scale_factor = 0.05  # Чаще чем 0.2 по умолчанию
                                       # Запускать VACUUM когда 5% строк стали dead

autovacuum_analyze_scale_factor = 0.02 # Обновлять статистику при 2% изменений

# ============================================
# ЛОКАЛИЗАЦИЯ (задаётся при initdb, менять нельзя без пересоздания)
# ============================================
# lc_messages = 'en_US.UTF-8'  # Сообщения об ошибках на английском — легче гуглить
```

---

## Применение изменений

Не все параметры в `postgresql.conf` требуют перезапуска. Параметры делятся на три группы:

```
1. Применяются без перезапуска (reload/sighup):
   - большинство параметров логирования
   - autovacuum и его подпараметры
   - max_connections (требует restart)
   - log_min_duration_statement
   - synchronous_commit

2. Требуют перезапуска (restart/postmaster):
   - shared_buffers
   - wal_level
   - max_connections
   - shared_preload_libraries
   - listen_addresses

3. Задаются только при initdb (нельзя изменить):
   - lc_collate, lc_ctype
   - encoding
   - data_checksums
```

### Reload (без перезапуска)

```bash
# Нативная установка
sudo systemctl reload postgresql

# Docker
docker exec postgres pg_ctl reload -D /var/lib/postgresql/data

# Через SQL (работает в обоих случаях)
SELECT pg_reload_conf();
```

### Узнать контекст параметра

```sql
SELECT name, context, setting
FROM pg_settings
WHERE name IN ('shared_buffers', 'log_min_duration_statement', 'max_connections');
```

Результат:

```
           name           |  context   | setting
--------------------------+------------+---------
 shared_buffers           | postmaster | 262144
 max_connections          | postmaster | 100
 log_min_duration_statement | sighup   | 1000
(3 rows)
```

- `context = postmaster` -> требует restart
- `context = sighup` -> достаточно reload (SIGHUP signal)
- `context = user` -> можно менять в текущей сессии через `SET`
- `context = superuser` -> только суперпользователь, `SET` или `ALTER SYSTEM`

### ALTER SYSTEM — изменение без редактирования файла

Вместо того чтобы редактировать `postgresql.conf` вручную, можно изменить параметр через SQL. Изменение записывается в `postgresql.auto.conf` — второй конфиг, который читается после основного и переопределяет его.

```sql
ALTER SYSTEM SET work_mem = '64MB';
-- Записано в $PGDATA/postgresql.auto.conf

SELECT pg_reload_conf();
-- Для sighup-параметров

SHOW work_mem;
```

```
 work_mem
----------
 64MB
(1 row)
```

Проверить, что записалось в файл:

```bash
cat $PGDATA/postgresql.auto.conf
```

```
# Do not edit this file manually!
# It will be overwritten by ALTER SYSTEM.
# 
# ALTER SYSTEM SET work_mem = '64MB';
work_mem = '64MB'
```

Сбросить изменение:

```sql
ALTER SYSTEM RESET work_mem;
SELECT pg_reload_conf();
SHOW work_mem;
```

```
 work_mem
----------
 16MB
(1 row)
```

> ☠️ **Осторожно:** не редактируй `postgresql.auto.conf` вручную. При ручном редактировании легко сделать синтаксическую ошибку, и PostgreSQL не стартует. Все изменения — только через `ALTER SYSTEM`.

### Разница между reload и restart

```
Reload (SIGHUP):
  - PostgreSQL перечитывает конфигурационные файлы
  - Существующие соединения продолжают работать
  - Новые соединения используют новые настройки
  - Без downtime

Restart:
  - Все соединения обрываются
  - PostgreSQL выключается и включается заново
  - Downtime: 10-60 секунд (зависит от размера shared buffers)
  - Необходим для параметров с context=postmaster
```

Как понять, нужен ли restart после `ALTER SYSTEM`:

```sql
SELECT name, context, pending_restart
FROM pg_settings
WHERE name = 'shared_buffers';
```

`pending_restart = t` означает, что параметр изменён, но изменению не применились — нужен перезапуск.

---

## Типичные ошибки

- **`shared_buffers` больше 40% RAM.** PostgreSQL начинает конкурировать с OS page cache за одни и те же страницы. Производительность падает, а не растёт. Максимум — 8GB. Если на сервере 64GB RAM, `shared_buffers = 8GB`, остальное отдаётся OS page cache.

- **`work_mem = 1GB` при 100 соединениях.** При массовых сортировках PostgreSQL может выделить `work_mem` на каждую операцию. 100 соединений × 1GB = 100GB потенциальной памяти. Считать: `work_mem × max_connections × одновременные сортировки ≤ RAM - shared_buffers`.

- **Редактировать `postgresql.auto.conf` вручную.** Синтаксическая ошибка в этой файле — PostgreSQL не стартует до её исправления. Используй `ALTER SYSTEM`.

- **Не указывать `restart: unless-stopped` в Docker Compose.** При перезагрузке сервера контейнер не поднимется автоматически. PostgreSQL будет недоступен до ручного запуска.

- **Путать `reload` и `restart`.** После изменения `shared_buffers` делать `pg_reload_conf()` бесполезно — параметр не применится. Нужно смотреть `context` в `pg_settings`.

---

## Чек-лист для самопроверки

- [ ] Запустил PostgreSQL в Docker, подключился через psql
- [ ] Понимаю, что в `$PGDATA/` и не трогаю `base/` руками
- [ ] Знаю разницу между `reload` и `restart` параметрами
- [ ] Настроил логирование медленных запросов

---

## Попробуйте сами

1. Запустите PostgreSQL в Docker. Выполните `docker exec postgres psql -U postgres -c "SHOW ALL;"` — сколько параметров? Найдите `shared_buffers` и `max_connections`.

2. Измените `log_min_duration_statement = 0` (логировать ВСЕ запросы). Примените через `pg_reload_conf()`. Выполните несколько запросов. Найдите их в логах: `docker logs postgres | grep duration`.

3. Выполните `ALTER SYSTEM SET work_mem = '64MB'`. Проверьте `cat $PGDATA/postgresql.auto.conf`. Примените `SELECT pg_reload_conf()`. Проверьте `SHOW work_mem`. Сбросьте через `ALTER SYSTEM RESET work_mem`.
