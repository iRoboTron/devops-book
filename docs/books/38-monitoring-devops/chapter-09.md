# Глава 9: Loki + Promtail — логи в Grafana

## Что вы узнаете

- чем Loki отличается от ELK и почему для DevOps-задач Loki чаще всего достаточен;
- как собрать логи Docker-контейнеров и системные логи через Promtail;
- как настроить logrotate чтобы Docker-логи не заполнили диск;
- LogQL: фильтры по тексту, парсинг JSON и logfmt, метрики из логов;
- как добавить Loki как datasource в Grafana и смотреть логи рядом с метриками;
- как связать метрику и лог через Explore split view и derived fields.

**Цель:** вы видите логи в Grafana рядом с метриками. При инциденте переходите с графика метрики на соответствующие строки логов за 2 клика.

---

## Loki vs ELK: замена Elasticsearch без боли

Если вы когда-нибудь настраивали ELK (Elasticsearch + Logstash + Kibana), вы знаете: Elasticsearch жадный до памяти. Одна инсталляция ELK на dev-сервере может съесть 4-6 GB RAM. Для продакшена нужен кластер, оператор Helm, S3-бакет для снапшотов. Это оправдано для full-text поиска по терабайтам логов — но для 90% DevOps-задач инструмент тяжелее чем задача.

Loki от Grafana Labs решает другую задачу: не индексировать содержимое логов, а только метки (labels). Логи хранятся сжатыми, поиск по тексту работает последовательным сканированием (как `grep`).

| Характеристика | ELK (Elasticsearch) | Loki |
|---|---|---|
| Индексация | Полнотекстовый индекс каждого поля | Только labels, содержимое не индексируется |
| RAM (min) | от 2-4 GB для осмысленной работы | от 128 MB для тестового режима |
| Хранение | Оригинал + индекс (2-3x от размера) | Только оригинал, сжатый |
| Скорость поиска | Быстрый full-text (миллисекунды) | Медленнее при большом объёме (сканирование) |
| Интеграция с Grafana | Через плагин, отдельный data source | Родной, из коробки |
| Агент сбора | Logstash (тяжёлый) или Filebeat | Promtail (лёгкий, ~15 MB) |
| Сложность настройки | Высокая (маппинги, шарды, ILM) | Низкая (один yaml) |

Для повседневной работы DevOps-инженера — поиск ошибок по логам за последние 30 дней, корреляция с метриками — Loki справляется на 100%. Elasticsearch имеет смысл ставить если нужен сложный full-text поиск по сотням гигабайт логов в день или если compliance требует индексации всех логов.

---

## Logrotate: чтобы Docker-логи не съели диск

До того как мы настроим Loki, решите проблему которая есть прямо сейчас — Docker-логи растут бесконечно. Контейнеры пишут в stdout/stderr, Docker сохраняет это в файлы `/var/lib/docker/containers/<container_id>/<container_id>-json.log`. Без ротации один контейнер может съесть десятки гигабайт.

Создайте файл `/etc/logrotate.d/docker`:

```bash
# /etc/logrotate.d/docker
/var/lib/docker/containers/*/*.log {
    rotate 7            # хранить 7 ротаций
    daily               # ротация раз в сутки
    compress            # сжимать старые ротации (gzip)
    delaycompress       # не сжимать самую свежую ротацию
    missingok           # не ошибка если файла нет
    copytruncate        # скопировать и усечь, не переименовывать
    size 100M           # или ротация при 100 MB
}
```

Параметр `copytruncate` критически важен для Docker-логов: он копирует файл и усекает оригинал до 0 байт, не переименовывая его. Docker продолжает писать в тот же дескриптор. Без `copytruncate` logrotate переименует файл, Docker продолжит писать в старый дескриптор — диск не освободится.

```bash
# Проверить синтаксис
sudo logrotate -d /etc/logrotate.d/docker

# Принудительно запустить ротацию
sudo logrotate -f /etc/logrotate.d/docker
```

