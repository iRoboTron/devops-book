# Глава 2: Prometheus — концепции, метрики, конфигурация

## Что вы узнаете

- как Prometheus хранит данные: time series и labels;
- Pull vs Push — почему Prometheus сам приходит за метриками;
- четыре типа метрик: Counter, Gauge, Histogram, Summary;
- полный синтаксис `prometheus.yml`: scrape_configs, relabeling, file_sd;
- как добавить новый таргет и перезагрузить конфиг без рестарта.

Цель главы: вы понимаете модель данных Prometheus и можете добавить любой новый таргет в конфиг за 2 минуты.

---

## Pull vs Push модель

Prometheus работает по pull-модели — он сам опрашивает таргеты по расписанию. Это принципиальное отличие от многих других систем мониторинга.

```
Pull (Prometheus):
Prometheus ──► GET /metrics ──► Exporter
«Prometheus сам приходит за метриками по расписанию»
+ Prometheus знает что таргет недоступен (нет ответа = алерт)
- Нужен сетевой доступ от Prometheus к каждому таргету

Push (Pushgateway / Loki / StatsD):
Приложение ──► POST метрик ──► Приёмник
«Приложение само отправляет метрики»
+ Подходит для batch jobs (нет постоянного endpoint)
- Prometheus не знает упало ли приложение (оно просто перестало пушить)
```

Pull-модель даёт ключевое преимущество: если сервис упал, Prometheus не получает ответ на запрос `/metrics` и немедленно видит что таргет недоступен. В push-модели вы никогда не знаете — сервис упал или просто нет метрик.

Pull нужен для постоянно работающих сервисов (веб-сервер, база данных, Node Exporter). Push — только для batch-задач (скрипты бэкапа, cron-задания) через Pushgateway (Глава 10).

---

## Модель данных: time series и labels

Метрика в Prometheus — это не просто число. Это **временной ряд (time series)**: имя + набор labels + значение + timestamp.

```
Метрика = имя + набор labels + значение + timestamp
```

Одна метрика `node_cpu_seconds_total` порождает множество time series — по одному на каждую комбинацию labels:

```text
node_cpu_seconds_total{cpu="0", mode="idle"}        -> 12345.6
node_cpu_seconds_total{cpu="0", mode="user"}        -> 234.5
node_cpu_seconds_total{cpu="0", mode="system"}      -> 67.8
node_cpu_seconds_total{cpu="0", mode="iowait"}      -> 12.3
node_cpu_seconds_total{cpu="1", mode="idle"}        -> 11987.3
node_cpu_seconds_total{cpu="1", mode="user"}        -> 198.4
node_cpu_seconds_total{cpu="1", mode="system"}      -> 45.6
node_cpu_seconds_total{cpu="1", mode="iowait"}      -> 3.2
```

**Каждая уникальная комбинация labels — отдельный time series.** Для 4 CPU и 8 режимов = 32 time series только для одной метрики.

Labels — это метаданные по которым вы фильтруете и группируете данные:

```promql
# Все CPU в режиме idle
node_cpu_seconds_total{mode="idle"}

# Конкретный CPU
node_cpu_seconds_total{cpu="0"}

# Регулярное выражение: режимы user или system
node_cpu_seconds_total{mode=~"user|system"}
```

> ☠️ **Осторожно:** Labels с высокой кардинальностью (например, `user_id`, `request_id`, `ip_address` как label) создают миллионы time series. Prometheus хранит каждый time series в памяти. 10 миллионов time series = 10+ ГБ RAM и гарантированный OOM. Labels должны иметь небольшое число уникальных значений (десятки, не миллионы).

---

## Типы метрик

Prometheus поддерживает четыре типа метрик. Понимание типов — ключ к правильным запросам.

