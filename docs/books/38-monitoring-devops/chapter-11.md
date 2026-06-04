# Глава 11: Масштабирование и long-term storage

## Что вы узнаете

- сколько данных реально хранит Prometheus и как управлять размером;
- что делать если 15 дней хранения недостаточно;
- как настроить Remote Write в VictoriaMetrics для хранения метрик 12 месяцев;
- когда одного Prometheus достаточно, а когда нужны несколько;
- как хранить алерты и дашборды в Git через Grafana provisioning;
- как добавить рендеринг PNG-скриншотов в алерты через grafana-image-renderer.

**Цель:** вы знаете границы одного Prometheus и умеете их расширять без перехода на K8s-стеки.

---

## Сколько данных хранит один Prometheus

### Расчёт объёма

Prometheus хранит каждую точку данных (sample) примерно в 1-2 байта на диске с учётом сжатия. Формула грубой оценки:

```text
количество_метрик × количество_samples_в_секунду × retention_секунд × 1.5 байта

Пример для 100 метрик при scrape_interval=15s и retention=15d:
100 × (1/15) × (15 × 24 × 3600) × 1.5 ≈ 100 × 5760 × 1.5 ≈ 864 000 байт ≈ 0.86 MB
```

На практике с учётом индекса, WAL и метаданных:

| Метрик | Scrape | Retention | Размер на диске |
|--------|--------|-----------|-----------------|
| 100 | 15s | 15d | ~100-150 MB |
| 1 000 | 15s | 15d | ~1-1.5 GB |
| 10 000 | 15s | 15d | ~10-15 GB |
| 10 000 | 15s | 90d | ~60-90 GB |

```bash
# Реальный размер данных вашего Prometheus
docker exec prometheus du -sh /prometheus

# Количество активных time series
# http://localhost:9090/graph
prometheus_tsdb_head_series
```

### Retention по умолчанию

Prometheus хранит данные 15 дней. Это значение по умолчанию, и для большинства DevOps-задач его достаточно:

- вы видите что сломалось сейчас (график за последние часы);
- вы видите когда началась проблема (график за несколько дней);
- тренды (рост памяти за неделю).

Когда 15 дней мало:

- «что было месяц назад до последнего релиза?»;
- сравнение метрик год к году для планирования ресурсов;
- compliance / аудит — нужно хранить данные 6-12 месяцев;
- расследование инцидента после того как данные уже вышли за retention.

```bash
# Изменить retention (при запуске)
--storage.tsdb.retention.time=30d    # 30 дней
--storage.tsdb.retention.size=50GB   # или не больше 50 GB
```

> ☠️ **Осторожно:** Не увеличивайте retention Prometheus без контроля размера диска. `--storage.tsdb.retention.time=1y` при 10 000 метрик заполнит ~60-90 GB. Если на разделе мало места — Prometheus упадёт с ошибкой «no space left on device» или по OOM при старте после перезапуска.

---

## Remote Write в VictoriaMetrics

Когда retention Prometheus (15 дней) недостаточен, правильное решение — не увеличивать retention в Prometheus, а настроить Remote Write во внешнее хранилище.

```text
┌──────────┐     Remote Write     ┌──────────────────┐
│          │ ──────────────────►  │                  │
│ Prometheus│   метрики в реальном│  VictoriaMetrics  │
│ (15 дней)│   времени           │  (12-24 месяца)   │
│          │                     │                  │
└──────────┘                     └──────────────────┘
      │                                │
      ▼                                ▼
  Grafana дашборды               Long-term запросы
  (короткий период)              (сравнение год к году)
```

### Docker-compose для VictoriaMetrics

```yaml
  victoriametrics:
    image: victoriametrics/victoria-metrics:v1.100.0
    container_name: victoriametrics
    restart: unless-stopped
    command:
      - '--storageDataPath=/victoria-metrics-data'
      - '--retentionPeriod=12'
    volumes:
      - vm_data:/victoria-metrics-data
      - ./victoriametrics/promscrape.yml:/etc/victoriametrics/promscrape.yml:ro
    ports:
      - "127.0.0.1:8428:8428"
    networks:
      - monitoring

volumes:
  vm_data: {}
```

VictoriaMetrics совместима с Prometheus API. Это значит:

- Grafana подключается к ней как к datasource типа Prometheus.
- PromQL работает без изменений.
- Любой инструмент который умеет читать из Prometheus, работает с VictoriaMetrics.

### Настройка Remote Write в Prometheus

Добавьте блок `remote_write` в `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

remote_write:
  - url: "http://victoriametrics:8428/api/v1/write"
    queue_config:
      max_samples_per_send: 10000
      max_shards: 30
      capacity: 50000

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['node_exporter:9100']
```

Параметры очереди:

