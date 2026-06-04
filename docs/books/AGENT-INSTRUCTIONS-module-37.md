# Инструкция для ИИ-агента: Модуль 37 — PostgreSQL для DevOps

> **Роль агента:** Ты — технический писатель и DevOps-инженер с опытом эксплуатации PostgreSQL в production. Ты не DBA — ты инженер который понимает БД ровно настолько, чтобы не создавать инциденты, уметь восстановиться после них и держать систему под контролем. Пишешь конкретно, с реальными командами и выводами, честно говоришь о trade-offs.

> **Это Модуль 37, книга части 4 "Прочее".**
> Предварительные требования: книга 03 (Docker), книга 35 (Сети), книга 36 (Vault).
> Читатель разворачивает приложения в Docker/K8s, но PostgreSQL для него — «чёрный ящик который просто должен работать».

---

## Контекст проекта

Читатель — DevOps-инженер у которого PostgreSQL «стоит на сервере и работает»:

- Бэкапы делаются «раз в неделю вручную» или не делаются вообще.
- Мониторинг: `SELECT 1` раз в минуту — и то хорошо.
- Пароль у базы один: `postgres` / `postgres`.
- При медленных запросах: «наверное нагрузка, подождём».
- 500 одновременных коннектов от приложения — «так работает».
- Миграция: `ALTER TABLE ... ADD COLUMN NOT NULL` в прод во время пика.
- Репликации нет, при падении primary — час простоя и 4 часа стресса.

**Чего он НЕ хочет после книги:**
Становиться DBA, писать хранимые процедуры, разбираться в MVCC на уровне исходников, оптимизировать запросы с subquery factoring.

**Что он хочет после книги:**
Поставить PostgreSQL так чтобы не было страшно. Делать бэкапы и уметь восстанавливаться. Смотреть мониторинг и понимать что видит. Настроить connection pooling. Делать миграции без даунтайма. Иметь read replica. Знать что делать когда что-то пошло не так.

---

## Что за книга

**Название:** "PostgreSQL для DevOps: надёжная эксплуатация без паники"

**Каталог:** `37-postgresql-devops`

**Место в курсе:** Книга 37, часть 4 "Прочее".

**Версии ПО:** PostgreSQL 16 (примеры работают на 15 и 16). Указывать когда команда появилась в конкретной версии.

**Объём:** 140–170 страниц.

**Формат файлов:** каждая глава — `chapter-XX.md`, приложения — `appendix-a.md`, `appendix-b.md`, `appendix-c.md`. Оглавление — `book.md`.

**Стиль:**
- Язык DevOps-инженера, не DBA. Не «реляционная алгебра», а «запрос завис — вот как найти».
- Каждая глава: «Что вы узнаете» → тело → «Типичные ошибки» → «Чек-лист» → «Попробуйте сами».
- Команды — с реальными выводами (обрезанными до сути).
- Mermaid-диаграммы для flows, ASCII для архитектур.
- Маркировка опасных операций: `> ☠️ **Осторожно:**`.
- Честно разделять: что делается в psql, что в bash, что в конфиг-файле.
- Всегда показывать полный путь к файлу конфигурации.

---

## Правило маркировки опасных операций

```markdown
> ☠️ **Осторожно:** [что именно удаляется/ломается и почему нельзя отменить]
```

Применять к:
- `DROP DATABASE` / `DROP TABLE` — необратимо без бэкапа
- `pg_restore --clean` — удаляет существующие объекты перед восстановлением
- `ALTER TABLE ... SET NOT NULL` без дефолта — блокирует таблицу
- `TRUNCATE` — удаляет все строки, нет WHERE
- `UPDATE / DELETE` без `WHERE` — типичная катастрофа
- изменение `max_connections` — требует перезапуска, может оборвать коннекты
- `pg_basebackup` на живой primary во время высокой нагрузки — нагружает WAL

---

## Антипаттерны подачи

**Плохо:** объяснять всё что умеет `EXPLAIN ANALYZE` на 4 страницах.
**Хорошо:** показать 3 конкретных паттерна в выводе EXPLAIN которые сигнализируют о проблеме.

**Плохо:** говорить «настройте PostgreSQL под вашу нагрузку».
**Хорошо:** давать конкретные стартовые значения для типичного веб-приложения с комментарием откуда они берутся.

**Плохо:** раздел «Теория MVCC» на 3 страницы.
**Хорошо:** одним абзацем объяснить почему dead tuples накапливаются и что делает VACUUM — ровно столько, чтобы понять `autovacuum`.

**Плохо:** показывать Patroni как «простой способ» HA.
**Хорошо:** честно сказать что Patroni — серьёзная система с learning curve, и для простых случаев достаточно streaming replication с ручным failover.

---

## Правило: визуализация — не опционально

- **Mermaid flowchart** — алгоритмы (backup strategy, failover procedure, migration steps).
- **ASCII-схемы** — архитектура (primary/replica, PgBouncer topology, WAL flow).
- **Таблицы** — сравнения (pg_dump vs pg_basebackup, synchronous vs asynchronous replication, connection modes в PgBouncer).
- **Схемы из секции «Обязательные схемы»** — минимум. Добавлять свои.

---

## Обязательные схемы

**Схема 1 — Архитектура PostgreSQL: процессы и файлы** (Глава 1):

```text
Клиент (psql / приложение)
        │ TCP :5432
        ▼
  postmaster (главный процесс)
        │ fork при каждом подключении
        ▼
  backend process (один на соединение)
        │
  ┌─────┴──────────────────────────────────────────┐
  │              Shared Memory                      │
  │  ┌──────────────┐  ┌──────────────────────────┐│
  │  │ Shared Buffers│  │  WAL Buffers             ││
  │  │ (кэш страниц) │  │  (буфер журнала)         ││
  │  └──────────────┘  └──────────────────────────┘│
  └─────────────────────────────────────────────────┘
        │                      │
        ▼                      ▼
  $PGDATA/base/         $PGDATA/pg_wal/
  (файлы таблиц)        (WAL-сегменты)
```
Разместить: начало главы 1.

**Схема 2 — Стратегия бэкапа** (Глава 4):

```text
Тип бэкапа        Что бэкапит          Скорость     Гранулярность
─────────────────────────────────────────────────────────────────
pg_dump           одна БД, логически   медленно     таблица, схема
pg_dumpall        все БД + роли        медленно     всё
pg_basebackup     весь кластер, файлы  быстро       весь кластер
WAL archiving     изменения (дельта)   непрерывно   точка во времени

Рекомендуемая комбинация:
─────────────────────────────────────────────────────────────────
pg_basebackup раз в сутки  +  WAL archiving  =  PITR (восстановление на любой момент)
pg_dump по отдельным БД    =  быстрое восстановление одной таблицы
```
Разместить: начало главы 4.

**Схема 3 — Connection Pooling с PgBouncer** (Глава 8):

```text
Без PgBouncer:
app (500 workers) → 500 PostgreSQL backends → 500 * ~10MB = 5GB RAM

С PgBouncer:
app (500 workers) → PgBouncer :5432 → 20 PostgreSQL backends → 20 * ~10MB = 200MB

Transaction mode:
worker А → соединение занято только во время транзакции → возврат в пул
worker Б → берёт то же соединение для следующей транзакции
```
Разместить: начало главы 8.

**Схема 4 — Streaming Replication** (Глава 9):

```text
Primary                              Replica(s)
─────────────────────────────────────────────────────
Пишем данные → WAL-файлы             WAL Receiver
                    │                    │
               WAL Sender ──────────────┘
               (отправляет                применяет WAL
                WAL в реальном            на свои данные
                времени)

Asynchronous (по умолчанию):
Primary подтвердил commit → реплика применит "когда-нибудь"
→ возможна потеря данных при падении primary (lag)

Synchronous:
Primary подтверждает commit только когда реплика записала WAL
→ нет потери данных, но латентность записи выше
```
Разместить: секция "Как работает репликация" в главе 9.

**Схема 5 — Expand/Contract миграция** (Глава 11):

```mermaid
flowchart LR
    A["Шаг 1: Expand\nДобавить новую колонку\n(nullable, без NOT NULL)"] --> B
    B["Шаг 2: Dual write\nПриложение пишет\nв обе колонки"] --> C
    C["Шаг 3: Backfill\nЗаполнить старые строки\nбез блокировки таблицы"] --> D
    D["Шаг 4: Migrate reads\nПриложение читает\nиз новой колонки"] --> E
    E["Шаг 5: Contract\nУдалить старую колонку\n(таблица небольшая)"]
```
Разместить: начало главы 11.

---

## Таблица объёмов глав

| Глава | Тема | Страниц |
|-------|------|---------|
| 0 | PostgreSQL для DevOps — роль инженера | 5–6 |
| 1 | Запуск, конфигурация, важные файлы | 10–12 |
| 2 | Пользователи, роли, права | 8–10 |
| 3 | pg_hba.conf, SSL, безопасное подключение | 7–9 |
| 4 | Бэкапы: pg_dump и pg_basebackup | 12–14 |
| 5 | WAL и PITR: восстановление на любой момент | 8–10 |
| 6 | Мониторинг: что смотреть и как | 10–12 |
| 7 | Медленные запросы: EXPLAIN, pg_stat_statements | 10–12 |
| 8 | Connection Pooling: PgBouncer | 10–12 |
| 9 | Репликация: streaming replication и read replicas | 10–12 |
| 10 | PostgreSQL в Docker и Kubernetes | 8–10 |
| 11 | Миграции без даунтайма: expand/contract | 8–10 |
| 12 | Диагностика: алгоритм разбора инцидентов | 7–8 |
| Приложения A–C | | 10–12 |

Общий объём: 140–170 страниц.

---

## Структура книги — детальное ТЗ по главам

---

### Глава 0: PostgreSQL для DevOps — не DBA, но и не игнорировать

