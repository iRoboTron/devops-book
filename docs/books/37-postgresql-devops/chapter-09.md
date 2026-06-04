# Глава 9: Репликация — streaming replication и read replicas

**Что вы узнаете:**
- как работает streaming replication: WAL от primary к replica;
- как настроить primary + replica с нуля;
- read replica: направить запросы на чтение на отдельный сервер;
- мониторинг lag и ручной failover;
- logical replication: выборочная репликация таблиц и zero-downtime upgrade.

**Цель:** читатель имеет read replica, которая принимает read-запросы. Знает как переключиться на replica при падении primary. Понимает разницу между streaming и logical replication.

---

## Схема 4: Streaming Replication

```
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

---

## Как работает streaming replication

Streaming replication — механизм, при котором primary сервер PostgreSQL непрерывно передаёт WAL (Write-Ahead Log) одной или нескольким репликам. Реплики применяют WAL к своим данным, поддерживая точную копию primary.

WAL — это не данные, а журнал изменений. Реплика читает WAL и воспроизводит каждое изменение в точности как оно произошло на primary. Поэтому реплика является бинарно идентичной копией — те же таблицы, те же индексы, те же OID.

Терминология:
- **Primary** — сервер, который принимает запись (INSERT/UPDATE/DELETE).
- **Replica** (standby) — сервер, который получает WAL и применяет его. Только чтение.
- **WAL Sender** — процесс на primary, который отправляет WAL реплике.
- **WAL Receiver** — процесс на replica, который получает WAL.
- **Replay** — применение WAL на replica.

Streaming replication бывает:
- **Asynchronous** (по умолчанию) — primary не ждёт подтверждения от реплики. Commit на primary — данные могут быть ещё не на реплике. Риск потери последних секунд при крахе primary.
- **Synchronous** — primary ждёт пока реплика запишет WAL на диск. Нет потери данных, но запись дольше (RTT до реплики).

---

## Настройка primary

### 1. Создать пользователя для репликации

```sql
-- На primary
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'ReplPass123';
```

Право `REPLICATION` необходимо для `pg_basebackup` и для потоковой репликации. Это минимальное право, без суперпользователя.

### 2. Настроить postgresql.conf

```ini
# postgresql.conf (primary)

# Уровень WAL — должен быть replica или logical
wal_level = replica

# Максимум одновременных WAL senders (реплик + бэкапов)
max_wal_senders = 5

# Минимум WAL на диске для отставших реплик
wal_keep_size = 1GB