- `max_samples_per_send: 10000` — сколько samples в одном запросе (стандарт).
- `max_shards: 30` — до 30 параллельных потоков отправки. Увеличьте если Prometheus не успевает отправлять данные.
- `capacity: 50000` — размер буфера очереди на один шард.

### Проверка

```bash
# UI VictoriaMetrics
curl http://localhost:8428

# Метрики поступают? (должны быть duplicate от Prometheus)
curl -s http://localhost:8428/api/v1/query?query=up

# Grafana datasource
# Type: Prometheus
# URL: http://victoriametrics:8428
# Save & Test
```

```promql
# Один и тот же запрос работает в обоих datasource
up{job="node"}

# VictoriaMetrics добавляет мета-метрики
vm_cache_size_bytes
vm_data_size_bytes
```

### Что даёт VictoriaMetrics

- **Долгое хранение** — `--retentionPeriod=12` месяцев без деградации производительности.
- **Меньше ресурсов** — VictoriaMetrics использует в 5-10 раз меньше RAM чем Prometheus на том же объёме данных.
- **Downsampling** — автоматическое прореживание старых данных (старые точки агрегируются).
- **Full PromQL compatibility** — все запросы из главы 4 работают без изменений.

---

## Когда нужен больше чем один Prometheus

Один Prometheus справляется с большинством задач DevOps-команды. Его границы:

| Параметр | Ограничение | Симптом |
|---|---|---|
| Активные time series | 1-3 млн | Медленные запросы, OOM |
| Scrape targets | ~500-1000 | Не успевает опрашивать |
| Retention | 15-30 дней без Remote Write | Заполняется диск |
| HA (High Availability) | Нет встроенной репликации | При падении — потеря метрик |

Когда нужно больше одного Prometheus:

```text
Несколько Prometheus:
┌───────────────────────────────────────────────┐
│                                               │
│  DC1 (Москва)          DC2 (СПб)              │
│  ┌──────────────┐     ┌──────────────┐        │
│  │ Prometheus 1 │     │ Prometheus 2 │        │
│  └──────┬───────┘     └──────┬───────┘        │
│         │                    │                 │
│         └────────┬───────────┘                 │
│                  ▼                             │
│        VictoriaMetrics (глобальное хранилище)  │
│                  │                             │
│                  ▼                             │
│             Grafana (единый дашборд)           │
│                                               │
└───────────────────────────────────────────────┘
```

- **Несколько дата-центров** — каждый DC свой Prometheus для автономности сети.
- **Более 1 млн time series** — разделить по группам: инфраструктурный, прикладной, бизнес-метрики.
- **High Availability** — два Prometheus с одинаковым конфигом, VictoriaMetrics дедуплицирует одинаковые метрики по labels.

Для команды из 1-5 человек, 1-3 серверов, 10-20 сервисов — **один Prometheus + VictoriaMetrics (remote write) вполне достаточно**. Thanos, Mimir, Grafana Cloud — для крупных K8s-кластеров, выходят за рамки этой книги.

---

## Grafana provisioning: алерты в Git

Если вы уже используете provisioning для datasources и dashboards (Глава 5), добавьте туда же alert rules. Все алерты в Git, а не в UI Grafana.

```yaml
# grafana/provisioning/alerting/alert_rules.yml
apiVersion: 1
groups:
  - orgId: 1
    name: infrastructure
    interval: 60s
    rules:
      - title: ServiceDown
        condition: A
        data:
          - refId: A
            datasourceUid: prometheus
            model:
              expr: up == 0
              intervalMs: 60000
              maxDataPoints: 0
        noDataState: Alerting
        execErrState: Alerting
        for: 1m
        annotations:
          summary: "Сервис недоступен"

      - title: HighCPU
        condition: A
        data:
          - refId: A
            datasourceUid: prometheus
            model:
              expr: 100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
              intervalMs: 60000
        noDataState: OK
        execErrState: Alerting
        for: 5m
        annotations:
          summary: "Высокий CPU на {{ $labels.instance }}"
```

Чтобы узнать `datasourceUid`:

```text
Grafana → Connections → Data Sources → Prometheus
→ URL показывает UID в адресной строке:
  connections/datasources/edit/UID   # UID = prometheus (по умолчанию)
```

Преимущества provisioning:

- Алерты хранятся в Git — code review, история изменений.
- Восстановление после переустановки Grafana — `docker compose up -d` и все алерты на месте.
- Однотипные алерты через шаблоны — не нужно создавать в UI 20 одинаковых правил.

---

## grafana-image-renderer: PNG в алертах

Когда алерт приходит в Telegram, хочется видеть не только текст, но и скриншот дашборда. Для этого нужен `grafana-image-renderer` — отдельный сервис, который рендерит панели Grafana в PNG.

### Добавить в docker-compose.yml