**Что вы узнаете:**
- чем задачи DevOps отличаются от задач DBA в контексте PostgreSQL;
- что ломается в production и почему это можно было предотвратить;
- что читатель получит после книги и чего в ней нет.

**Цель:** задать правильные ожидания. Читатель понимает что DevOps не пишет хранимые процедуры, но обязан уметь делать бэкапы, мониторинг и безопасные миграции.

**Темы:**

Раздел "Три роли и PostgreSQL":
```text
DBA (Database Administrator):
  - проектирование схемы данных
  - оптимизация запросов
  - capacity planning
  - tuning PostgreSQL для специфической нагрузки

Разработчик:
  - пишет запросы и миграции
  - проектирует индексы
  - работает с ORM

DevOps-инженер:
  - деплой и обновление PostgreSQL
  - бэкапы и тестирование восстановления ← критично
  - мониторинг: доступность, нагрузка, медленные запросы
  - connection pooling
  - репликация и failover
  - безопасность: права, SSL, pg_hba.conf
  - миграции без даунтайма ← совместно с разработчиком
```

Раздел "Типичные инциденты которые можно было предотвратить":
Дать 5 реальных сценариев — коротко, без лишней драматизации:

```text
1. Диск заполнился WAL-файлами → PostgreSQL перестал принимать записи
   Профилактика: мониторинг места на диске, настройка wal_keep_size

2. 1000 соединений от приложения → OOM killer убил PostgreSQL
   Профилактика: PgBouncer с пулом из 20 соединений

3. ALTER TABLE ADD COLUMN NOT NULL без DEFAULT → таблица заблокирована на 40 минут
   Профилактика: expand/contract миграция (Глава 11)

4. Бэкапа не было 3 недели → восстановление невозможно
   Профилактика: ежедневный pg_basebackup + тест восстановления раз в месяц

5. UPDATE без WHERE случайно → обнулили поле у всех 2 млн пользователей
   Профилактика: PITR (Глава 5), begin/commit привычка, pgaudit
```

Раздел "Что в книге и что нет":
```text
В книге (DevOps-задачи):
✓ Деплой в Docker и K8s
✓ Бэкапы: pg_dump, pg_basebackup, WAL/PITR
✓ Мониторинг: ключевые метрики и запросы
✓ Медленные запросы: найти и понять EXPLAIN (не оптимизировать самому)
✓ PgBouncer: connection pooling
✓ Streaming replication: read replicas
✓ Миграции без даунтайма
✓ Диагностика инцидентов

Не в книге (зона DBA):
✗ Проектирование схемы данных
✗ Глубокая оптимизация запросов
✗ Partitioning и шардирование
✗ Параллельные запросы и планировщик
✗ Logical replication (упомянуть вскользь)
✗ Foreign Data Wrappers
```

**Типичные ошибки:**
- Думать что «PostgreSQL сам справится» — без минимального внимания справляется до первого инцидента.
- Отдать все задачи по БД разработчикам — у них нет прав и контекста для инфраструктурных задач.

**Чек-лист для самопроверки:**
- [ ] Понимаю чем DevOps-задачи по PostgreSQL отличаются от DBA
- [ ] Знаю 5 типичных инцидентов которые можно предотвратить
- [ ] Понимаю что в книге и что за её рамками

**Попробуйте сами:**
1. Посмотрите на свой текущий PostgreSQL: есть ли бэкапы? Настроен ли мониторинг? Есть ли connection pooling? Запишите — это ваш список задач после книги.
2. Спросите у разработчика: сколько соединений открывает приложение к БД? Сравните с `max_connections` в PostgreSQL. Что будет при пиковой нагрузке?
3. Найдите последний бэкап БД и проверьте: можно ли восстановиться из него прямо сейчас? На каком окружении? За сколько минут?

---

### Глава 1: Запуск, конфигурация, важные файлы

**Что вы узнаете:**
- как запустить PostgreSQL в Docker и нативно на Ubuntu;
- структура PGDATA: что где лежит и зачем;
- ключевые параметры `postgresql.conf`;
- как применять изменения конфигурации без перезапуска.

**Цель:** читатель запускает PostgreSQL, понимает где живут данные и конфиги, и умеет безопасно менять параметры.

**Темы:**

Разместить Схему 1 (процессы и файлы) в начале главы.

Раздел "Запуск в Docker":
```bash
# Минимальный запуск (данные теряются при удалении контейнера)
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_DB=myapp \
  -p 5432:5432 \
  postgres:16-alpine

# Проверить
docker exec -it postgres psql -U appuser -d myapp -c "SELECT version();"
```

Раздел "Docker Compose с персистентностью":
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

Раздел "Нативная установка на Ubuntu 22.04":
```bash
# Официальный репозиторий PostgreSQL (не apt из Ubuntu — там старые версии)
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh

sudo apt install -y postgresql-16
sudo systemctl enable --now postgresql

# Проверить
sudo -u postgres psql -c "SELECT version();"
sudo systemctl status postgresql
```

Раздел "Структура PGDATA":
```text
/var/lib/postgresql/16/main/    (дефолт на Ubuntu)
/var/lib/postgresql/data/       (дефолт в Docker)

$PGDATA/
├── base/                   ← данные каждой БД (по OID директории)
│   ├── 1/                  ← template1
│   ├── 16384/              ← ваша БД myapp (OID)
│   └── ...
├── global/                 ← глобальные объекты (роли, tablespaces)
├── pg_wal/                 ← WAL-сегменты (16MB файлы)
├── pg_hba.conf             ← правила аутентификации
├── postgresql.conf         ← основной конфиг
├── postgresql.auto.conf    ← переопределения через ALTER SYSTEM
├── PG_VERSION              ← версия PostgreSQL
└── postmaster.pid          ← PID главного процесса (если запущен)
```

> ☠️ **Осторожно:** не трогай файлы внутри `$PGDATA/base/` руками. Любое изменение сломает БД.

Раздел "Ключевые параметры postgresql.conf":
Давать конкретные рекомендации, не «зависит от нагрузки». Объяснить логику каждого:

```ini
# postgresql.conf — стартовые значения для типичного веб-приложения

# Память
shared_buffers = 256MB          # 25% RAM сервера (не больше)
effective_cache_size = 1GB      # 75% RAM — подсказка планировщику
work_mem = 16MB                 # RAM для каждой сортировки/hash; умножить на max_connections

# WAL и производительность записи
wal_level = replica             # нужно для репликации (по умолчанию)
synchronous_commit = on         # безопасно; off = быстрее но риск потери ~200ms данных
checkpoint_completion_target = 0.9  # размазать checkpoint по 90% интервала

# Соединения
max_connections = 100           # для PgBouncer достаточно; без него — по числу воркеров + запас
superuser_reserved_connections = 3  # всегда зарезервировать для DBA

# Логирование медленных запросов
log_min_duration_statement = 1000  # логировать запросы дольше 1 секунды
log_line_prefix = '%t [%p] %u@%d '
log_checkpoints = on
log_connections = off           # включать только для аудита, шумно
log_lock_waits = on             # логировать ожидания блокировок > deadlock_timeout

# Autovacuum
autovacuum = on                 # никогда не выключать
autovacuum_vacuum_scale_factor = 0.05  # чаще чем 0.2 по умолчанию
autovacuum_analyze_scale_factor = 0.02

# Локализация (задаётся при initdb, менять нельзя без пересоздания кластера)
# lc_messages = 'en_US.UTF-8'  # сообщения об ошибках на английском — легче гуглить
```

Раздел "Применение изменений":
```bash
# Параметры делятся на три группы:
# 1. Применяются без перезапуска (reload)
# 2. Требуют перезапуска (restart)
# 3. Задаются только при initdb (нельзя изменить)

# Применить reload-параметры (большинство настроек логирования, autovacuum)
sudo systemctl reload postgresql   # нативно
# или
docker exec postgres pg_ctl reload -D /var/lib/postgresql/data

# Узнать контекст параметра
sudo -u postgres psql -c "SELECT name, context FROM pg_settings WHERE name = 'shared_buffers';"
# context = postmaster → требует restart
# context = sighup → reload достаточно
# context = user → можно менять в сессии через SET

# Изменить параметр через SQL (записывается в postgresql.auto.conf)
ALTER SYSTEM SET shared_buffers = '512MB';
SELECT pg_reload_conf();   -- для sighup-параметров
-- или перезапуск для postmaster-параметров

# Сбросить ALTER SYSTEM изменение
ALTER SYSTEM RESET shared_buffers;
```

**Типичные ошибки:**
- `shared_buffers` больше 40% RAM — PostgreSQL будет конкурировать с OS page cache, деградация производительности.
- `work_mem` = 1GB при 100 соединениях = потенциально 100GB RAM на сортировки. Считать: N_connections × work_mem ≤ (RAM - shared_buffers).
- Редактировать `postgresql.auto.conf` вручную — только через `ALTER SYSTEM`. При ручном редактировании легко сделать синтаксическую ошибку и PostgreSQL не стартует.
- Не указывать `restart: unless-stopped` в Docker Compose — при перезагрузке сервера PostgreSQL не поднимется сам.

**Чек-лист для самопроверки:**
- [ ] Запустил PostgreSQL в Docker, подключился через psql
- [ ] Понимаю что в `$PGDATA/` и не трогаю `base/` руками
- [ ] Знаю разница между `reload` и `restart` параметрами
- [ ] Настроил логирование медленных запросов

**Попробуйте сами:**
1. Запустите PostgreSQL в Docker. Выполните `docker exec postgres psql -U postgres -c "SHOW ALL;"` — сколько параметров? Найдите `shared_buffers` и `max_connections`.
2. Измените `log_min_duration_statement = 0` (логировать ВСЕ запросы). Примените через `pg_reload_conf()`. Выполните несколько запросов. Найдите их в логах: `docker logs postgres | grep duration`.
3. Выполните `ALTER SYSTEM SET work_mem = '64MB'`. Проверьте `cat $PGDATA/postgresql.auto.conf`. Примените `SELECT pg_reload_conf()`. Проверьте `SHOW work_mem`.