> ☠️ **Осторожно:** Без logrotate один контейнер с активным логированием может заполнить раздел `/var/lib/docker` за несколько дней. Если раздел заполнится — Docker перестанет запускать контейнеры. Это одна из самых частых причин «внезапно всё упало» на production.

---

## Loki + Promtail: добавляем в стек

### docker-compose.yml

Добавьте два новых сервиса в ваш `docker-compose.yml`:

```yaml
  loki:
    image: grafana/loki:2.9.7
    container_name: loki
    restart: unless-stopped
    volumes:
      - ./loki/loki-config.yml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "127.0.0.1:3100:3100"
    networks:
      - monitoring

  promtail:
    image: grafana/promtail:2.9.7
    container_name: promtail
    restart: unless-stopped
    volumes:
      - ./promtail/promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: -config.file=/etc/promtail/config.yml
    networks:
      - monitoring
```

Не забудьте добавить том для данных Loki:

```yaml
volumes:
  loki_data: {}
```

### Конфигурация Loki

`loki/loki-config.yml` — минимальная конфигурация для тестового окружения:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  chunk_idle_period: 3m
  chunk_retain_period: 1m

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  retention_period: 30d
  reject_old_samples: true
  reject_old_samples_max_age: 168h
```

Прокомментируем ключевые параметры:

- `auth_enabled: false` — отключаем аутентификацию для простоты. В production включите multi-tenancy.
- `chunk_idle_period: 3m` — через 3 минуты без записи чанк считается готовым к сбросу на диск.
- `retention_period: 30d` — хранить логи 30 дней. Без этого параметра Loki хранит логи вечно.
- `reject_old_samples_max_age: 168h` — отклонять логи старше 7 дней при записи (чтобы Promtail случайно не залил архив).

> ☠️ **Осторожно:** Без `retention_period` Loki будет копить логи бесконечно. При 30 днях хранения следите за размером `loki_data` — если логи пишутся активно (nginx access log, отладка), объём может достигать десятков гигабайт.

### Конфигурация Promtail

`promtail/promtail-config.yml`:

```yaml
server:
  http_listen_port: 9080

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Системные логи (syslog, auth.log и т.д.)
  - job_name: system
    static_configs:
      - targets: [localhost]
        labels:
          job: varlogs
          host: myserver
          __path__: /var/log/*.log

  # Логи Docker-контейнеров через Docker socket
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: container
      - source_labels: ['__meta_docker_container_image']
        target_label: image
      - source_labels: ['__meta_docker_container_id']
        target_label: container_id
```

Promtail использует Docker Service Discovery (`docker_sd_configs`) чтобы узнавать о новых контейнерах в реальном времени. Когда вы запускаете новый контейнер, Promtail автоматически находит его лог-файл и добавляет label `container=<имя>`.

Альтернативный вариант — читать файлы напрямую:

```yaml
  - job_name: docker_files
    static_configs:
      - targets: [localhost]
        labels:
          job: docker
          __path__: /var/lib/docker/containers/*/*.log
    pipeline_stages:
      - json:
          expressions:
            log: log
            stream: stream
            time: time
      - labels:
          stream: ""
```

Этот вариант не требует доступа к Docker socket, но не добавляет label с именем контейнера автоматически.

### Запуск и проверка

```bash
# Создать директории для конфигов
mkdir -p loki promtail

# Перезапустить стек
docker compose up -d

# Проверить что оба сервиса запущены
docker compose ps

# Логи Loki
docker compose logs loki --tail 20

# Логи Promtail
docker compose logs promtail --tail 20
```

---

## LogQL: язык запросов к логам

LogQL — это как PromQL, но для логов. Два типа запросов: **log queries** (возвращают строки логов) и **metric queries** (возвращают временные ряды на основе логов).

### Label selectors

Первый и обязательный элемент любого LogQL-запроса — выборка по labels. Это аналог `{}` в PromQL.

```logql
# Все логи контейнера nginx
{container="nginx"}

# Все логи с job="varlogs" на хосте myserver
{job="varlogs", host="myserver"}