```text
Тип           Описание                         Пример
────────────────────────────────────────────────────────────────────
Counter       Только растёт. Сбрасывается      http_requests_total
              при рестарте.                    errors_total
              -> используй rate() для скорости

Gauge         Текущее значение. Растёт и       memory_used_bytes
              убывает.                         cpu_usage_percent
              -> используй напрямую            active_connections

Histogram     Распределение значений.          http_request_duration_seconds
              _bucket, _sum, _count.           (99-й перцентиль задержки)
              -> используй histogram_quantile()

Summary       Перцентили на стороне клиента.   go_gc_duration_seconds
              Менее гибкий чем Histogram.
              -> использовать редко, prefer Histogram
```

### Counter

Только увеличивается. Сбрасывается в ноль при перезапуске процесса. Используется для счётчиков событий: количество запросов, ошибок, байт переданных по сети.

```promql
# Бессмысленно: текущее значение счётчика (например, 1 234 567)
http_requests_total

# Правильно: скорость запросов в секунду
rate(http_requests_total[5m])

# Правильно: прирост за последний час
increase(http_requests_total[1h])
```

### Gauge

Может расти и убывать. Текущее значение в конкретный момент времени. Используется для показателей состояния: температура, загрузка CPU, занятая память.

```promql
# Имеет смысл напрямую
node_memory_MemAvailable_bytes
cpu_temperature_celsius
active_connections
```

### Histogram

Измеряет распределение значений. Экспортирует три группы метрик:
- `_bucket{le="..."}` — количество событий попадающих в интервал
- `_sum` — сумма всех значений
- `_count` — количество событий

```promql
# P99 задержки HTTP-запросов
histogram_quantile(0.99, sum by(le) (rate(http_request_duration_seconds_bucket[5m])))

# Средняя задержка
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

### Summary

Похож на Histogram, но перцентили вычисляются на стороне приложения, а не в PromQL. Менее гибок — нельзя агрегировать по разным инстансам. Используйте Histogram если не уверены.

---

## Формат /metrics endpoint

Prometheus ожидает от таргетов определённый формат метрик. Посмотрите на реальный вывод Node Exporter:

```bash
curl -s http://localhost:9100/metrics | head -30
```

Результат:

```text
# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode.
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{cpu="0",mode="idle"} 12345.67
node_cpu_seconds_total{cpu="0",mode="user"} 234.56
node_cpu_seconds_total{cpu="0",mode="system"} 45.67
node_cpu_seconds_total{cpu="1",mode="idle"} 11987.34

# HELP node_memory_MemFree_bytes Memory information field MemFree_bytes.
# TYPE node_memory_MemFree_bytes gauge
node_memory_MemFree_bytes 1073741824

# HELP node_disk_reads_completed_total The total number of reads completed successfully.
# TYPE node_disk_reads_completed_total counter
node_disk_reads_completed_total{device="sda"} 123456
node_disk_reads_completed_total{device="sdb"} 78901
```

Формат строки:

```text
# HELP имя_метрики описание          — комментарий, необязателен
# TYPE имя_метрики тип              — объявление типа
имя_метрики{label="значение"} число  — значение с метками
```

Найти конкретную метрику:

```bash
curl -s http://localhost:9100/metrics | grep "^node_memory_MemAvailable"
```

Каждый exporter отдаёт метрики в этом формате. Prometheus парсит `/metrics`, извлекает имена, метки, значения и сохраняет их в свою базу временных рядов.

---

## Полный prometheus.yml с объяснениями

```yaml
# prometheus/prometheus.yml