---

### Глава 2: Пользователи, роли и права

**Что вы узнаете:**
- как устроена система прав в PostgreSQL: роли, привилегии, схемы;
- принцип наименьших привилегий для приложений;
- как создать пользователя с минимальными правами;
- что такое `GRANT` и `REVOKE`.

**Цель:** каждый сервис подключается к PostgreSQL со своим пользователем у которого есть только необходимые права. Пользователь `postgres` — только для администрирования.

**Темы:**

Раздел "Роль = пользователь в PostgreSQL":
Объяснить что в PostgreSQL роль и пользователь — одно и то же. `CREATE USER` = `CREATE ROLE ... WITH LOGIN`. Роль без LOGIN — группа прав.

```sql
-- Просмотр всех ролей
\du

-- Или через системную таблицу
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin
FROM pg_roles
ORDER BY rolname;
```

Раздел "Создание пользователей для приложения":
```sql
-- Создать пользователя без прав суперпользователя
CREATE USER appuser WITH PASSWORD 'StrongPassword123';

-- Создать БД
CREATE DATABASE myapp OWNER appuser;

-- Подключиться к БД и выдать права
\c myapp

-- Дать права на схему
GRANT USAGE ON SCHEMA public TO appuser;

-- Дать права на существующие таблицы
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO appuser;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO appuser;

-- Дать права на будущие таблицы (важно!)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO appuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO appuser;
```

Раздел "Read-only пользователь для аналитики/мониторинга":
```sql
CREATE USER readonly WITH PASSWORD 'ReadOnlyPass123';

\c myapp
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO readonly;
```

Раздел "Разделение прав по схемам":
Объяснить pattern: несколько сервисов в одной БД изолируются через схемы.
```sql
-- Схемы как namespace для разных сервисов
CREATE SCHEMA service_a;
CREATE SCHEMA service_b;

CREATE USER service_a_user WITH PASSWORD '...';
CREATE USER service_b_user WITH PASSWORD '...';

-- service_a_user видит только свою схему
GRANT USAGE ON SCHEMA service_a TO service_a_user;
GRANT ALL ON ALL TABLES IN SCHEMA service_a TO service_a_user;

-- Установить search_path для пользователя
ALTER USER service_a_user SET search_path = service_a, public;
```

Раздел "Смена пароля и ротация":
```sql
-- Сменить пароль
ALTER USER appuser WITH PASSWORD 'NewPassword456';

-- Посмотреть когда истекает пароль
SELECT rolname, rolvaliduntil FROM pg_roles WHERE rolname = 'appuser';

-- Пароль с временем истечения
ALTER USER appuser WITH PASSWORD 'TempPass' VALID UNTIL '2026-12-31';
```

Интеграция с Vault: упомянуть что Vault Database Engine (книга 36) создаёт временных пользователей автоматически — это лучшая практика для production.

**Типичные ошибки:**
- Использовать суперпользователя `postgres` для подключения из приложения. При SQL-инъекции — полный доступ к серверу.
- `GRANT ALL ON DATABASE` ≠ доступ к таблицам. `GRANT ON DATABASE` даёт право подключиться, но не читать таблицы.
- Не выдать `ALTER DEFAULT PRIVILEGES` — после миграций новые таблицы будут без прав у appuser.
- Хранить пароль в строке подключения в коде: `postgresql://appuser:password@host/db` — попадает в логи и APM.

**Чек-лист для самопроверки:**
- [ ] Понимаю что в PostgreSQL роль = пользователь
- [ ] Умею создать пользователя с минимальными правами для приложения
- [ ] Знаю зачем нужен `ALTER DEFAULT PRIVILEGES`
- [ ] Умею создать read-only пользователя для мониторинга/аналитики

**Попробуйте сами:**
1. Создайте пользователя `appuser` без суперправ. Создайте таблицу от имени `postgres`. Попробуйте SELECT от `appuser` — ошибка. Выдайте `GRANT SELECT`. Попробуйте снова. Создайте вторую таблицу — `appuser` снова без прав. Теперь добавьте `ALTER DEFAULT PRIVILEGES`.
2. Подключитесь от имени `appuser` и попробуйте `CREATE DATABASE` — должно быть `permission denied`. Попробуйте `DROP TABLE` чужой таблицы. Убедитесь что изоляция работает.
3. Создайте read-only пользователя. Подключитесь от его имени. Попробуйте `INSERT` — ошибка. `SELECT` — работает. Это мониторинговый пользователь.

---

### Глава 3: pg_hba.conf, SSL и безопасное подключение

**Что вы узнаете:**
- как работает pg_hba.conf: порядок правил, типы соединений, методы аутентификации;
- как настроить SSL для шифрования соединений;
- как ограничить доступ к PostgreSQL по IP и методу;
- типичные ошибки подключения и их диагностика.

**Цель:** PostgreSQL принимает соединения только от доверенных клиентов, пароли не передаются в открытом виде.

**Темы:**

Раздел "Как работает pg_hba.conf":
Объяснить что PostgreSQL проверяет правила сверху вниз и применяет первое совпавшее. Формат строки: `тип database user address метод`.

```text
# TYPE  DATABASE  USER      ADDRESS         METHOD

# Локальные Unix-сокет соединения
local   all       postgres                  peer    ← OS user = PG user
local   all       all                       scram-sha-256

# IPv4
host    myapp     appuser   192.168.1.0/24  scram-sha-256
host    all       all       127.0.0.1/32    scram-sha-256

# IPv6
host    all       all       ::1/128         scram-sha-256

# Запретить всё остальное (явный запрет, хорошая практика)
host    all       all       all             reject
```

Разобрать типы (`local`, `host`, `hostssl`, `hostnossl`) и методы (`peer`, `md5`, `scram-sha-256`, `trust`, `reject`).

Объяснить: `scram-sha-256` — современный стандарт (PostgreSQL 10+). `md5` — устарел. `trust` — никогда не использовать в production.

Раздел "Перезагрузить после изменений":
```bash
sudo systemctl reload postgresql   # не restart!
# или
SELECT pg_reload_conf();

# Проверить текущие правила HBA
TABLE pg_hba_file_rules;
```

Раздел "SSL":
```bash
# PostgreSQL 14+ включает SSL по умолчанию при наличии сертификатов
ls $PGDATA/server.{crt,key}

# Создать self-signed сертификат для тестирования
openssl req -new -x509 -days 365 -nodes \
  -out $PGDATA/server.crt \
  -keyout $PGDATA/server.key \
  -subj "/CN=mypostgres"

chmod 600 $PGDATA/server.key
chown postgres: $PGDATA/server.{crt,key}
```

```ini
# postgresql.conf
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
# ssl_ca_file = 'root.crt'   # если нужна клиентская аутентификация
```

```text
# pg_hba.conf — принудительно SSL
hostssl  myapp   appuser   0.0.0.0/0   scram-sha-256
hostnossl all    all       all         reject   ← без SSL — запрещено
```

```bash
# Проверить SSL при подключении
psql "host=myserver dbname=myapp user=appuser sslmode=require"
# или
psql "postgresql://appuser@myserver/myapp?sslmode=verify-full&sslrootcert=root.crt"
```

Раздел "Диагностика ошибок подключения":
```text
Ошибка: "pg_hba.conf entry not found for host X, user Y, database Z"
→ Нет совпадающего правила в pg_hba.conf
→ Добавить правило или проверить порядок

Ошибка: "password authentication failed"
→ Неверный пароль или метод аутентификации
→ Проверить метод в pg_hba.conf (md5 vs scram-sha-256 vs trust)

Ошибка: "role 'username' does not exist"
→ Пользователь не создан в PostgreSQL
→ CREATE USER ...

Ошибка: "SSL connection is required"
→ pg_hba.conf требует SSL, клиент подключается без него
→ Добавить sslmode=require в строку подключения

Ошибка: "connection refused: connect to port 5432"
→ PostgreSQL не слушает на этом IP
→ Проверить listen_addresses в postgresql.conf
```

Параметр `listen_addresses`:
```ini
# postgresql.conf
listen_addresses = 'localhost'   # только localhost (дефолт)
listen_addresses = '*'           # все интерфейсы (нужно + pg_hba.conf с ограничениями)
listen_addresses = '192.168.1.10,127.0.0.1'  # конкретные IP
```

**Типичные ошибки:**
- `trust` для любого пользователя — любой кто достучался до порта 5432 может войти без пароля.
- Правило `host all all 0.0.0.0/0 scram-sha-256` открывает PostgreSQL всему интернету (если `listen_addresses = '*'`). Ограничивать по IP или закрыть порт файрволом.
- Порядок правил: более специфичные правила должны быть выше более общих.

**Чек-лист для самопроверки:**
- [ ] Понимаю формат строк pg_hba.conf и порядок применения правил
- [ ] Знаю разницу между `md5`, `scram-sha-256` и `trust`
- [ ] Умею включить SSL и требовать его через pg_hba.conf
- [ ] Умею диагностировать типичные ошибки подключения

**Попробуйте сами:**
1. Добавьте в pg_hba.conf правило `host myapp appuser 192.168.100.0/24 scram-sha-256`. Попробуйте подключиться с адреса не из этой подсети — должен быть отказ. Убедитесь что с нужного IP работает.
2. Настройте SSL на тестовом PostgreSQL. Подключитесь с `sslmode=require` — работает. С `sslmode=disable` — должен быть отказ (если настроен `hostnossl reject`).
3. Намеренно введите неверный пароль — запишите ошибку. Подключитесь с несуществующим пользователем — другая ошибка. Попробуйте подключиться к несуществующей БД — ещё одна. Умейте различать эти три случая.

