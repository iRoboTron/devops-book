# Глава 7: Exporters — PostgreSQL, Nginx, Redis, Blackbox

## Что вы узнаете

- концепция exporter: любой сервис можно мониторить через Prometheus;
- postgres_exporter: ключевые метрики БД;
- nginx-prometheus-exporter: RPS, ошибки, соединения;
- redis_exporter: память, команды, hit rate;
- blackbox_exporter: проверка URL, TCP-портов, DNS, ICMP.

**Цель:** читатель добавляет мониторинг любого сервиса из списка за 15 минут.

---

## Концепция exporter

Prometheus снимает метрики через HTTP-эндпоинт `/metrics` в формате plain text. Но большинство сервисов (PostgreSQL, Nginx, Redis) не имеют встроенного `/metrics`. **Exporter** — это прокси между Prometheus и сервисом.

```text
Prometheus ──► GET :9187/metrics ──► postgres_exporter ──► PostgreSQL SQL queries
Prometheus ──► GET :9113/metrics ──► nginx_exporter    ──► Nginx stub_status
Prometheus ──► GET :9121/metrics ──► redis_exporter    ──► Redis INFO
```

Exporter:
- опрашивает сервис через его родной протокол (SQL, HTTP, Redis командой);
- преобразует ответ в Prometheus-метрики (gauge, counter, histogram);
- отдаёт метрики на HTTP-порту в формате `/metrics`.

Большинство exporter-ов написаны сообществом и поддерживаются в Prometheus ecosystem. Официальный список: https://prometheus.io/docs/instrumenting/exporters/

---

## postgres_exporter

PostgreSQL не имеет встроенного `/metrics`. `postgres_exporter` подключается к БД через SQL и выполняет запросы к системным таблицам (`pg_stat_activity`, `pg_database`, `pg_stat_database`).

### docker-compose.yml

```yaml
  postgres_exporter:
    image: prometheuscommunity/postgres-exporter:v0.15.0
    container_name: postgres_exporter
    restart: unless-stopped
    environment:
      DATA_SOURCE_NAME: "postgresql://monitoring:MonitorPass@postgres:5432/postgres?sslmode=disable"
    ports:
      - "127.0.0.1:9187:9187"
    networks:
      - monitoring
```

Перед запуском создайте пользователя в PostgreSQL:

```sql
CREATE USER monitoring WITH PASSWORD 'MonitorPass';
ALTER USER monitoring WITH SUPERUSER;
```

> ☠️ **Осторожно:** Пароль передаётся через переменную окружения — он виден в `docker inspect`. Для production используйте Docker secrets или файл с паролем.

### Ключевые метрики

**Активные соединения**

```promql
# Все соединения
pg_stat_activity_count

# Соединения по состоянию
pg_stat_activity_count{state="active"}
pg_stat_activity_count{state="idle in transaction"}  # тревога если > 5
```

`idle in transaction` означает что клиент открыл транзакцию и не завершает её. Если таких соединений много — они блокируют автовакуум и приводят к росту dead tuples.

**Размер базы данных**

```promql
# Размер каждой БД в байтах
pg_database_size_bytes

# Суммарный размер всех БД
sum(pg_database_size_bytes)
```

**Replication lag**

```promql
# Отставание реплики в байтах WAL
pg_replication_lag
```

Если replica lag растёт — реплика не успевает применять изменения с мастера. Критично для чтения актуальных данных с реплик.

**Cache hit ratio**

```promql
rate(pg_stat_database_blks_hit[5m])
  / (rate(pg_stat_database_blks_hit[5m]) + rate(pg_stat_database_blks_read[5m]))
```

Cache hit ratio — процент обращений к данным которые нашлись в shared buffers (кэш PostgreSQL). Значение > 99% отлично, < 95% — нужно увеличить `shared_buffers`.

**Другие полезные метрики:**