# Regex: все контейнеры начинающиеся на "app"
{container=~"app.*"}

# Все кроме "prometheus"
{container!="prometheus"}
```

Без label selector запрос не сработает. Loki сначала фильтрует по labels (индексированное поле), а потом по содержимому (сканирование).

### Line filters: поиск по тексту

После label selector можно добавить фильтр по содержимому строки:

```logql
# Строки содержащие "error" (регистр зависит)
{container="nginx"} |= "error"

# Строки НЕ содержащие "health"
{container="nginx"} != "health"

# Regex: любой из паттернов
{container="myapp"} |~ "ERROR|CRITICAL|FATAL"

# Regex: исключить
{container="myapp"} !~ "DEBUG|TRACE"
```

Порядок фильтров важен: сначала ставьте самый селективный (который отсекает больше всего строк). Loki выполняет их последовательно.

### Парсеры: JSON, logfmt и regex

Если лог — структурированный (JSON или logfmt), можно парсить его в labels и фильтровать по полям.

```logql
# JSON-парсер: лог {"level":"error","message":"connection refused","service":"api"}
{container="myapp"} | json | level="error"

# Фильтр по полю с числовым значением
{container="myapp"} | json | status_code >= 500

# logfmt-парсер: лог level=error msg="connection refused" service=api
{container="myapp"} | logfmt | level="error"

# Regex-парсер для произвольного формата
{container="nginx"} | regexp "(?P<ip>\\S+) \\S+ \\S+ \\[(?P<time>[^\\]]+)\\]"
```

Парсеры добавляют поля к строке лога. Эти поля можно использовать в фильтрах, группировке и метриках.

### Metric queries: графики из логов

LogQL может вычислять временные ряды из логов — это превращает логи в метрики.

```logql
# Количество ошибок в минуту
rate({container="nginx"} |= "error" [1m])

# Количество строк лога за 5 минут
count_over_time({job="varlogs"}[5m])

# Топ-10 IP из nginx access log
topk(10, sum by(remote_addr) (
  rate({job="nginx_access"} | logfmt | __error__="" [5m])
))

# Количество 500-х ошибок в минуту
sum by(container) (
  rate({container=~"app.*"} | json | status >= 500 [1m])
)
```

```promql
# Сравнение: тот же запрос в PromQL (если есть метрика http_requests_total)
rate(http_requests_total{status=~"5.."}[5m])
```

Разница: PromQL оперирует готовыми метриками, LogQL вычисляет метрики прямо из текста логов. Это полезно когда нет exporter'а для сервиса.

---

## Добавить Loki как datasource в Grafana

1. Откройте Grafana: `http://localhost:3000`
2. Левое меню → Connections → Data Sources → Add data source
3. Выберите **Loki**
4. URL: `http://loki:3100`
5. Нажмите **Save & Test** — должно появиться "Data source connected and labels found."

### Использование в дашборде

```text
1. Dashboard → New → Add visualization
2. Выбрать datasource: Loki
3. Ввести запрос: {container="nginx"} |= "error"
4. Тип визуализации: Logs
5. Настроить: Time range, Legend
```

Панель типа Logs отображает строки логов в реальном времени. Можно фильтровать и настраивать отображение полей.

---

## Correlating metrics and logs

### Explore split view

Самое полезное при диагностике: открыть метрики и логи рядом.

```text
1. Grafana → Explore
2. Выбрать datasource: Prometheus
3. Ввести запрос, например увеличение ошибок: 
   rate(http_requests_total{status=~"5.."}[5m])
4. Нажать кнопку Split (панель разделения) — справа откроется второй Explore
5. Выбрать datasource: Loki
6. Ввести запрос: {container="myapp"} |= "error"
7. Теперь: слева метрика (рост ошибок), справа логи в тот же момент времени
8. Выделить временной диапазон на графике — логи автоматически синхронизируются
```

Теперь при spike на графике ошибок вы видите конкретные строки логов в тот же момент. Два клика вместо часов grep'a.