---

### Глава 4: Бэкапы — pg_dump и pg_basebackup

**Что вы узнаете:**
- три инструмента бэкапа и когда что использовать;
- `pg_dump`: логический бэкап одной БД;
- `pg_basebackup`: физический бэкап всего кластера;
- как тестировать восстановление (самое важное).

**Цель:** читатель настраивает ежедневный бэкап и умеет восстановиться из него за 30 минут.

**Темы:**

Разместить Схему 2 (стратегия бэкапа) в начале главы.

Раздел "pg_dump — логический бэкап":
```bash
# Дамп одной БД в custom-формат (рекомендуется для pg_restore)
pg_dump -U postgres -d myapp -F c -f /backup/myapp_$(date +%Y%m%d_%H%M).dump

# Ключи:
# -F c = custom format (бинарный, сжатый, позволяет селективное восстановление)
# -F p = plain SQL (читаемый, большой, нельзя --list)
# -F d = directory format (параллельный дамп)
# -j 4 = параллельный дамп 4 потока (только для directory format)

# Дамп конкретной таблицы
pg_dump -U postgres -d myapp -t users -F c -f /backup/users.dump

# Дамп схемы без данных
pg_dump -U postgres -d myapp -s -F p -f /backup/schema_only.sql

# Дамп данных без схемы
pg_dump -U postgres -d myapp -a -F c -f /backup/data_only.dump

# Дамп всех БД + роли + tablespaces
pg_dumpall -U postgres -f /backup/full_cluster.sql
```

Раздел "pg_restore — восстановление":
```bash
# Восстановить в новую (уже созданную) БД
createdb -U postgres myapp_restored
pg_restore -U postgres -d myapp_restored /backup/myapp_20260601.dump

# Параллельное восстановление (быстрее на большой БД)
pg_restore -U postgres -d myapp_restored -j 4 /backup/myapp_20260601.dump

# Восстановить только одну таблицу
pg_restore -U postgres -d myapp_restored -t users /backup/myapp_20260601.dump

# Посмотреть что в дампе (без восстановления)
pg_restore -l /backup/myapp_20260601.dump

# Восстановить поверх существующей БД (drop + create objects)
pg_restore -U postgres -d myapp --clean --if-exists /backup/myapp_20260601.dump
```

> ☠️ **Осторожно:** `pg_restore --clean` удаляет существующие таблицы перед восстановлением. Использовать только если точно понимаешь последствия.

Раздел "pg_basebackup — физический бэкап кластера":
```bash
# Полный бэкап кластера (работает на живом сервере)
pg_basebackup -U replicator -h localhost \
  -D /backup/basebackup_$(date +%Y%m%d) \
  -P -Xs -R -z

# Ключи:
# -P = progress bar
# -Xs = включить WAL в бэкап (stream mode)
# -R = создать standby.signal + postgresql.auto.conf для репликации
# -z = gzip-сжатие

# Требования: пользователь replicator с правом REPLICATION
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'ReplPass';
# pg_hba.conf: host replication replicator 127.0.0.1/32 scram-sha-256
```

Раздел "Тест восстановления — обязательно!":
```text
Бэкап без теста восстановления — не бэкап.

Алгоритм тестирования (раз в месяц):
1. Создать тестовый PostgreSQL (Docker Compose)
2. Загрузить туда последний бэкап
3. Проверить что данные читаются:
   SELECT count(*) FROM users;
   SELECT max(created_at) FROM orders;
4. Проверить что схема корректна
5. Замерить время восстановления
6. Записать результат (дата, время восстановления, версия бэкапа)
```

```bash
# Автоматический тест pg_dump
docker run --rm \
  -v /backup:/backup \
  postgres:16-alpine \
  sh -c "
    createdb -U postgres test_restore && \
    pg_restore -U postgres -d test_restore /backup/myapp_latest.dump && \
    psql -U postgres -d test_restore -c 'SELECT count(*) FROM users;' && \
    echo 'RESTORE TEST: OK'
  "
```

Раздел "Автоматизация бэкапов":
```bash
#!/bin/bash
# /opt/backup/backup_postgres.sh

BACKUP_DIR="/backup/postgres"
PGUSER="postgres"
PGHOST="localhost"
RETENTION_DAYS=14
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Дамп каждой БД
for DB in $(psql -U "$PGUSER" -h "$PGHOST" -At -c "SELECT datname FROM pg_database WHERE datistemplate = false;"); do
    pg_dump -U "$PGUSER" -h "$PGHOST" -d "$DB" -F c \
        -f "$BACKUP_DIR/${DB}_${DATE}.dump"
    echo "$(date): Dumped $DB"
done

# Удалить старые бэкапы
find "$BACKUP_DIR" -name "*.dump" -mtime +$RETENTION_DAYS -delete

# Cron: каждый день в 2:00
# 0 2 * * * /opt/backup/backup_postgres.sh >> /var/log/pg_backup.log 2>&1
```

**Типичные ошибки:**
- `pg_dump` блокирует таблицы на `ACCESS SHARE` — не влияет на чтение, но блокирует `DROP TABLE`. В general — безопасно.
- Бэкап на том же диске что и данные — сломался диск, потерял и данные и бэкап. Копировать на удалённый сервер/S3.
- `pg_dump` не бэкапит роли (пользователей). Для полного восстановления нужен `pg_dumpall -g` (только глобальные объекты).
- Никогда не тестировать восстановление — узнаешь о проблеме только во время реального инцидента.

**Чек-лист для самопроверки:**
- [ ] Умею сделать `pg_dump` в custom-формате и восстановить из него
- [ ] Понимаю разницу между `pg_dump` и `pg_basebackup`
- [ ] Настроил автоматический ежедневный бэкап через cron
- [ ] Провёл тест восстановления и знаю сколько времени это занимает

**Попробуйте сами:**
1. Сделайте `pg_dump` в custom-формат. Посмотрите что внутри через `pg_restore -l`. Восстановите только одну таблицу (не всю БД) — убедитесь что выборочное восстановление работает.
2. Создайте БД с тестовыми данными. Сделайте дамп. Дропните таблицу. Восстановите таблицу из дампа. Данные вернулись?
3. Настройте cron для ежедневного бэкапа. Проверьте через `crontab -l` что задание добавлено. Запустите скрипт вручную и убедитесь что файлы создаются в нужном месте.

---

### Глава 5: WAL и PITR — восстановление на любой момент времени

**Что вы узнаете:**
- что такое WAL и зачем он нужен;
- как настроить непрерывную архивацию WAL;
- PITR: восстановление на точный момент времени;
- когда PITR нужен и как его тестировать.

**Цель:** читатель понимает что WAL-архивирование + ежедневный pg_basebackup даёт восстановление на любую минуту последних N дней с потерей максимум нескольких секунд данных.

**Темы:**

Раздел "Что такое WAL":
Объяснить без глубокой теории: WAL (Write-Ahead Log) — журнал всех изменений. Перед изменением данных PostgreSQL записывает изменение в WAL. При сбое PostgreSQL восстанавливается применяя WAL к последнему checkpoint. WAL хранится в `$PGDATA/pg_wal/` сегментами по 16MB.

```text
Без WAL: данные изменились → сбой → неизвестно в каком состоянии файлы
С WAL:  WAL записан → данные изменились → сбой → применить WAL = консистентность
```

Раздел "WAL archiving":
```ini
# postgresql.conf
wal_level = replica           # нужен для архивации (и репликации)
archive_mode = on
archive_command = 'cp %p /archive/wal/%f'
# %p = полный путь к WAL-файлу
# %f = имя файла

# Для S3 (через aws cli или WAL-G):
# archive_command = 'aws s3 cp %p s3://my-bucket/wal/%f'
# archive_command = 'wal-g wal-push %p'
```

Раздел "WAL-G — промышленный инструмент для бэкапов":
```bash
# WAL-G — стандарт индустрии для PostgreSQL backup
# Поддерживает S3, GCS, Azure, filesystem
# Сжатие, дедупликация, delta backup

# Установка
curl -L https://github.com/wal-g/wal-g/releases/latest/download/wal-g-pg-ubuntu-20.04-amd64 \
  -o /usr/local/bin/wal-g && chmod +x /usr/local/bin/wal-g

# ~/.walg.json (конфиг)
{
  "WALG_FILE_PREFIX": "/backup/walg",
  "PGDATABASE": "postgres"
}

# postgresql.conf
archive_command = 'wal-g wal-push %p'
restore_command = 'wal-g wal-fetch %f %p'

# Сделать базовый бэкап
wal-g backup-push $PGDATA

# Список бэкапов
wal-g backup-list

# Восстановить последний
wal-g backup-fetch $PGDATA LATEST
```

Раздел "PITR: восстановление на момент времени":
```bash
# Сценарий: в 14:32 кто-то выполнил DELETE FROM orders WHERE 1=1
# Нужно восстановиться на 14:31

# 1. Остановить PostgreSQL
systemctl stop postgresql

# 2. Очистить текущие данные (или использовать новую директорию)
rm -rf $PGDATA/*

# 3. Восстановить базовый бэкап
pg_basebackup -D $PGDATA ... # или: wal-g backup-fetch $PGDATA LATEST

# 4. Создать recovery.conf (PostgreSQL < 12) или postgresql.auto.conf
# PostgreSQL 12+: создать файл recovery.signal + параметры в postgresql.conf
touch $PGDATA/recovery.signal

cat >> $PGDATA/postgresql.auto.conf << 'EOF'
restore_command = 'cp /archive/wal/%f %p'
recovery_target_time = '2026-06-04 14:31:00'
recovery_target_action = 'promote'   # после достижения цели — стать primary
EOF

# 5. Запустить PostgreSQL — он применит WAL до указанного момента
systemctl start postgresql

# 6. Мониторить восстановление
tail -f /var/log/postgresql/postgresql.log
# Увидишь: "recovery stopping before commit of transaction..."
# Потом: "database system is ready to accept connections"
```