```promql
# Количество dead tuples (нуждаются в vacuum)
pg_stat_user_tables_n_dead_tup

# Количество транзакций в секунду
rate(pg_stat_database_xact_commit[5m])

# Длительность запросов (требует pg_stat_statements)
pg_stat_statements_mean_time_seconds
```

---

## nginx_exporter

Nginx сам по себе не отдаёт метрики в Prometheus формате. В Nginx есть встроенная страница `stub_status` — nginx_exporter читает её и преобразует в метрики.

### Настройка stub_status в Nginx

Добавьте в конфигурацию Nginx:

```nginx
server {
    listen 8080;
    location /stub_status {
        stub_status;
        allow 127.0.0.1;
        deny all;
    }
}
```

> ☠️ **Осторожно:** stub_status показывает метрики о всех соединениях — количество активных, принятых, обработанных. Никогда не открывайте `stub_status` наружу. Всегда `allow 127.0.0.1; deny all;`. Если ошиблись — любой может узнать RPS вашего сервиса.

### docker-compose.yml

```yaml
  nginx_exporter:
    image: nginx/nginx-prometheus-exporter:1.1.0
    container_name: nginx_exporter
    restart: unless-stopped
    command:
      - '--nginx.scrape-uri=http://nginx:8080/stub_status'
    ports:
      - "127.0.0.1:9113:9113"
    networks:
      - monitoring
```

### Ключевые метрики

```promql
# Активные соединения
nginx_connections_active

# Всего запросов (Counter)
nginx_http_requests_total

# RPS — запросов в секунду
rate(nginx_http_requests_total[5m])

# Соединения по состоянию
nginx_connections_accepted   # принято всего
nginx_connections_handled    # обработано (если != accepted — ошибка)
nginx_connections_reading    # читает запрос
nginx_connections_writing    # пишет ответ
nginx_connections_waiting    # keepalive, ожидание
```

Соотношение `accepted / handled` — важный показатель: если accepted > handled, Nginx не справляется (не хватает worker_connections).

---

## redis_exporter

Redis также не имеет `/metrics`. `redis_exporter` выполняет команду `INFO` и обрабатывает её вывод.

### docker-compose.yml

```yaml
  redis_exporter:
    image: oliver006/redis_exporter:v1.58.0
    container_name: redis_exporter
    restart: unless-stopped
    environment:
      REDIS_ADDR: "redis://redis:6379"
    ports:
      - "127.0.0.1:9121:9121"
    networks:
      - monitoring
```

### Ключевые метрики

```promql
# Использование памяти
redis_memory_used_bytes              # занято
redis_memory_max_bytes               # лимит (maxmemory)
redis_memory_used_bytes / redis_memory_max_bytes * 100  # % от лимита

# Команды в секунду
rate(redis_commands_total[5m])

# Hit rate (сколько запросов в кэш попали)
rate(redis_keyspace_hits_total[5m])
  / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))

# Количество ключей по БД
redis_db_keys

# Соединения
redis_connected_clients
redis_rejected_connections_total   # превышен maxclients
```

---

## Blackbox exporter — проверка доступности

Blackbox exporter занимает особое место: он не опрашивает внутренний сервис, а **проверяет внешние эндпоинты** — HTTP-URL, TCP-порт, ICMP (ping), DNS.

Prometheus не может сам сделать HTTP-запрос к `https://google.com` — он только снимает `/metrics` с известных таргетов. Blackbox exporter решает эту задачу: Prometheus говорит «проверь этот URL», Blackbox делает запрос и отдаёт результат в метриках.

### Модули blackbox.yml

```yaml
# blackbox/blackbox.yml
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_status_codes: [200, 201, 204]
      method: GET
      fail_if_ssl: false
      fail_if_not_ssl: false

  tcp_connect:
    prober: tcp
    timeout: 5s

  icmp_ping:
    prober: icmp
    timeout: 10s
    icmp:
      preferred_ip_protocol: ip4
```

### docker-compose.yml

