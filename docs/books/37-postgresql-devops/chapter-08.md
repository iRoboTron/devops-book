# Глава 8: Connection Pooling — PgBouncer

## Что вы узнаете

- почему большое число соединений убивает PostgreSQL;
- три режима PgBouncer и когда какой использовать;
- как установить, настроить и запустить PgBouncer;
- мониторинг PgBouncer: занятые/свободные соединения, очередь ожидания.

## Почему нужен PgBouncer

PostgreSQL создаёт отдельный процесс операционной системы для каждого подключения. Каждый процесс потребляет ~10MB RAM.

```
Без PgBouncer:
app (500 workers) → 500 PostgreSQL backends → 500 * ~10MB = 5GB RAM

С PgBouncer:
app (500 workers) → PgBouncer :5432 → 20 PostgreSQL backends → 20 * ~10MB = 200MB

Transaction mode:
worker A → соединение занято только во время транзакции → возврат в пул
worker B → берёт то же соединение для следующей транзакции
```

Сценарий из реального production:

- приложение: 10 подов Kubernetes x 50 worker'ов = 500 одновременных соединений;
- при spike-нагрузке: 500 x 2 = 1000 соединений;
- без PgBouncer: 1000 процессов PostgreSQL по 10MB = 10GB RAM;
- с PgBouncer: 20-50 соединений к PostgreSQL = 200-500MB RAM.

PgBouncer принимает тысячи соединений от приложений и мультиплексирует их через небольшой пул соединений к PostgreSQL. Лишние запросы становятся в очередь и ждут освободившегося соединения.

## Три режима пулинга

PgBouncer поддерживает три режима работы.

### Session mode (сессионный)

- Соединение из пула выдаётся клиенту на всё время его сессии.
- После разрыва клиентского соединения — возврат в пул.
- = никакого пулинга на практике.
- client_idle_timeout — когда закрыть бездействующее клиентское соединение.

```ini
pool_mode = session
default_pool_size = 20
```

Использовать только для приложений которые не поддерживают transaction mode (используют временные таблицы, LISTEN/NOTIFY, SET сессионных параметров).

### Transaction mode (транзакционный) — рекомендуется

- Соединение выдаётся клиенту на время одной транзакции.
- После COMMIT или ROLLBACK соединение возвращается в пул.
- 500 воркеров могут делиться 20 соединениями.
- latency на открытие соединения практически отсутствует.

```ini
pool_mode = transaction
default_pool_size = 20
```

**Ограничения transaction mode:**

- Нельзя использовать `SET` (например, `SET search_path`) вне транзакции — изменения не сохранятся между транзакциями.
- `LISTEN` / `NOTIFY` не работают — уведомление придёт в одно из соединений пула, но не обязательно тому клиенту который слушает.
- Prepared statements по умолчанию не работают — нужно отключить их в приложении или добавить `prepare_threshold` в конфиг PgBouncer.
- `LOCK TABLE` вне транзакции — не сработает.

### Statement mode (статементный)

- Соединение на один запрос.
- После выполнения запроса — немедленный возврат в пул.
- Максимальная экономия соединений.

```ini
pool_mode = statement
default_pool_size = 10
```

Ограничения: подготовленные запросы не работают, курсоры не работают, временные таблицы не работают.

**Не использовать если не знаете зачем.** Для типичного веб-приложения transaction mode — правильный выбор.

## Установка PgBouncer

### Нативная установка

```bash
sudo apt install pgbouncer

# Проверить версию
pgbouncer --version
```

Конфигурационные файлы после установки:

```
/etc/pgbouncer/
├── pgbouncer.ini       # основной конфиг
└── userlist.txt        # список пользователей
```

### Запуск через Docker