**Типичные ошибки:**
- `archive_command` написан но `wal_level != replica` — WAL архивируется неполно.
- Архив на том же сервере что и данные — при сбое сервера теряется и то и другое.
- Не тестировать PITR — единственный способ убедиться что восстановление работает.
- `recovery_target_time` в неверном часовом поясе — восстановление на неверный момент.

**Чек-лист для самопроверки:**
- [ ] Понимаю что WAL — это журнал изменений, не копия данных
- [ ] Умею настроить `archive_command` для локального архива
- [ ] Понимаю процедуру PITR на высоком уровне (6 шагов)
- [ ] Знаю что WAL-G — промышленный стандарт для бэкапов

**Попробуйте сами:**
1. Настройте `archive_mode = on` и `archive_command = 'cp %p /tmp/wal_archive/%f'`. Создайте директорию. Сделайте несколько изменений в БД. Проверьте что в `/tmp/wal_archive/` появились файлы. Это и есть WAL-архивация.
2. (Продвинутое) Выполните полный PITR-тест: база данных → добавьте строки → запомните время → удалите строки → восстановите на момент до удаления. Строки вернулись?
3. Изучите `wal-g backup-list` если настроили WAL-G. Посмотрите размер бэкапов. Сколько места занимают WAL-файлы за сутки на вашей нагрузке?

---

### Глава 6: Мониторинг — что смотреть и как

**Что вы узнаете:**
- ключевые системные представления (`pg_stat_*`);
- метрики для Prometheus через `postgres_exporter`;
- что должно быть на дашборде: минимальный набор метрик;
- как найти активные запросы и заблокированные сессии.

**Цель:** читатель видит дашборд PostgreSQL и понимает каждую метрику. Знает как найти «кто завис» через psql.

**Темы:**

Раздел "Ключевые системные представления":

```sql
-- Активные соединения и их статус
SELECT pid, usename, application_name, client_addr,
       state, wait_event_type, wait_event,
       now() - state_change AS duration,
       left(query, 80) AS query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Сводка по состояниям соединений
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
-- idle: 45, active: 3, idle in transaction: 2

-- Заблокированные запросы (ждут lock)
SELECT pid, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE wait_event_type = 'Lock';

-- Что блокирует что (иерархия блокировок)
SELECT blocked.pid AS blocked_pid,
       blocked.query AS blocked_query,
       blocking.pid AS blocking_pid,
       blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE cardinality(pg_blocking_pids(blocked.pid)) > 0;
```

```sql
-- Размеры БД
SELECT datname,
       pg_size_pretty(pg_database_size(datname)) AS size
FROM pg_database
ORDER BY pg_database_size(datname) DESC;

-- Размеры таблиц
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total,
       pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_only,
       pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;

-- Статистика таблиц (vacuum, analyze)
SELECT schemaname, relname,
       n_live_tup, n_dead_tup,
       last_vacuum, last_autovacuum,
       last_analyze, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 10;
```

Раздел "postgres_exporter для Prometheus":
```yaml
# docker-compose.yml
services:
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    environment:
      DATA_SOURCE_NAME: "postgresql://monitoring:MonitorPass@postgres:5432/postgres?sslmode=disable"
    ports:
      - "9187:9187"
```

```sql
-- Пользователь для мониторинга (минимальные права)
CREATE USER monitoring WITH PASSWORD 'MonitorPass';
GRANT pg_monitor TO monitoring;   -- PostgreSQL 10+: роль pg_monitor
```

Раздел "Ключевые метрики для дашборда":
Давать конкретные пороги, не «зависит от нагрузки»:

```text
Метрика                          Норма              Тревога
───────────────────────────────────────────────────────────────────
pg_up                            1                  0 = PostgreSQL недоступен
Активные соединения              < 80% max_conn     > 90% max_conn
Idle in transaction              < 5               > 20 (утечка транзакций)
DB size growth (день)            < 5%               > 20% за день
Replication lag (секунды)        < 10s              > 60s
Checkpoint frequency             < 1/min            > 5/min (нагрузка WAL)
Dead tuples (доля)               < 20%              > 50% (нужен VACUUM)
Cache hit ratio                  > 95%              < 90% (мало shared_buffers)
TPS (транзакции/сек)             baseline ± 20%     -50% от baseline
```

```promql
# Cache hit ratio — должен быть > 95%
rate(pg_stat_bgwriter_buffers_alloc_total[5m]) /
(rate(pg_stat_bgwriter_buffers_alloc_total[5m]) + rate(pg_stat_bgwriter_buffers_clean_total[5m]))

# Доля dead tuples по таблице
pg_stat_user_tables_n_dead_tup / (pg_stat_user_tables_n_live_tup + 1)
```

Раздел "Убить зависший запрос":
```sql
-- Послать SIGTERM (запрос завершится после текущей операции)
SELECT pg_cancel_backend(pid);

-- Послать SIGKILL (немедленно)
SELECT pg_terminate_backend(pid);

-- Найти и убить все запросы дольше 5 минут
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state != 'idle'
  AND now() - query_start > interval '5 minutes'
  AND pid != pg_backend_pid();
```

**Типичные ошибки:**
- Не мониторить `idle in transaction` — это открытые транзакции которые держат блокировки. При накоплении — весь сервер встаёт.
- Cache hit ratio < 90% — первый признак что `shared_buffers` мал. Не индексы, не запросы — память.
- Мониторить только `pg_up` (лишь бы работал) — узнаешь о деградации производительности только от пользователей.

**Чек-лист для самопроверки:**
- [ ] Умею найти активные запросы и зависшие транзакции через `pg_stat_activity`
- [ ] Умею найти что блокирует что через `pg_blocking_pids`
- [ ] Настроил `postgres_exporter` и вижу метрики в Prometheus
- [ ] Знаю 5 ключевых метрик и их пороги

**Попробуйте сами:**
1. Откройте транзакцию (`BEGIN;`) и не закрывайте её. В другом соединении запустите `SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction'`. Нашли?
2. Создайте ситуацию блокировки: в одном соединении `BEGIN; UPDATE users SET name='test' WHERE id=1;` (не коммитить). В другом: `UPDATE users SET name='other' WHERE id=1;` — завис. Найдите блокировку через `pg_blocking_pids`. Убейте блокирующий запрос через `pg_terminate_backend`.
3. Настройте `postgres_exporter` в Docker Compose. Откройте `http://localhost:9187/metrics` — найдите `pg_stat_activity_count` и `pg_database_size_bytes`.

---

### Глава 7: Медленные запросы — pg_stat_statements и EXPLAIN

**Что вы узнаете:**
- как найти самые медленные запросы через `pg_stat_statements`;
- как читать вывод `EXPLAIN ANALYZE` — ключевые сигналы проблемы;
- три главных паттерна медленных запросов и их признаки в EXPLAIN;
- когда добавить индекс и когда это не поможет.

**Цель:** читатель умеет найти медленный запрос, прочитать его EXPLAIN и понять — это проблема индекса, нагрузки или кода приложения. Передать разработчику с диагнозом, не просто «запрос медленный».

**Темы:**

Раздел "pg_stat_statements — топ медленных запросов":
```sql
-- Включить расширение (один раз)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- postgresql.conf
-- shared_preload_libraries = 'pg_stat_statements'  -- требует restart

-- Топ-10 запросов по суммарному времени
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

-- Топ-10 по среднему времени (самые медленные в среднем)
SELECT
    substring(query, 1, 100) AS query,
    calls,
    round(mean_exec_time::numeric, 2) AS avg_ms
FROM pg_stat_statements
WHERE calls > 100   -- только часто выполняемые
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Сбросить статистику
SELECT pg_stat_statements_reset();
```

Раздел "EXPLAIN ANALYZE — читать вывод":

Объяснить структуру: дерево узлов, каждый узел — шаг плана. Для каждого узла: `(cost=... rows=... width=...)` — оценка планировщика, `(actual time=... rows=... loops=...)` — реальность.

```sql
EXPLAIN ANALYZE
SELECT u.name, count(o.id)
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE u.created_at > '2026-01-01'
GROUP BY u.name;
```

Объяснить три главных сигнала проблемы и примеры вывода:

```text
Сигнал 1: Seq Scan на большой таблице
──────────────────────────────────────
Seq Scan on orders  (cost=0.00..45231.00 rows=1500000 ...)
                          ↑ огромный cost → полный просмотр 1.5 млн строк
→ Нет нужного индекса. Решение: CREATE INDEX ON orders(user_id);

Сигнал 2: Rows estimation далеко от actual
──────────────────────────────────────────
Hash Join  (cost=... rows=10 ...) (actual ... rows=150000 ...)
                      ↑ план думал 10, было 150000
→ Устаревшая статистика. Решение: ANALYZE orders;

Сигнал 3: Nested Loop на большом dataset
──────────────────────────────────────────
Nested Loop  (... loops=50000)
  → Index Scan on orders  (actual ... loops=50000)
→ N+1 запрос. На каждую строку из users делается запрос в orders.
  Решение: переписать запрос или добавить JOIN по индексу.
```

```sql
-- Получить EXPLAIN в формате JSON (удобнее анализировать)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT ...;

-- Онлайн-анализатор: вставить вывод на explain.dalibo.com или pganalyze.com
```

Раздел "Индексы: когда добавлять":
```sql
-- Найти таблицы с Sequential Scan > Index Scan
SELECT schemaname, relname, seq_scan, idx_scan,
       n_live_tup,
       seq_scan - idx_scan AS seq_minus_idx
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
  AND n_live_tup > 10000
ORDER BY seq_scan - idx_scan DESC;

-- Найти неиспользуемые индексы (только занимают место)
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;

-- Создать индекс без блокировки таблицы
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
-- CONCURRENTLY: долго строится, но не блокирует INSERT/UPDATE/DELETE
```