```yaml
  blackbox_exporter:
    image: prom/blackbox-exporter:v0.24.0
    container_name: blackbox_exporter
    restart: unless-stopped
    volumes:
      - ./blackbox/blackbox.yml:/etc/blackbox_exporter/config.yml:ro
    ports:
      - "127.0.0.1:9115:9115"
    networks:
      - monitoring
```

### Конфигурация Prometheus для Blackbox

```yaml
  - job_name: 'blackbox_http'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - https://myapp.example.com
          - https://api.example.com/health
          - https://google.com
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox_exporter:9115

  - job_name: 'blackbox_tcp'
    metrics_path: /probe
    params:
      module: [tcp_connect]
    static_configs:
      - targets:
          - postgres:5432
          - nginx:80
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox_exporter:9115

  - job_name: 'blackbox_icmp'
    metrics_path: /probe
    params:
      module: [icmp_ping]
    static_configs:
      - targets:
          - 8.8.8.8
          - 1.1.1.1
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox_exporter:9115
```

### Ключевые метрики

```promql
# Доступен ли URL (1 = да, 0 = нет)
probe_success{job="blackbox_http"}

# Время ответа (в секундах)
probe_duration_seconds

# Дней до истечения SSL-сертификата
(probe_ssl_earliest_cert_expiry - time()) / 86400

# Статус код HTTP
probe_http_status_code

# DNS резолв (время)
probe_dns_lookup_time_seconds

# Потеря пакетов при ICMP (0..1)
probe_icmp_duration_seconds  # если 0 — пакет потерян
```

---

## Synthetic monitoring — валидация ответа API

Blackbox может не просто проверять «статус код 200», а валидировать содержимое ответа. Это называется **synthetic monitoring** — симуляция реального запроса пользователя.

### Модуль http_json_ok

```yaml
  http_json_ok:
    prober: http
    timeout: 10s
    http:
      valid_status_codes: [200]
      fail_if_body_not_matches_regexp:
        - '"status":\s*"ok"'
```

Этот модуль:
1. Делает GET-запрос к URL;
2. Проверяет что статус код 200;
3. Проверяет что тело ответа содержит `"status": "ok"` (с гибким пробелом).

### prometheus.yml для json модуля

```yaml
  - job_name: 'blackbox_json'
    metrics_path: /probe
    params:
      module: [http_json_ok]
    static_configs:
      - targets:
          - https://myapi.example.com/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox_exporter:9115
```

### Когда это нужно

- health endpoint вашего приложения который возвращает `{"status":"ok"}`;
- API gateway — проверить что gateway отвечает и не возвращает ошибку;
- проверка что сервис прошёл инициализацию (не просто запущен, а готов принимать запросы);
- мониторинг upstream статусов через обратный прокси (например nginx возвращает 200, но бэкенд упал).

> ☠️ **Осторожно:** Регулярное выражение должно совпадать именно с частью тела ответа. Если API возвращает `{"status": "ok", "code": 200}` — паттерн `"status":\s*"ok"` сработает. Но если JSON отформатирован с переносами строк — регулярка может не сработать. Тестируйте модуль на реальном ответе API.

### Дополнительные fail_conditions

```yaml
  http_json_check:
    prober: http
    timeout: 10s
    http:
      valid_status_codes: [200, 201]
      fail_if_body_matches_regexp:
        - "error"
        - "timeout"
      fail_if_header_missing:
        - "X-API-Version"
```

Этот модуль проверяет: статус 200 или 201, в теле нет слов `error`/`timeout`, присутствует заголовок `X-API-Version`.

---

## Альтернативы Prometheus для малых команд

### Uptime Kuma

Uptime Kuma — простой UI-based мониторинг для HTTP/TCP/DNS. Не требует PromQL. Подходит когда задача «просто проверить что сайт работает».

Плюсы:
- Запускается в одном контейнере;
- Веб-интерфейс с дашбордом;
- Уведомления в Telegram, email, Slack из коробки;
- Не нужно писать конфиги YAML.

Минусы:
- Нет гибких метрик — только up/down и latency;
- Не хранит историю для анализа трендов;
- Нельзя строить сложные дашборды.