```yaml
  renderer:
    image: grafana/grafana-image-renderer:3.11.0
    container_name: renderer
    restart: unless-stopped
    environment:
      - HTTP_HOST=0.0.0.0
      - HTTP_PORT=8081
    ports:
      - "127.0.0.1:8081:8081"
    networks:
      - monitoring
```

### Настроить Grafana

```yaml
# docker-compose.yml → environment для grafana
environment:
  GF_RENDERING_SERVER_URL: http://renderer:8081/render
  GF_RENDERING_CALLBACK_URL: http://grafana:3000
  GF_UNIFIED_ALERTING_SCREENSHOTS: "true"
```

### Использовать в алертах

```yaml
# alertmanager/alertmanager.yml → telegram_configs
telegram_configs:
  - bot_token: 'YOUR_BOT_TOKEN'
    chat_id: -1001234567890
    message: |
      {{ range .Alerts }}
      {{ if eq .Status "firing" }}🔴{{ else }}✅{{ end }} *{{ .Labels.alertname }}*
      {{ .Annotations.summary }}
      {{ end }}
    parse_mode: Markdown
    disable_notification: false
```

PNG-скриншот будет прикреплён к сообщению если в алерте используется панель Grafana. Не все версии Telegram поддерживают вложения. Для стабильной работы — используйте email или отдельный сервис отправки.

> ☠️ **Осторожно:** renderer — ресурсоёмкий сервис. Каждый скриншот использует ~50-100 MB RAM. Для частых алертов (раз в минуту) renderer может потребить несколько GB. На small VPS (1-2 GB RAM) используйте только для критических алертов.

---

## Типичные ошибки

- **`--storage.tsdb.retention.time=1y` без Remote Write** — Prometheus работает на Go, его TSDB не рассчитан на годы данных. При 1 году хранения TSDB деградирует: запросы медленнее, OOM при compaction, файлы TSDB не уменьшаются после удаления старых блоков. Используйте VictoriaMetrics для долгого хранения.
- **Remote Write без мониторинга очереди** — если VictoriaMetrics недоступен, метрики накапливаются в буфере. Метрика `prometheus_remote_storage_queue_highest_sent_timestamp` показывает последний отправленный timestamp. Если она отстаёт от `time()` — очередь растёт, данные не успевают отправляться.
- **Grafana provisioning alert rules с неверным datasourceUid** — алерт создаётся, но condition 'B' не может найти datasource. Проверьте UID после создания datasource.
- **renderer не отвечает** — Grafana ждёт рендер до 30 секунд по умолчанию. Если renderer не запущен, панели с рендерингом будут долго грузиться. `GF_RENDERING_CALLBACK_URL` должен указывать на контейнер Grafana (не localhost), иначе renderer не сможет отдать PNG обратно.

---

## Чек-лист для самопроверки

- [ ] Знаю приблизительный размер данных моего Prometheus (`docker exec prometheus du -sh /prometheus`)
- [ ] Понимаю что 15 дней retention — нормально для оперативного мониторинга
- [ ] Настроил Remote Write в VictoriaMetrics (или знаю как это сделать)
- [ ] Проверил что VictoriaMetrics получает данные (`up` возвращает значения)
- [ ] Добавил VictoriaMetrics как datasource в Grafana и вижу те же метрики через неё
- [ ] Настроил хотя бы одно alert rule через Grafana provisioning
- [ ] Понимаю когда одного Prometheus достаточно и когда нужно несколько
- [ ] Знаю что такое grafana-image-renderer и как его подключить

---

## Попробуйте сами

1. Проверьте текущий размер данных Prometheus:
   ```bash
   docker exec prometheus du -sh /prometheus
   ```
   Сколько гигабайт занимают метрики за N дней работы? Совпадает с расчётом?

2. Запустите VictoriaMetrics. Добавьте `remote_write` в конфиг Prometheus. Проверьте что метрики дублируются:
   ```bash
   curl -s http://localhost:8428/api/v1/query?query=up
   curl -s http://localhost:9090/api/v1/query?query=up
   ```
   Оба возвращают одинаковые значения?

3. Добавьте VictoriaMetrics как второй datasource в Grafana. Создайте панель которая использует VictoriaMetrics напрямую. Работает так же как через Prometheus?

4. Проверьте метрику `prometheus_remote_storage_queue_highest_sent_timestamp` — отстаёт ли она от текущего времени?
   ```promql
   time() - prometheus_remote_storage_queue_highest_sent_timestamp
   ```
   Если больше 60 секунд — VictoriaMetrics не справляется или недоступен.

5. Настройте provisioning alert rule для любого алерта из главы 8 (например, HighCPU). Создайте файл `grafana/provisioning/alerting/alert_rules.yml`. Перезапустите Grafana — алерт появился в UI Grafana без ручного создания?