> ☠️ **Осторожно:** `CREATE INDEX` (без CONCURRENTLY) блокирует всю таблицу до завершения. На таблице из 10 млн строк это минуты. В production всегда использовать `CREATE INDEX CONCURRENTLY`.

**Типичные ошибки:**
- Добавлять индекс на колонку с низкой кардинальностью (например, boolean). Планировщик всё равно выберет Seq Scan.
- Смотреть только на `total_exec_time` в pg_stat_statements — важнее `mean_exec_time` и `calls`. Запрос с 100ms * 100000 calls хуже чем 10s * 10 calls.
- Читать только `cost` в EXPLAIN без `actual time` — cost это оценка, actual — реальность.

**Чек-лист для самопроверки:**
- [ ] Включил `pg_stat_statements` и умею найти топ медленных запросов
- [ ] Умею читать вывод `EXPLAIN ANALYZE` и найти три главных сигнала проблемы
- [ ] Знаю когда добавлять индекс и что использовать `CONCURRENTLY`
- [ ] Умею найти неиспользуемые индексы

**Попробуйте сами:**
1. Создайте таблицу с 100,000 строк (`INSERT INTO ... SELECT generate_series(1, 100000)`). Выполните `EXPLAIN ANALYZE SELECT * FROM mytable WHERE user_id = 42` — Seq Scan. Добавьте индекс. Повторите EXPLAIN — Index Scan. Разница в `actual time`?
2. Включите `pg_stat_statements`. Выполните несколько разных запросов 100+ раз каждый. Посмотрите `pg_stat_statements` — найдите самый медленный по `total_exec_time` и по `mean_exec_time`. Это разные запросы?
3. Найдите в вашей базе неиспользуемые индексы через `pg_stat_user_indexes`. Если есть — убедитесь что они действительно не нужны, прежде чем удалять.

---

### Глава 8: Connection Pooling — PgBouncer

**Что вы узнаете:**
- почему большое число соединений убивает PostgreSQL;
- три режима PgBouncer: session, transaction, statement;
- как установить и настроить PgBouncer;
- мониторинг PgBouncer: занятые, свободные соединения, очередь.

**Цель:** читатель ставит PgBouncer перед PostgreSQL и приложение работает со своими 500 worker'ами не убивая базу.

**Темы:**

Разместить Схему 3 (Connection Pooling) в начале главы.

Раздел "Почему нужен PgBouncer":
```text
PostgreSQL: каждое соединение = отдельный процесс ~10MB RAM
100 соединений → 1GB RAM только на процессы PostgreSQL
500 соединений → 5GB RAM → OOM killer убьёт PostgreSQL

Приложение в production:
- 10 pods × 50 workers = 500 соединений одновременно
- При spike-нагрузке: 500 × 2 = 1000 соединений

PgBouncer:
- Принимает 1000 соединений от приложений
- Держит 20-50 соединений к PostgreSQL
- Умеет ставить запросы в очередь при исчерпании пула
```

Раздел "Три режима пулинга":
```text
Session mode (сессионный):
- Соединение выдаётся клиенту на всё время его сессии
- = никакого пулинга на практике
- Только для совместимости со старым кодом

Transaction mode (транзакционный) — рекомендуется:
- Соединение из пула на время одной транзакции
- После COMMIT/ROLLBACK → возврат в пул
- 500 воркеров могут делиться 20 соединениями
- Ограничение: нельзя SET, LISTEN, prepared statements*

Statement mode (статементный):
- Соединение на один запрос
- Очень жёсткие ограничения
- Не использовать если не знаешь зачем
```

Раздел "Установка и конфигурация":
```bash
# Установка
sudo apt install pgbouncer

# Или Docker
docker run -d \
  --name pgbouncer \
  -p 5432:5432 \
  -e DATABASE_URL="postgres://appuser:password@postgres:5432/myapp" \
  -e POOL_MODE=transaction \
  -e MAX_CLIENT_CONN=1000 \
  -e DEFAULT_POOL_SIZE=20 \
  edoburu/pgbouncer
```

```ini
# /etc/pgbouncer/pgbouncer.ini

[databases]
# alias = host=... port=... dbname=... user=...
myapp = host=127.0.0.1 port=5432 dbname=myapp

[pgbouncer]
listen_port = 6432          # PgBouncer слушает на 6432 (не 5432)
listen_addr = 127.0.0.1
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

pool_mode = transaction     # рекомендуется
default_pool_size = 20      # соединений к PostgreSQL
max_client_conn = 1000      # соединений от приложений
reserve_pool_size = 5       # резерв для burst
reserve_pool_timeout = 5    # секунд ждать из резерва

# Мониторинг
admin_users = pgbouncer_admin
stats_users = monitoring

# Логирование
log_connections = 0
log_disconnections = 0
log_pooler_errors = 1
```

```text
# /etc/pgbouncer/userlist.txt
# Формат: "username" "scram-sha-256$..." или "md5..."
# Получить хеш из PostgreSQL:
# SELECT '"' || rolname || '" "' || rolpassword || '"' FROM pg_authid WHERE rolname = 'appuser';

"appuser" "SCRAM-SHA-256$4096:..."
```

Раздел "Мониторинг PgBouncer":
```bash
# Подключиться к консоли PgBouncer (специальная БД "pgbouncer")
psql -U pgbouncer_admin -h 127.0.0.1 -p 6432 pgbouncer

# Статус пулов
SHOW POOLS;
# database | user | cl_active | cl_waiting | sv_active | sv_idle | sv_used | maxwait
# myapp    | app  | 45        | 3          | 20        | 0       | 0       | 0.5

# cl_active: активных клиентских соединений
# cl_waiting: клиентов в очереди (нет свободных серверных соединений) ← мониторить!
# sv_active: активных соединений к PostgreSQL
# maxwait: время ожидания самого долгого в очереди ← > 1s = проблема

SHOW STATS;      # статистика запросов
SHOW CLIENTS;    # список клиентских соединений
SHOW SERVERS;    # список серверных соединений
```

**Типичные ошибки:**
- `transaction mode` + prepared statements = ошибка. Отключить prepared statements в приложении (`PgBouncer` документация: `prepare=false` в connection string).
- Слишком большой `default_pool_size` нивелирует пользу от pooling. 20-50 соединений к PostgreSQL достаточно для большинства приложений.
- `cl_waiting > 0` постоянно — пул слишком мал. Увеличить `default_pool_size` или оптимизировать длинные транзакции.
- PgBouncer в transaction mode не поддерживает `SET search_path`, `LISTEN/NOTIFY`, `LOCK TABLE` вне транзакций — проверить что приложение это не использует.

**Чек-лист для самопроверки:**
- [ ] Понимаю почему большое число соединений убивает PostgreSQL
- [ ] Знаю разницу между session и transaction mode и почему transaction лучше
- [ ] Умею настроить PgBouncer и подключить к нему приложение
- [ ] Умею читать `SHOW POOLS` — найти `cl_waiting` и `maxwait`

**Попробуйте сами:**
1. Запустите PgBouncer в Docker перед PostgreSQL. Измените строку подключения приложения на PgBouncer (порт 6432). Убедитесь что всё работает. Проверьте `SHOW POOLS` — видите активные соединения.
2. Создайте нагрузку: 100 параллельных подключений к PgBouncer (`pgbench -c 100 -j 4 -T 30 pgbouncer_dsn`). Посмотрите `SHOW POOLS` во время нагрузки. Сколько серверных соединений используется?
3. Проверьте `pg_stat_activity` на PostgreSQL во время нагрузки через PgBouncer. Убедитесь что соединений к PostgreSQL значительно меньше чем к PgBouncer.

---

### Глава 9: Репликация — streaming replication и read replicas

**Что вы узнаете:**
- как работает streaming replication;
- как настроить primary + replica;
- read replica: нагрузка на чтение на отдельный сервер;
- мониторинг lag и ручной failover.

**Цель:** читатель имеет read replica которая принимает read-запросы. Знает как переключиться на replica при падении primary (ручной failover).

**Темы:**

Разместить Схему 4 (Streaming Replication) в начале главы.

Раздел "Настройка primary":
```sql
-- На primary: создать пользователя для репликации
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'ReplPass123';
```

```ini
# postgresql.conf (primary)
wal_level = replica
max_wal_senders = 5         # максимум одновременных реплик
wal_keep_size = 1GB         # хранить минимум 1GB WAL для реплик
```

```text
# pg_hba.conf (primary)
# TYPE  DATABASE    USER        ADDRESS             METHOD
host    replication replicator  192.168.1.11/32     scram-sha-256
```

Раздел "Настройка replica":
```bash
# На replica: клонировать primary
pg_basebackup \
  -h 192.168.1.10 \          # IP primary
  -U replicator \
  -D /var/lib/postgresql/16/main \
  -P -Xs -R                   # -R = создаст standby.signal + auto.conf

# -R создаёт:
# - файл standby.signal (PostgreSQL знает что он реплика)
# - postgresql.auto.conf с primary_conninfo
```

```ini
# postgresql.auto.conf (replica, создаётся -R)
primary_conninfo = 'host=192.168.1.10 port=5432 user=replicator password=ReplPass123'
```

```bash
# Запустить replica
systemctl start postgresql
# PostgreSQL увидит standby.signal и начнёт получать WAL от primary
```

Раздел "Мониторинг репликации":
```sql
-- На primary: состояние репликации
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- Lag в байтах
SELECT client_addr,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes
FROM pg_stat_replication;

-- На replica: отставание
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
SELECT pg_is_in_recovery();   -- true = это реплика
```