# Рекомендуется для синхронной репликации
# synchronous_standby_names = 'FIRST 1 (replica1)'
```

- `wal_level = replica` — минимальный уровень для streaming replication (по умолчанию). `logical` — если нужна logical replication.
- `max_wal_senders` — максимальное число одновременных подключений WAL. Каждая реплика + каждый `pg_basebackup` = один слот. Для 2 реплик + 1 бэкап достаточно 5.
- `wal_keep_size` — сколько WAL хранить на primary для отставших реплик. Если replica отстала больше чем на 1GB — ей понадобится новый `pg_basebackup`.

> Вместо `wal_keep_size` можно использовать **replication slots**. Слот гарантирует что WAL не удалится пока replica его не получила. Но если replica упала надолго — диск заполнится.

### 3. Настроить pg_hba.conf

```text
# pg_hba.conf (primary)
# TYPE    DATABASE        USER            ADDRESS             METHOD
host    replication     replicator      192.168.1.11/32     scram-sha-256
```

Тип `replication` — отдельный, не `all`. Он разрешает подключение к виртуальной БД "replication". Без этой записи `pg_basebackup` и WAL sender будут отклонены.

### 4. Перезагрузить конфигурацию

```bash
sudo systemctl reload postgresql
# или
SELECT pg_reload_conf();
```

---

## Настройка replica

### 1. Установить PostgreSQL на replica (та же версия)

```bash
sudo apt install -y postgresql-16
```

Версия PostgreSQL на replica должна совпадать с primary. Разные minor-версии допустимы (16.1 и 16.3), но major-версии — обязательно одинаковые.

### 2. Остановить PostgreSQL и очистить PGDATA

```bash
sudo systemctl stop postgresql
sudo rm -rf /var/lib/postgresql/16/main/*
```

### 3. Клонировать primary через pg_basebackup

```bash
pg_basebackup \
  -h 192.168.1.10 \              # IP primary
  -U replicator \
  -D /var/lib/postgresql/16/main \
  -P -Xs -R
```

Ключи:
- `-P` — progress bar (сколько передано).
- `-Xs` — включить текущий WAL в бэкап (stream mode).
- `-R` — **создать `standby.signal` + `postgresql.auto.conf` с `primary_conninfo`**.

Что создаёт `-R`:

```text
# standby.signal — маркер что это реплика (PG 12+)
# Если файл есть → PostgreSQL запускается в standby mode

# postgresql.auto.conf — переопределения конфигурации
primary_conninfo = 'host=192.168.1.10 port=5432 user=replicator password=ReplPass123'
```

### 4. Запустить replica

```bash
sudo systemctl start postgresql
```

PostgreSQL видит `standby.signal` и запускается в режиме реплики. Он подключается к primary по `primary_conninfo` и начинает получать WAL.

### 5. Проверить

```sql
-- На replica
SELECT pg_is_in_recovery();
-- true → это реплика (только чтение)

SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
-- отставание в секундах
```

---

## Мониторинг репликации

### На primary: состояние подключенных реплик

```sql
SELECT client_addr, state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

- `client_addr` — IP реплики.
- `state` — `streaming` (работает), `catchup` (догоняет), `startup` (подключается).
- `sent_lsn` — последний LSN отправленный реплике.
- `replay_lag` — отставание в применении WAL (type interval).
- `write_lag`, `flush_lag` — отставание записи/сброса на диск.

### Lag в байтах

```sql
SELECT client_addr,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes
FROM pg_stat_replication;
```

`pg_wal_lsn_diff` — разница между текущим LSN на primary и тем, что реплика уже применила. Если lag_bytes растёт — replica не успевает.

### На replica: отставание по времени

```sql
-- Сколько секунд назад последняя применённая транзакция
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
-- Если replica догнала — значение близко к 0

-- Ошибка: если реплика долго не получала WAL
-- pg_last_xact_replay_timestamp() может быть NULL
```

### Алертинг

```promql
# Prometheus: алерт на лаг > 60 секунд
pg_stat_replication_replay_lag_seconds > 60
```

> Lag — нормальное явление при пиковой нагрузке. Тревога должна быть на sustained lag > 60s, не на spike.

---

## Read replica: направление read-трафика

Read replica — это та же streaming replica, но её явно используют для SELECT-запросов, разгружая primary.

**Важно:** replica принимает только SELECT. Любая попытка INSERT/UPDATE/DELETE на replica:
```
ERROR:  cannot execute INSERT in a read-only transaction
```

### Вариант 1: на уровне приложения

Приложение само решает, на какой сервер отправлять запрос:

```text
Django:
  DATABASES = {
      'default': {            # primary — запись
          'HOST': 'primary-host',
      },
      'replica': {            # replica — чтение
          'HOST': 'replica-host',
      },
  }
  # Использование: User.objects.using('replica').all()

Rails:
  config.read_replica = 'replica-host'
  # ActiveRecord::Base.connected_to(role: :reading)

Hibernate / Spring:
  @ReadReplica  # аннотация для read-only методов
```

**Плюсы:** полный контроль, явно видно где какой запрос.
**Минусы:** каждый сервис нужно настраивать отдельно.

### Вариант 2: через PgBouncer с несколькими базами

```ini
# /etc/pgbouncer/pgbouncer.ini
[databases]
myapp = host=primary-host port=5432 dbname=myapp       # write
myapp_ro = host=replica-host port=5432 dbname=myapp    # read-only
```

Приложение использует `myapp` для записи и `myapp_ro` для чтения. PgBouncer маршрутизирует на нужный сервер.

**Плюсы:** единая точка конфигурации, не нужно менять приложение (только connection string).
**Минусы:** дополнительный hop через PgBouncer.

### Когда читать с replica — предостережение

```text
Чтение с replica даёт устаревшие данные.

Сценарий:
1. Пользователь оформил заказ (INSERT на primary)
2. Перенаправлен на страницу подтверждения
3. SELECT заказа идёт на replica (lag 2 секунды)
4. Пользователь видит: "Заказ не найден" ← паника

Правило:
- read-after-write (проверка платежа, подтверждение) → только primary
- аналитика, отчёты, дашборды → replica (допустима задержка)
```

---

## Ручной failover

**Сценарий:** primary упал. Нужно сделать replica новым primary.

> ☠️ **Осторожно:** ручной failover — необратимая операция. После `pg_promote()` старая replica становится primary. Если старый primary всё ещё работает — у вас два primary, данные расходятся. Всегда сначала убеждаться что старый primary мёртв.

### Шаги failover

```
1. Убедиться что primary недоступен:
   - pg_isready -h primary-host — не отвечает
   - Проверить в мониторинге: метрики пропали?
   - Не ложная тревога (сетевая проблема?)

2. На реплике:
   sudo -u postgres psql -c "SELECT pg_promote();"
   # Или:
   pg_ctl promote -D /var/lib/postgresql/16/main

3. Проверить что replica стала primary:
   sudo -u postgres psql -c "SELECT pg_is_in_recovery();"
   → false (теперь это primary)

4. Обновить строки подключения в приложениях:
   - Поменять DNS/endpoint на новый primary
   - Или изменить PgBouncer конфиг

5. Настроить pg_hba.conf нового primary:
   - Добавить правило для репликации (если есть другие реплики)

6. Когда старый primary восстановится:
   - Сделать его репликой нового primary
   - pg_basebackup с нового primary на старый
   - Или pg_rewind (если нужно быстро)
```

После failover все реплики, которые были подключены к старому primary, нужно перенастроить на новый.

---

### Когда failover не нужен

Failover — это стресс. Если приложение переживёт 5-10 минут простоя, не делайте failover. Восстановите primary и перезапустите.

Failover делают когда:
- primary не восстановится в ближайшие 30 минут (аппаратная поломка, потеря диска);
- у приложения нет tolerance к простою;
- реплика есть и отставание минимальное.

---

### Patroni: автоматический failover

```text
Patroni — система для автоматического управления репликацией и failover.

Что делает:
- Мониторит primary (healthcheck каждые N секунд)
- При падении primary — автоматически выбирает новую реплику
- Управляет VIP/DNS для переключения приложений
- Поддерживает synchronous replication

Что НЕ делает:
- Не клонирует реплики (нужен WAL archiving или pg_basebackup)
- Не делает бэкапы (нужен WAL-G / pgBackRest)

Trade-offs:
✓ Автоматический failover за 10-30 секунд
✓ Консистентность: не даёт split-brain
✓ Интеграция с etcd/Consul для кворума

✗ Learning curve: DCS (etcd/Consul), конфигурация, тестирование
✗ Overhead для 1-2 серверов: проще ручной failover
✗ При сбое DCS — кластер может встать

Когда Patroni нужен:
- 3+ сервера PostgreSQL
- SLA требует recovery < 5 минут
- Есть команда которая умеет его поддерживать

Когда Patroni не нужен:
- 1 primary + 1 replica
- Ручной failover за 15 минут — допустимо
- Нет опыта работы с etcd/Consul
```

---

## Logical replication

Streaming replication реплицирует **весь кластер** — все базы, все таблицы, бинарно идентично. Logical replication реплицирует **выбранные таблицы** на уровне строк.

```text
Streaming replication (physical):
  Реплицирует: весь кластер (WAL на уровне блоков)
  Версии PG:  одинаковые major-версии
  Назначение:  read replica, HA, резервирование

Logical replication:
  Реплицирует: выбранные таблицы (строки)
  Версии PG:  разные версии (15 → 16, 14 → 17)
  Назначение:  zero-downtime upgrade, аналитика, selective sharing
```

### Когда нужна logical replication

1. **Zero-downtime upgrade PostgreSQL** — настройка logical replication между PG 15 (старый) и PG 16 (новый), переключение трафика, остановка старого.
2. **Выборочная репликация** — только таблицы `orders` и `users` в аналитическое хранилище.
3. **Сбор данных с нескольких серверов** — несколько primary публикуют данные в одну центральную БД.

### Настройка: publisher (primary)

```sql
-- На publisher: создать публикацию для выбранных таблиц
CREATE PUBLICATION mypub FOR TABLE users, orders;

-- Все таблицы в схеме:
-- CREATE PUBLICATION mypub FOR ALL TABLES;

-- С фильтром строк (PG 15+):
-- CREATE PUBLICATION mypub FOR TABLE users WHERE (active = true);
```

### Настройка: subscriber (replica)

```sql
-- На subscriber: создать подписку
CREATE SUBSCRIPTION mysub
CONNECTION 'host=publisher-db port=5432 dbname=myapp user=replicator password=ReplPass123'
PUBLICATION mypub;

-- С копированием существующих данных (по умолчанию)
-- Без копирования (только новые изменения):
-- CREATE SUBSCRIPTION mysub ... PUBLICATION mypub WITH (copy_data = false);
```

Subscriber запускает COPY существующих данных из publisher, затем переключается на streaming изменений.

### Мониторинг logical replication

```sql
-- На publisher: состояние публикации
SELECT * FROM pg_publication;

-- На subscriber: состояние подписки
SELECT * FROM pg_subscription;

-- Лаг logical replication
SELECT slot_name, pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)
FROM pg_replication_slots
WHERE slot_type = 'logical';
```

### Zero-downtime upgrade через logical replication

```text
Сценарий: апгрейд PostgreSQL 15 → 16 без простоя.

Шаги:
1. Установить PostgreSQL 16 рядом (новый сервер или контейнер)
2. Настроить logical replication с PG 15 (publisher) на PG 16 (subscriber)
3. Дождаться когда PG 16 догонит (lag ≈ 0)
4. Остановить запись на приложении (read-only mode)
5. Дождаться финальной синхронизации (lag = 0)
6. Переключить приложение на PG 16
7. Включить запись на приложении
8. Остановить PG 15

Время простоя: секунды (финальная синхронизация + переключение)
```

> ☠️ **Осторожно:** logical replication не реплицирует DDL (CREATE TABLE, ALTER TABLE). Sequence nextval тоже не реплицируется. DDL нужно выполнять на subscriber вручную.

### Ограничения logical replication

```text
- Не реплицирует DDL (только DML: INSERT, UPDATE, DELETE, TRUNCATE)
- Не реплицирует sequences (nextval)
- Не реплицирует TRUNCATE (до PG 11 не было, с PG 11+ реплицируется)
- TRUNCATE — только если таблица в публикации
- Требует PRIMARY KEY или REPLICA IDENTITY FULL на таблице
- Латентность выше чем у streaming replication
```

---

## Типичные ошибки

- **Не мониторить replication lag** — replica отстала на 10 минут, никто не знает. Алерт на `replay_lag > 60s` обязателен.
- **`wal_keep_size` слишком мал** — replica отстала и WAL-файлы уже удалены с primary. Replica сломана, нужно клонировать заново. Лечение: настроить replication slots.
- **Читать с replica без учёта lag** — данные могут быть устаревшими. Для critical reads (проверка платежа, подтверждение заказа) — только primary.
- **После failover не обновить строки подключения** — часть сервисов пишет в старый primary (который упал), часть — в новый. Раздвоение данных.
- **Использовать logical replication без primary key** — таблицы без PK реплицируются медленно (REPLICA IDENTITY FULL = каждая строка копируется целиком).
- **Думать что logical replication = streaming replication** — разные механизмы, разные сценарии. Logical replication не заменяет physical для HA.

---

## Чек-лист для самопроверки

- [ ] Понимаю как работает streaming replication: WAL от primary к replica
- [ ] Умею настроить primary + replica через `pg_basebackup -R`
- [ ] Знаю разницу между sync и async replication
- [ ] Умею мониторить lag через `pg_stat_replication` и `pg_wal_lsn_diff`
- [ ] Понимаю процедуру ручного failover через `pg_promote()`
- [ ] Знаю когда Patroni нужен, а когда достаточно ручного failover
- [ ] Понимаю разницу между streaming и logical replication
- [ ] Умею настроить logical replication: `CREATE PUBLICATION` + `CREATE SUBSCRIPTION`
- [ ] Знаю сценарий zero-downtime upgrade через logical replication

---

## Попробуйте сами

1. Запустите два PostgreSQL в Docker Compose. Настройте streaming replication. Убедитесь что `pg_is_in_recovery() = true` на replica. Запишите данные на primary — они появляются на replica?

2. Проверьте lag: сделайте интенсивную запись на primary через `pgbench`. Смотрите `replay_lag` в `pg_stat_replication`. Становится больше под нагрузкой?

3. Выполните ручной failover: остановите primary (`docker stop`), выполните `SELECT pg_promote()` на replica. Убедитесь что новый primary принимает запись. Перенастройте реплику.

4. Настройте logical replication между двумя PostgreSQL (15 и 16). Создайте публикацию для одной таблицы. Убедитесь что строки реплицируются. Выполните DDL на subscriber — убедитесь что logical replication не реплицирует её.