### Netdata

Агентный мониторинг который даёт тысячи метрик из коробки (CPU, память, диск, сеть, PostgreSQL, Nginx). Дашборд сразу после установки.

Плюсы:
- Ставится на хост одной командой (`bash <(curl -Ss https://my-netdata.io/kickstart.sh)`);
- Сотни предустановленных дашбордов;
- Низкое потребление ресурсов;
- Поддержка exporters — может экспортировать метрики в Prometheus.

Минусы:
- Меньше гибкости в кастомизации запросов;
- Визуализация привязана к Netdata UI (хотя есть Prometheus remote write).

**Выбор:** Prometheus даёт максимальную гибкость и единый стек. Netdata быстрее запустить и проще для первичного мониторинга. Для курса мы строим стек на Prometheus — это универсальное решение которое работает везде.

---

## Типичные ошибки

- Blackbox exporter запускается в Docker, но проверяет `localhost` — он проверяет себя, а не хост. Для проверки сервисов на хосте используйте IP хоста (например `172.17.0.1` или host.docker.internal) или DNS-имя сервиса.
- Nginx stub_status открыт без ограничений по IP — любой может посмотреть статистику. Всегда `allow 127.0.0.1; deny all;`.
- `DATA_SOURCE_NAME` postgres_exporter в env виден в `docker inspect`. Использовать Docker secrets или файл с паролем.
- redis_exporter без пароля — если Redis требует `AUTH`, нужно передавать пароль через `REDIS_PASSWORD` или в `REDIS_ADDR: redis://:password@redis:6379`.
- Blackbox проверяет HTTPS но не проверяет SSL-сертификат — `fail_if_ssl: false` пропускает истекшие сертификаты. Для production установите `fail_if_not_ssl: true` и настройте алерт на `probe_ssl_earliest_cert_expiry`.
- postgres_exporter без прав SUPERUSER — часть метрик (`pg_replication_lag`, `pg_stat_database`) требует повышенных прав.
- Забыть relabel_configs для Blackbox — Prometheus будет стучаться на blackbox_exporter:9115 вместо целевого URL.

---

## Чек-лист для самопроверки

- [ ] Понимаю что exporter — это прокси между Prometheus и сервисом
- [ ] Добавил postgres_exporter и вижу метрики БД
- [ ] Настроил Blackbox exporter для проверки доступности URL
- [ ] Знаю как отслеживать срок истечения SSL через `probe_ssl_earliest_cert_expiry`
- [ ] stub_status защищён `allow/deny`
- [ ] Пароль postgres_exporter не передаётся в открытом виде
- [ ] Могу написать модуль Blackbox для проверки JSON-ответа

---

## Попробуйте сами

1. Запустите postgres_exporter. В Prometheus найдите метрику `pg_up` — значение должно быть 1. Остановите PostgreSQL (`docker stop postgres`). Через 30 секунд `pg_up` стало 0? Это и есть мониторинг БД. Запустите PostgreSQL обратно.

2. Настройте Blackbox для проверки `https://google.com`. Найдите `probe_ssl_earliest_cert_expiry`. Посчитайте сколько дней до истечения сертификата: `(probe_ssl_earliest_cert_expiry - time()) / 86400`.

3. Добавьте в Blackbox проверку несуществующего URL (например `https://example.com/nonexistent`). `probe_success` = 0. Это будущий алерт «сайт недоступен».

4. Создайте модуль Blackbox `http_json_ok` который проверяет что API возвращает `{"status":"ok"}`. Если у вас нет тестового API — используйте https://httpbin.org/status/200 (он вернёт пустой ответ — probe_success будет 0, что и демонстрирует что валидация сработала).

5. Запустите Nginx с stub_status. Найдите `nginx_connections_active` когда никто не стучится (должно быть около 1-2). Затем выполните `ab -n 100 -c 10 http://nginx/` (Apache Bench) и наблюдайте рост `nginx_connections_active` и `nginx_http_requests_total`.