Раздел "Read replica: направить чтение":
Объяснить что read replica принимает SELECT-запросы (только чтение). Запись — только на primary. Два варианта направления трафика:

```text
Вариант 1: на уровне приложения
  Django: DATABASES['replica']['HOST'] = 'replica-host'
  Rails: establish_connection :replica
  Hibernate: @ReadReplica annotation

Вариант 2: через PgBouncer + несколько баз
  [databases]
  myapp = host=primary ...    (write operations)
  myapp_ro = host=replica ... (read operations)
```

Раздел "Failover (ручной)":
```text
Сценарий: primary упал, нужно переключиться на replica.

Шаги:
1. Убедиться что primary недоступен (не ложная тревога)
2. На replica:
   SELECT pg_promote();   -- PostgreSQL 12+
   -- или
   pg_ctl promote -D /var/lib/postgresql/16/main
   
3. Replica стала primary (pg_is_in_recovery() = false)
4. Обновить строки подключения в приложениях
5. Обновить pg_hba.conf и postgresql.conf если нужно
6. Когда старый primary восстановится — сделать его репликой нового primary
   (pg_basebackup снова или через pg_rewind)
```

Упомянуть Patroni: для автоматического failover используют Patroni (или repmgr). Это серьёзный инструмент требующий отдельного изучения. Для homelab и небольших систем — ручной failover достаточен.

**Типичные ошибки:**
- Не мониторить replication lag — replica отстала на 10 минут, никто не знает. Алерт на `replay_lag > 60s`.
- `wal_keep_size` слишком мал — replica отстала и WAL-файлы уже удалены с primary. Replica сломана, нужно клонировать заново.
- Читать с replica без учёта lag — данные могут быть устаревшими. Для critical reads (например, проверка платежа) — читать только с primary.
- После failover не обновить строки подключения везде — часть сервисов пишет в старый primary (который упал), часть в новый. Раздвоение данных.

**Чек-лист для самопроверки:**
- [ ] Понимаю как работает streaming replication (WAL от primary к replica)
- [ ] Умею настроить primary + replica через pg_basebackup -R
- [ ] Знаю как мониторить lag через `pg_stat_replication`
- [ ] Понимаю процедуру ручного failover через `pg_promote()`

**Попробуйте сами:**
1. Запустите два PostgreSQL в Docker Compose. Настройте репликацию. Убедитесь что `pg_is_in_recovery() = true` на replica. Запишите данные на primary — они появляются на replica?
2. Проверьте lag: сделайте интенсивную запись на primary (`pgbench`). Смотрите `replay_lag` на primary. Становится больше под нагрузкой?
3. Выполните ручной failover: остановите primary, выполните `pg_promote()` на replica. Убедитесь что новый primary принимает запись (`INSERT INTO test VALUES (1)`).

---

### Глава 10: PostgreSQL в Docker и Kubernetes

**Что вы узнаете:**
- правильная конфигурация PostgreSQL-контейнера: данные, конфиги, секреты;
- PostgreSQL в Kubernetes: StatefulSet, PVC, headless service;
- CloudNativePG — оператор K8s для PostgreSQL;
- подводные камни контейнеризованного PostgreSQL.

**Цель:** читатель запускает PostgreSQL в Kubernetes надёжно: данные переживают рестарт пода, секреты из Vault, бэкапы работают.

**Темы:**

Раздел "Docker: правильная конфигурация":
```yaml
# docker-compose.yml — production-ready
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_USER: appuser
      POSTGRES_DB: myapp
      # Настройки производительности через переменные
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=en_US.utf8"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./config/postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./config/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro
    command: >
      postgres
      -c config_file=/etc/postgresql/postgresql.conf
      -c hba_file=/etc/postgresql/pg_hba.conf
    ports:
      - "127.0.0.1:5432:5432"  # не открывать наружу
    secrets:
      - postgres_password
    shm_size: '256mb'
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d myapp"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  pgdata:

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
```

Раздел "Kubernetes: StatefulSet":
```yaml
# postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: production
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
            - name: POSTGRES_USER
              value: appuser
            - name: POSTGRES_DB
              value: myapp
          volumeMounts:
            - name: pgdata
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "2Gi"
              cpu: "1"
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "appuser", "-d", "myapp"]
            initialDelaySeconds: 15
            periodSeconds: 10
  volumeClaimTemplates:
    - metadata:
        name: pgdata
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: production
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
  clusterIP: None   # headless service: DNS → pod IP напрямую
```

Раздел "CloudNativePG — оператор для K8s":
```yaml
# Установка
kubectl apply -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.0.yaml

# Кластер PostgreSQL через CR (Custom Resource)
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: myapp-postgres
spec:
  instances: 3          # 1 primary + 2 replicas
  imageName: ghcr.io/cloudnative-pg/postgresql:16

  storage:
    size: 20Gi

  superuserSecret:
    name: postgres-superuser-secret

  backup:
    barmanObjectStore:
      destinationPath: "s3://my-bucket/myapp-postgres"
      s3Credentials:
        accessKeyId:
          name: aws-creds
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: aws-creds
          key: ACCESS_SECRET_KEY
      wal:
        compression: gzip
    retentionPolicy: "7d"
```

Объяснить: CloudNativePG управляет всем — репликацией, failover, бэкапами, восстановлением. Для production K8s — лучший выбор.

**Типичные ошибки:**
- Хранить данные PostgreSQL в `emptyDir` — при рестарте пода все данные теряются. Только PVC с `ReadWriteOnce`.
- Запускать PostgreSQL как `Deployment` вместо `StatefulSet` — нет гарантий уникальности пода и стабильного DNS-имени.
- `shm_size` не указан в Docker — `/dev/shm` только 64MB, PostgreSQL использует shared memory для работы буферов. Нужно минимум 256MB.
- Использовать `latest` тег образа — обновление произойдёт неожиданно при следующем pull. Всегда фиксировать версию: `postgres:16.3-alpine`.

**Чек-лист для самопроверки:**
- [ ] Знаю почему PostgreSQL в K8s должен быть StatefulSet, не Deployment
- [ ] Умею настроить PVC для персистентности данных
- [ ] Знаю о CloudNativePG как операторе для production K8s
- [ ] Понимаю зачем нужен `shm_size` в Docker

**Попробуйте сами:**
1. Запустите PostgreSQL в K8s как StatefulSet. Запишите данные. Удалите под (`kubectl delete pod postgres-0`). Дождитесь пересоздания. Данные сохранились?
2. Посмотрите через `kubectl describe pvc` — какой StorageClass используется? Что произойдёт с данными при удалении PVC?
3. Посмотрите метрики PostgreSQL-пода через `kubectl top pod postgres-0`. Сравните с `resources.requests` — есть ли запас?

---

### Глава 11: Миграции без даунтайма — expand/contract

**Что вы узнаете:**
- почему некоторые ALTER TABLE блокируют таблицу;
- паттерн expand/contract для безопасных миграций;
- конкретные примеры: добавить колонку, переименовать, изменить тип;
- как проверить что миграция безопасна.

**Цель:** читатель знает какие DDL-операции опасны и умеет выполнить любое изменение схемы без даунтайма.

**Темы:**

Разместить Схему 5 (expand/contract flowchart) в начале главы.

Раздел "Почему DDL блокирует":
```text
PostgreSQL DDL-операции и их блокировки:

Безопасно (не блокирует):
✓ CREATE INDEX CONCURRENTLY
✓ ADD COLUMN (nullable, без DEFAULT или с константным DEFAULT, PG 11+)
✓ DROP INDEX CONCURRENTLY
✓ CREATE TABLE
✓ ALTER TABLE ... ADD CONSTRAINT ... NOT VALID

Опасно (блокирует таблицу):
✗ ADD COLUMN NOT NULL без DEFAULT    ← переписывает все строки
✗ ALTER COLUMN TYPE                  ← переписывает все строки
✗ ADD CONSTRAINT (без NOT VALID)     ← проверяет все строки
✗ CREATE INDEX (без CONCURRENTLY)    ← блокирует запись
✗ DROP COLUMN                        ← блокирует
```

Раздел "Добавить колонку с NOT NULL":
```sql
-- Плохо (блокирует таблицу при большом дефолтном значении):
ALTER TABLE users ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active';

-- Хорошо (expand/contract):

-- Шаг 1: Добавить nullable колонку (мгновенно, PostgreSQL 11+)
ALTER TABLE users ADD COLUMN status VARCHAR(20);

-- Шаг 2: Добавить дефолтное значение без блокировки
ALTER TABLE users ALTER COLUMN status SET DEFAULT 'active';

-- Шаг 3: Заполнить существующие строки батчами (не UPDATE всего!)
DO $$
DECLARE
  batch_size INT := 10000;
  offset_val INT := 0;
BEGIN
  LOOP
    UPDATE users SET status = 'active'
    WHERE id IN (
      SELECT id FROM users WHERE status IS NULL
      ORDER BY id LIMIT batch_size
    );
    EXIT WHEN NOT FOUND;
    PERFORM pg_sleep(0.01);   -- небольшая пауза между батчами
  END LOOP;
END $$;

-- Шаг 4: После заполнения — добавить NOT NULL constraint
ALTER TABLE users ALTER COLUMN status SET NOT NULL;
-- (PostgreSQL проверит что NULL не осталось, но если заполнили — быстро)
```

Раздел "Переименовать колонку":
```sql
-- Нельзя просто RENAME — сломает все запросы в деплое старого кода

-- Expand: добавить новую колонку
ALTER TABLE users ADD COLUMN full_name VARCHAR(255);

-- Синхронизировать данные через триггер
CREATE OR REPLACE FUNCTION sync_names() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
    NEW.full_name := NEW.name;
    NEW.name := NEW.full_name;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_names_trigger
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION sync_names();

-- Бэкфилл существующих данных
UPDATE users SET full_name = name WHERE full_name IS NULL;

-- Деплой нового кода который читает full_name
-- Деплой кода который пишет в full_name
-- Удалить триггер
-- Contract: DROP COLUMN name (через несколько дней)
```