### Derived fields — кликабельные ID в логах

Если в логах есть traceID, requestID или userID, можно сделать их ссылками на внешнюю систему (Jaeger, Kibana, свой сервис).

```text
1. Grafana → Connections → Data Sources → Loki → edit
2. Derived fields → Add
3. Name: TraceID
4. Regex: traceID=(\w+)    # или request_id=([a-f0-9-]+)
5. URL: http://jaeger:16686/trace/${__value.raw}
   # или http://kibana:5601/app/discover#/?_q=(query:'${__value.raw}')
6. Save & Test
```

Теперь в логах traceID подсвечивается как ссылка. Клик — открывается трейс в Jaeger.

---

## Типичные ошибки

- **Loki без retention** — `limits_config.retention_period` не выставлен, Loki хранит логи вечно. Диск заполняется за 2-3 недели активной работы. Всегда ставьте `retention_period`.
- **Высокая кардинальность labels в Loki** — если добавить `user_id` или `request_id` как label, индекс раздуется как в Prometheus. Labels должны быть низкокардинальными: `container`, `job`, `host`, `level`. Не более 5-10 уникальных значений на label в идеале.
- **Promtail не видит Docker-логи** — не примонтирован `/var/lib/docker/containers` или `/var/run/docker.sock`. Проверьте volumes в docker-compose.
- **Loki не стартует** — ошибка `"schema v11 requires boltdb-shipper"`. Убедитесь что `schema_config` и `storage_config` корректны. В версиях Loki > 2.8 схема v11 обязательна.
- **logrotate без copytruncate** — после ротации Docker продолжает писать в старый inode, диск не освобождается. `copytruncate` обязателен для Docker-логов.

---

## Чек-лист для самопроверки

- [ ] Loki + Promtail запущены и не падают (`docker compose ps`)
- [ ] Logrotate настроен для Docker-логов (`sudo logrotate -d /etc/logrotate.d/docker` не выдаёт ошибок)
- [ ] Логи поступают в Loki (Grafana → Explore → Loki → `{job="varlogs"}` видит строки)
- [ ] В Promtail настроен сбор Docker-логов через `docker_sd_configs`
- [ ] Добавлен Loki datasource в Grafana (Save & Test успешен)
- [ ] Умею написать LogQL-запрос с label selector + line filter
- [ ] Умею парсить JSON-логи через `| json`
- [ ] Умею строить график из логов через `rate()` и `count_over_time()`
- [ ] Настроен `retention_period: 30d` в конфиге Loki
- [ ] Знаю как использовать Split view в Explore для корреляции метрик и логов

---

## Попробуйте сами

1. Запустите Loki + Promtail. Откройте Grafana → Explore → Loki. Введите `{job="varlogs"}`. Видите строки из `/var/log/syslog` или `/var/log/auth.log`? Сколько строк в минуту приходит?

2. Создайте тестовый контейнер который пишет в stdout:
   ```bash
   docker run -d --name log-test alpine sh -c 'while true; do echo "$(date) INFO: всё работает"; sleep 2; done'
   ```
   Найдите его логи в Loki через `{container="log-test"}`. Остановите контейнер (`docker rm -f log-test`).

3. Напишите LogQL-запрос для логов nginx:
   ```logql
   # Если у вас есть nginx, найдите все строки с 404:
   {container="nginx"} |= "404"
   
   # Количество 404 в минуту:
   rate({container="nginx"} |= " 404 " [1m])
   ```

4. Настройте Split view в Explore: слева PromQL с `rate(http_requests_total[5m])`, справа Loki с `{container="myapp"} |= "error"`. Убедитесь что временные диапазоны синхронизированы при выделении.

5. Сымитируйте проблему: запустите `stress --cpu 4 --timeout 120` и одновременно смотрите логи системы через `{job="varlogs"} |= "stress"`.

6. Проверьте работу logrotate: `sudo logrotate -f /etc/logrotate.d/docker && ls -la /var/lib/docker/containers/*/*.log`. Появился ли сжатый файл ротации?