global:
  # Как часто опрашивать таргеты
  scrape_interval: 15s

  # Сколько ждать ответа от таргета (должно быть меньше scrape_interval)
  scrape_timeout: 10s

  # Как часто вычислять recording rules и alert rules
  evaluation_interval: 15s

  # Метки которые добавляются ко всем метрикам этого Prometheus
  external_labels:
    cluster: 'production'
    region: 'ru-msk'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/rules/*.yml'

scrape_configs:
  # Мониторинг самого Prometheus
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Метрики сервера через Node Exporter
  - job_name: 'node'
    static_configs:
      - targets:
          - 'node_exporter:9100'

  # Пример: мониторинг приложения
  - job_name: 'myapp'
    metrics_path: '/metrics'      # путь (по умолчанию /metrics)
    scheme: 'http'                # http или https
    scrape_interval: 30s          # переопределить global для этого job
    static_configs:
      - targets:
          - 'app1:8080'
          - 'app2:8080'
        labels:
          environment: 'production'   # добавить label ко всем метрикам

  # Динамическое обнаружение через file_sd (из JSON-файлов)
  - job_name: 'dynamic-targets'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/*.json'
        refresh_interval: 30s
```

### Ключевые параметры global

- **scrape_interval** — как часто Prometheus опрашивает таргеты. 15s — хороший баланс для большинства задач. Для критических сервисов можно 5-10s.
- **scrape_timeout** — максимальное время ожидания ответа. Если таргет не ответил за 10s — ошибка. Всегда меньше `scrape_interval`.
- **evaluation_interval** — частота вычисления правил алертов. Влияет на скорость срабатывания алертов.
- **external_labels** — глобальные метки которые добавляются к каждой метрике. Полезны когда несколько Prometheus шлют данные в общее хранилище.

### Ключевые параметры scrape_config

- **job_name** — логическое имя группы таргетов. Добавляется как метка `job` к каждой метрике.
- **metrics_path** — путь к `/metrics` endpoint (по умолчанию `/metrics`).
- **scrape_interval** — переопределить глобальный интервал для конкретного job (если один сервис нужно опрашивать чаще).
- **static_configs.targets** — список адресов `host:port`.
- **static_configs.labels** — метки которые добавляются ко всем метрикам этого таргета. Используются для идентификации окружения, команды, дата-центра.

---

## Добавить таргет и проверить

Добавление нового таргета — самая частая операция. Алгоритм:

```bash
# 1. Добавить секцию в scrape_configs prometheus.yml
# 2. Перезагрузить конфиг без рестарта контейнера:
curl -X POST http://localhost:9090/-/reload

# 3. Проверить в UI:
# http://localhost:9090/targets -> найти новый job
# Status: UP = всё работает
# Status: DOWN = ошибка (смотреть поле Error)
```

Для перезагрузки через `/-/reload` нужен флаг `--web.enable-lifecycle`. Он уже добавлен в `docker-compose.yml` из Главы 1.

Частые причины статуса DOWN:

```text
connection refused            -> сервис не запущен или неверный порт
context deadline exceeded     -> таргет не отвечает за scrape_timeout
404                           -> неверный metrics_path (не /metrics)
dial tcp: lookup              -> DNS имя не разрешается (опечатка в имени)
```

Пример: добавьте несуществующий таргет и посмотрите как выглядит ошибка:

```yaml
  - job_name: 'test-down'
    static_configs:
      - targets: ['fake:9999']
```

После `curl -X POST /-/reload` этот таргет появится в Targets со статусом DOWN и описанием `connection refused`.

---

## Файловое обнаружение сервисов (file_sd)

Когда серверов становится больше двух, редактировать `prometheus.yml` для каждого нового таргета неудобно. `file_sd_configs` позволяет вынести таргеты в отдельные JSON-файлы — Prometheus читает их и обновляет список без рестарта.

```json
// /etc/prometheus/targets/servers.json
[
  {
    "targets": ["server1:9100", "server2:9100"],
    "labels": {"env": "prod", "team": "backend"}
  },
  {
    "targets": ["server3:9100"],
    "labels": {"env": "staging"}
  }
]
```

```yaml
# prometheus.yml
  - job_name: 'nodes-file-sd'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/*.json'
        refresh_interval: 30s
```

Prometheus проверяет файлы каждые `refresh_interval` секунд. Если файл изменился — список таргетов обновляется без `/-/reload`.

Преимущества:

- Новый сервер = новый файл или строка в JSON. Не нужно трогать `prometheus.yml`.
- Файлы можно генерировать скриптом (например, из Ansible инвентори или облачного API).
- Разные файлы для разных групп серверов: `backend.json`, `frontend.json`, `staging.json`.

Для Docker-среды путь к файлам будет `./prometheus/targets/*.json` (монтируется в `/etc/prometheus/targets/`).

```bash
# Создать файл с таргетами
mkdir -p prometheus/targets
cat > prometheus/targets/servers.json << 'EOF'
[
  {"targets": ["myserver:9100"], "labels": {"env": "prod"}}
]
EOF

# Добавить file_sd_configs в prometheus.yml
# Подождать 30 секунд — новый таргет появится в Targets
```

---

## Типичные ошибки

- **scrape_timeout больше scrape_interval.** Prometheus выдаст ошибку при старте. `scrape_timeout` должен быть строго меньше `scrape_interval` (например, 10s и 15s).

- **Labels с высокой кардинальностью.** `user_id`, `request_id`, `email`, `ip_address` как метки — каждый новый пользователь создаёт новый time series. 10 000 пользователей = 10 000 time series на одну метрику. Prometheus упадёт по памяти. Labels — для ограниченного набора значений (десятки), не для уникальных идентификаторов.

- **Не добавлен `--web.enable-lifecycle`.** `curl -X POST /-/reload` возвращает 404. Без этого флага перезагрузка конфига требует полного рестарта Prometheus. В production рестарт = потеря метрик на время остановки.

- **Путать `localhost` и имя контейнера.** В `docker-compose.yml` Node Exporter называется `node_exporter`. В `prometheus.yml` нужно писать `node_exporter:9100`, а не `localhost:9100`. localhost внутри контейнера Prometheus — это сам контейнер Prometheus, а не хост.

- **Не проверять `/targets` после добавления.** Добавил новый таргет, перезагрузил конфиг, забыл проверить. Через неделю оказалось что таргет DOWN с первого дня — метрик нет, мониторинг не работает. Всегда проверяйте `http://localhost:9090/targets` после изменений.

---

## Чек-лист для самопроверки

- [ ] Понимаю что time series = имя метрики + уникальный набор labels.
- [ ] Знаю все 4 типа метрик: Counter (только рост, нужен rate), Gauge (текущее значение), Histogram (распределение, перцентили), Summary (редко).
- [ ] Умею добавить таргет в `prometheus.yml` и проверить его статус в UI `/targets`.
- [ ] Умею перезагрузить конфиг без рестарта через `curl -X POST /-/reload`.
- [ ] Понимаю что `localhost` в Docker-контейнере — это сам контейнер, а не хост.
- [ ] Знаю что `file_sd_configs` позволяет добавлять таргеты через JSON-файлы без редактирования `prometheus.yml`.

---

## Попробуйте сами

1. Откройте `http://localhost:9100/metrics` в браузере или через curl. Найдите 3 метрики разных типов (counter, gauge). По названию и `# HELP` догадайтесь что они измеряют. Проверьте догадку через PromQL-запрос в Prometheus UI.

2. Добавьте в `prometheus.yml` таргет с несуществующим адресом:
   ```yaml
   - job_name: 'test-down'
     static_configs:
       - targets: ['fake:9999']
   ```
   Перезагрузите конфиг: `curl -X POST http://localhost:9090/-/reload`. Найдите его в http://localhost:9090/targets — статус DOWN и описание ошибки. Удалите таргет когда наглядетесь.

3. Создайте файл `prometheus/targets/extra.json` с одним таргетом:
   ```json
   [{"targets": ["localhost:9090"], "labels": {"source": "extra"}}]
   ```
   Добавьте `file_sd_configs` в `prometheus.yml` (секция `job_name: 'extra-nodes'` с `file_sd_configs` указывающим на `/etc/prometheus/targets/*.json`). Подождите 30 секунд. Появился ли новый таргет в Targets без перезагрузки Prometheus?

4. Откройте http://localhost:9090/status. Посмотрите сколько time series хранит ваш Prometheus (`TSDB Status → Head series`). Это число будет расти с добавлением новых таргетов. Если видите резкий скачок без добавления таргетов — проверьте нет ли утечки кардинальности.