Раздел "Инструменты для безопасных миграций":
```text
strong_migrations (Ruby/Rails):
  - Гем который проверяет миграции на опасные операции
  - Ошибка при попытке ADD COLUMN NOT NULL без шагов

squawk (PostgreSQL migration linter):
  squawk migration.sql
  → warns: "Adding a column with a volatile default is not safe"

django-zero-downtime-migrations:
  - Аналог для Django
```

**Типичные ошибки:**
- `ALTER TABLE users ADD COLUMN score INTEGER DEFAULT 0 NOT NULL` на таблице 50 млн строк в PostgreSQL < 11 — блокировка на несколько минут. В PG 11+ с константным DEFAULT — мгновенно (default хранится в метаданных, не переписывает строки).
- Батчевый UPDATE без паузы (`pg_sleep`) — перегружает PostgreSQL, лаг на репликах, slow queries у пользователей.
- Удалить старую колонку сразу после переименования — старый код ещё работает и обращается к ней. Contract делать через 1-2 дня после полного деплоя нового кода.

**Чек-лист для самопроверки:**
- [ ] Знаю какие DDL-операции опасны и почему
- [ ] Умею добавить NOT NULL колонку в большую таблицу без блокировки
- [ ] Понимаю шаги expand/contract: добавить → дуальная запись → backfill → переключить → удалить
- [ ] Знаю о `squawk` и `strong_migrations` для проверки миграций

**Попробуйте сами:**
1. Создайте таблицу с 1 млн строк. Попробуйте `ALTER TABLE ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'` — замерьте время. В PostgreSQL 11+ это быстро. Теперь попробуйте `DEFAULT random()::text` — медленно (volatile default переписывает строки).
2. Выполните expand/contract миграцию: добавьте nullable колонку, заполните батчами, добавьте NOT NULL. Убедитесь что таблица не блокировалась (другие SELECT работали во время UPDATE).
3. Установите `squawk` и проверьте несколько миграций из вашего проекта. Есть ли небезопасные?

---

### Глава 12: Диагностика — алгоритм разбора инцидентов

**Что вы узнаете:**
- системный подход к диагностике PostgreSQL-инцидентов;
- пять типовых сценариев: что сломалось и как найти;
- быстрые проверки которые дают ответ за 2 минуты;
- что собрать для передачи DBA или разработчику.

**Цель:** при инциденте читатель не паникует, а идёт по алгоритму. За 5-10 минут ставит диагноз: «проблема здесь, вот данные».

**Темы:**

Раздел "Алгоритм первичной диагностики":

```mermaid
flowchart TD
    A[Проблема с PostgreSQL] --> B{PostgreSQL отвечает?}
    B -->|Нет| C[pg_isready / systemctl status]
    C --> C1{Причина}
    C1 -->|Disk full| D[df -h → /var/lib/postgresql]
    C1 -->|OOM| E[dmesg | grep -i 'oom\|killed']
    C1 -->|Crash| F[journalctl -u postgresql --since '1h ago']
    B -->|Да| G{Медленно или ошибки?}
    G -->|Медленно| H[pg_stat_activity: active + waiting]
    H --> H1{Есть ожидающие?}
    H1 -->|Lock wait| I[pg_blocking_pids → убить блокирующий]
    H1 -->|Нет| J[pg_stat_statements: топ медленных запросов]
    G -->|Ошибки| K[Логи приложения + pg_log]
    K --> K1{Тип ошибки}
    K1 -->|connection refused| L[max_connections исчерпан? ss -tnp]
    K1 -->|too many clients| M[PgBouncer не настроен?]
    K1 -->|deadlock| N[pg_log: deadlock detail]
```

Раздел "Сценарий 1: PostgreSQL не принимает соединения":
```bash
# Быстрые проверки (30 секунд)
pg_isready -h localhost -p 5432       # отвечает?
systemctl status postgresql            # запущен?
df -h /var/lib/postgresql             # диск не заполнен?
journalctl -u postgresql -n 50        # последние ошибки

# Если диск полон:
du -sh /var/lib/postgresql/16/main/pg_wal/   # WAL занимает много?
# Удалить старые WAL через checkpoint:
sudo -u postgres psql -c "CHECKPOINT;"
# Настроить wal_keep_size если проблема повторяется

# Если max_connections исчерпан:
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
# Убить idle соединения старше 10 минут:
sudo -u postgres psql -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND state_change < now() - interval '10 minutes';"
```

Раздел "Сценарий 2: Всё работает, но медленно":
```sql
-- За 2 минуты:

-- 1. Активные запросы и сколько ждут
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC
LIMIT 10;

-- 2. Есть ли блокировки?
SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock';

-- 3. Нагрузка на checkpoint (частые checkpoint = нагрузка на WAL)
SELECT checkpoints_timed, checkpoints_req, buffers_checkpoint
FROM pg_stat_bgwriter;

-- 4. Cache hit ratio
SELECT round(blks_hit * 100.0 / (blks_hit + blks_read), 2) AS hit_ratio
FROM pg_stat_database
WHERE datname = current_database();
-- < 90% → увеличить shared_buffers
```

Раздел "Сценарий 3: Репликация отстала":
```sql
-- На primary
SELECT client_addr, replay_lag FROM pg_stat_replication;

-- Причины:
-- 1. Сетевая нагрузка между primary и replica (проверить bandwidth)
-- 2. Replica не справляется с применением WAL (CPU/IO реплики)
-- 3. long-running query на primary держит xmin → autovacuum не чистит
SELECT pid, now() - query_start AS age, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '5 minutes';
```

Раздел "Что собрать для DBA/разработчика":
```text
При передаче проблемы DBA указать:

1. Временной диапазон инцидента (когда началось, когда заметили)
2. Вывод pg_stat_activity в момент проблемы
3. Фрагмент pg_log за этот период
4. Результат pg_stat_statements за период
5. Метрики из Prometheus (если есть): TPS, connections, cache hit, lag
6. Что изменилось перед инцидентом: деплой, миграция, нагрузка
```

**Типичные ошибки:**
- Перезапускать PostgreSQL как первый шаг диагностики — теряется `pg_stat_activity`, `pg_stat_statements`, информация о блокировках.
- Убивать все соединения подряд — может прервать критические транзакции. Сначала идентифицировать виновника через `pg_blocking_pids`.
- Не логировать медленные запросы (`log_min_duration_statement`) — нет данных для анализа после инцидента.

**Чек-лист для самопроверки:**
- [ ] Знаю 4 первых команды при недоступности PostgreSQL
- [ ] Умею найти причину медленной работы за 2 минуты
- [ ] Знаю что собрать при передаче проблемы DBA
- [ ] Никогда не перезапускаю PostgreSQL как первый шаг

**Попробуйте сами:**
1. Создайте искусственную блокировку (BEGIN + UPDATE без COMMIT в одном соединении). Пройдите по алгоритму диагностики: найдите блокировку, определите виновника, устраните.
2. Заполните диск WAL-файлами (symlink + несколько больших транзакций). Попробуйте подключиться к PostgreSQL. Диагностируйте за 2 минуты.
3. Создайте нагрузку через `pgbench`. Одновременно смотрите `pg_stat_activity`, `pg_stat_bgwriter`, hit ratio. Как меняются показатели под нагрузкой?

---

## Приложения

### Приложение A: Шпаргалка команд

Разделы: psql команды (`\dt`, `\d table`, `\du`, `\c db`), администрирование (pg_dump, pg_restore, pg_basebackup), роли и права, pg_stat_activity частые запросы, PgBouncer консоль, WAL и репликация. Формат: комментарий + команда. Максимум 2 страницы.

### Приложение B: Важные системные представления (pg_stat_*)

Таблица для каждого представления: название, что показывает, когда использовать, пример запроса. Включить: `pg_stat_activity`, `pg_stat_user_tables`, `pg_stat_user_indexes`, `pg_stat_replication`, `pg_stat_bgwriter`, `pg_stat_database`, `pg_locks`, `pg_stat_statements`.

### Приложение C: Чеклист production PostgreSQL

Список с чекбоксами — что должно быть настроено перед выходом в production:

```
[ ] Бэкапы настроены и протестированы (ежедневный pg_dump или pg_basebackup)
[ ] WAL-архивирование (для PITR)
[ ] Мониторинг: postgres_exporter + Grafana дашборд
[ ] Алерт на pg_up = 0
[ ] Алерт на replication lag > 60s
[ ] Алерт на disk usage > 80%
[ ] Алерт на idle in transaction > 20
[ ] PgBouncer настроен (если > 20 соединений)
[ ] Пользователь postgres не используется приложением
[ ] SSL включён (hostnossl reject в pg_hba.conf)
[ ] log_min_duration_statement = 1000 (медленные запросы логируются)
[ ] autovacuum включён (никогда не выключать)
[ ] shared_buffers = 25% RAM
[ ] max_connections соответствует реальным потребностям
[ ] Версия PostgreSQL зафиксирована (не latest)
[ ] Тест восстановления проведён и записан результат
```

---

## Что читатель получит к концу книги

- Работающий PostgreSQL в Docker с персистентностью, SSL и правильными правами
- Ежедневные бэкапы + WAL-архивирование + тест восстановления
- Мониторинг: postgres_exporter, Grafana дашборд, алерты на ключевые метрики
- pg_stat_statements включён, медленные запросы логируются
- PgBouncer перед PostgreSQL в transaction mode
- Read replica настроена, lag монируется
- Умение делать expand/contract миграции без даунтайма
- Алгоритм диагностики инцидентов: диагноз за 5-10 минут без паники