```bash
docker run -d \
  --name pgbouncer \
  --restart unless-stopped \
  -p 6432:5432 \
  -e DATABASE_URL="postgres://appuser:password@postgres:5432/myapp" \
  -e POOL_MODE=transaction \
  -e MAX_CLIENT_CONN=1000 \
  -e DEFAULT_POOL_SIZE=20 \
  edoburu/pgbouncer
```

> ☠️ **Осторожно:** `DATABASE_URL` содержит пароль в открытом виде. В production использовать переменные окружения из секретов или Docker secrets.

## Конфигурация PgBouncer

### pgbouncer.ini

```ini
# /etc/pgbouncer/pgbouncer.ini

[databases]
# alias = host=... port=... dbname=... user=...
# Можно указать несколько БД
myapp = host=127.0.0.1 port=5432 dbname=myapp
myapp_ro = host=192.168.1.11 port=5432 dbname=myapp  # read replica

[pgbouncer]
# Адрес и порт для клиентов
listen_port = 6432          # PgBouncer слушает на 6432, не на 5432
listen_addr = 127.0.0.1     # только localhost

# Аутентификация
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

# Пулинг
pool_mode = transaction     # transaction mode — рекомендуется
default_pool_size = 20      # соединений к PostgreSQL (ядро пула)
max_client_conn = 1000      # соединений от приложений
reserve_pool_size = 5       # резерв для burst-нагрузки
reserve_pool_timeout = 5    # секунд — через столько подключается резерв

# Таймауты
server_idle_timeout = 600   # закрыть простаивающее серверное соединение через 10 мин
client_idle_timeout = 0     # не закрывать клиентские соединения (0 = отключено)
server_connect_timeout = 15 # таймаут на подключение к PostgreSQL

# Администрирование
admin_users = pgbouncer_admin
stats_users = monitoring

# Логирование
log_connections = 0
log_disconnections = 0
log_pooler_errors = 1
```

### userlist.txt

```text
# /etc/pgbouncer/userlist.txt
# Формат: "username" "хеш_пароля"

"appuser" "SCRAM-SHA-256$4096:..."
"monitoring" "SCRAM-SHA-256$4096:..."
```

Получить хеш пароля из PostgreSQL:

```sql
SELECT '"' || rolname || '" "' || rolpassword || '"'
FROM pg_authid
WHERE rolname IN ('appuser', 'monitoring');
```

### Применение изменений

```bash
# Перезагрузить конфигурацию
sudo systemctl reload pgbouncer

# или SIGTERM (не убивать!)
sudo killall -HUP pgbouncer
```

## PgBouncer в Docker Compose

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf:ro
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    shm_size: '256mb'
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d myapp"]
      interval: 10s
      retries: 5

  pgbouncer:
    image: edoburu/pgbouncer:latest
    container_name: pgbouncer
    restart: unless-stopped
    ports:
      - "127.0.0.1:6432:5432"   # PgBouncer на порту 6432
    environment:
      DATABASE_URL: "postgres://appuser:secret@postgres:5432/myapp"
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 1000
      DEFAULT_POOL_SIZE: 20
      AUTH_TYPE: scram-sha-256
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
```

Приложение подключается к `localhost:6432` вместо `localhost:5432`. Пароль и пользователь — те же что и для прямого подключения к PostgreSQL.

## Подключение приложения к PgBouncer

Строка подключения меняется только портом или хостом:

```bash
# Было (прямое подключение к PostgreSQL):
postgresql://appuser:secret@localhost:5432/myapp

# Стало (через PgBouncer):
postgresql://appuser:secret@localhost:6432/myapp
```

### Prepared statements и PgBouncer

Transaction mode не поддерживает prepared statements по умолчанию. Когда клиент подготавливает запрос (`PREPARE`), а затем выполняет его (`EXECUTE`), после COMMIT соединение возвращается в пул. Следующая транзакция может получить другое соединение, где этот prepared statement не существует.

Решения:

1. **Отключить prepared statements в приложении** (рекомендуется):
   - В PostgreSQL connection string: `postgresql://user:pass@host/db?prepareThreshold=0`
   - В приложении: отключить подготовленные запросы в ORM.

2. **Настроить PgBouncer для работы с prepared statements**:
   ```ini
   # pgbouncer.ini
   pkt_buf = 8192         # размер буфера для prepared statements
   max_prepared_statements = 100
   ```
   Но это увеличивает потребление памяти и не всегда стабильно.

## Мониторинг PgBouncer

PgBouncer предоставляет специальную базу данных `pgbouncer` для административных команд.

### Подключение к консоли

```bash
psql -U pgbouncer_admin -h 127.0.0.1 -p 6432 pgbouncer
```

Если пароль не задан — можно использовать `auth_type = trust` для админ-пользователя на localhost.

### SHOW POOLS — главная команда

```sql
SHOW POOLS;
```

Вывод:

```
 database | user    | cl_active | cl_waiting | sv_active | sv_idle | sv_used | maxwait
----------+---------+-----------+------------+-----------+---------+---------+---------
 myapp    | appuser | 45        | 3          | 20        | 0       | 0       | 0.5
 myapp_ro | appuser | 12        | 0          | 5         | 15      | 0       | 0
```

Что смотреть:

| Метрика | Что показывает | Тревога |
|---|---|---|
| `cl_active` | Активных клиентских соединений | > default_pool_size * 2 |
| `cl_waiting` | Клиентов в очереди (ждёт свободного серверного соединения) | > 0 постоянно |
| `sv_active` | Активных серверных соединений к PostgreSQL | = default_pool_size |
| `sv_idle` | Свободных серверных соединений | > 0 — хорошо |
| `maxwait` | Максимальное время ожидания в очереди (секунды) | > 1s |

**`cl_waiting > 0` постоянно** означает что PgBouncer не хватает серверных соединений. Увеличить `default_pool_size` или оптимизировать длительность транзакций.

**`maxwait > 1s`** — транзакции ждут соединения дольше секунды. Критично для веб-приложений.

### SHOW STATS

```sql
SHOW STATS;
```

Показывает статистику по запросам: сколько запросов выполнено, сколько байт передано, среднее время запроса.

### SHOW CLIENTS и SHOW SERVERS

```sql
-- Детали клиентских соединений
SHOW CLIENTS;

-- Детали серверных соединений к PostgreSQL
SHOW SERVERS;
```

Полезно когда нужно найти конкретное соединение по IP или времени подключения.

### Prometheus метрики PgBouncer

Для сбора метрик в Prometheus используйте `postgres_exporter` с Data Source Name указывающим на базу `pgbouncer`:

```yaml
services:
  pgbouncer-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    environment:
      DATA_SOURCE_NAME: "postgresql://monitoring:MonitorPass@pgbouncer:6432/pgbouncer?sslmode=disable"
    ports:
      - "9189:9187"
```

Метрики: `pgbouncer_pools_cl_active`, `pgbouncer_pools_cl_waiting`, `pgbouncer_pools_sv_active`, `pgbouncer_pools_maxwait`.

## PgBouncer sidecar в Kubernetes

В Kubernetes PgBouncer часто запускается как sidecar — один PgBouncer на под приложения. Это снижает latency (соединение локальное, без сетевых задержек) и упрощает конфигурацию.

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          image: myapp:latest
          env:
            - name: DATABASE_URL
              value: "postgresql://appuser:password@localhost:6432/myapp?prepareThreshold=0"
        - name: pgbouncer
          image: edoburu/pgbouncer:latest
          env:
            - name: DATABASE_URL
              value: "postgresql://appuser:password@postgres-service:5432/myapp"
            - name: POOL_MODE
              value: "transaction"
            - name: DEFAULT_POOL_SIZE
              value: "10"
            - name: MAX_CLIENT_CONN
              value: "100"
          ports:
            - containerPort: 6432
```

Сравнение подходов:

| Параметр | Sidecar PgBouncer | Централизованный PgBouncer |
|---|---|---|
| Latency | Минимальная (localhost) | + сетевая задержка |
| Конфигурация | Одна на под | Одна на кластер |
| Использование ресурсов | Выше (N подов x PgBouncer) | Ниже (один PgBouncer) |
| Управление | Сложнее (обновлять каждый под) | Проще (один сервис) |
| Изоляция | Полная (один tenant на PgBouncer) | Общий пул |

Для большинства случаев централизованный PgBouncer проще и эффективнее. Sidecar имеет смысл когда latency критична и каждый под обрабатывает тысячи запросов в секунду.

## Типичные ошибки

- **Transaction mode + prepared statements = ошибка.** Отключить prepared statements в приложении (`prepareThreshold=0` в connection string). Без этого приложение получает "prepared statement X does not exist".
- **Слишком большой `default_pool_size`.** 20-50 соединений достаточно для большинства приложений. 200 соединений нивелируют пользу от pooling (снова 2GB RAM).
- **`cl_waiting > 0` постоянно и не замечают.** Пул слишком мал. Увеличить `default_pool_size` или оптимизировать длинные транзакции.
- **PgBouncer в transaction mode + `SET search_path`.** SET не сохраняется между транзакциями. Использовать `ALTER USER ... SET search_path = ...` на уровне PostgreSQL.
- **Не менять `max_connections` в PostgreSQL после установки PgBouncer.** Если раньше было 500 соединений — можно уменьшить до 50 (20 + 5 резерв + запас для админов). PostgreSQL ставится легче.
- **Забыть про `auth_type`.** Если auth_type в pgbouncer.ini отличается от метода в pg_hba.conf — подключение не пройдёт. Рекомендуется везде `scram-sha-256`.
- **PgBouncer на том же сервере что PostgreSQL без ограничения listen_addr.** По умолчанию PgBouncer слушает на всех интерфейсах — ограничить `listen_addr = 127.0.0.1`.

## Чек-лист для самопроверки

- [ ] Понимаю почему большое число соединений убивает PostgreSQL (процесс ~10MB на соединение)
- [ ] Знаю разницу между session, transaction и statement mode
- [ ] Умею настроить PgBouncer и подключить к нему приложение
- [ ] Умею читать `SHOW POOLS` — найти `cl_waiting` и `maxwait`
- [ ] Настроил мониторинг PgBouncer в Prometheus
- [ ] Отключил prepared statements в приложении или настроил PgBouncer для их поддержки
- [ ] Уменьшил `max_connections` в PostgreSQL после установки PgBouncer
- [ ] Знаю trade-off между sidecar и централизованным PgBouncer в Kubernetes

## Попробуйте сами

1. Запустите PostgreSQL и PgBouncer в Docker Compose. Подключитесь к PgBouncer через psql на порту 6432. Выполните несколько запросов. Проверьте `SHOW POOLS` — видите активные соединения.

2. Создайте нагрузку: 100 параллельных подключений к PgBouncer (`pgbench -U appuser -h 127.0.0.1 -p 6432 -c 100 -j 4 -T 30 pgbouncer_dsn`). Во время выполнения откройте второе окно и смотрите `SHOW POOLS` — сколько `cl_active`, `sv_active`, есть ли `cl_waiting`?

3. Посмотрите `pg_stat_activity` на PostgreSQL во время нагрузки через PgBouncer. Убедитесь что соединений к PostgreSQL (20) значительно меньше чем клиентов к PgBouncer (100).

4. Намеренно создайте ситуацию когда пул исчерпан: выполните `BEGIN; SELECT pg_sleep(60);` в 25 соединениях одновременно. Посмотрите `SHOW POOLS` — `cl_waiting` растёт, `maxwait` увеличивается. Отмените долгие транзакции (`pg_terminate_backend` на уровне PostgreSQL) — очередь рассасывается.
