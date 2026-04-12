# Инструкция для ИИ-агента: Написание книги по Prometheus + Grafana + Loki

> **Это Модуль 12 курса DevOps 2.0.**
> Предварительные требования: пройдены модули 1–11 (включая K8s продвинутый и Helm).
> Смотри также:
> - [AGENT-INSTRUCTIONS-module-11.md](AGENT-INSTRUCTIONS-module-11.md) — Модуль 11 (K8s + Helm)
> - [AGENT-INSTRUCTIONS-module-06.md](AGENT-INSTRUCTIONS-module-06.md) — Модуль 6 (Безопасность и мониторинг базово)

---

## Контекст проекта

Ученик умеет деплоить в Kubernetes и управлять конфигурацией через Helm.
Его приложение работает. Но он не знает — работает ли оно хорошо. Память растёт? CPU упирается? Ошибки в логах? Он узнаёт об этом только когда звонят пользователи.

**Что он уже умеет** (не повторяй):
- Деплоит в K8s через Helm charts
- Знает `kubectl logs`, `kubectl top pods` — ручной мониторинг
- Из Модуля 6 знал базовый `htop`, `netdata` на одном сервере
- Умеет настраивать alerting через fail2ban (базово)

**Что его раздражает прямо сейчас:**
- Узнаёт о проблемах от пользователей, а не от системы
- `kubectl logs` — это ручной поиск по одному поду
- Нет истории: что было с CPU вчера в 3 ночи?
- 5 сервисов в K8s — логи везде, ничего не агрегировано

**Что он хочет после этой книги:**
Система сама сообщает когда что-то не так. Дашборд показывает состояние всех сервисов. Логи всех подов — в одном месте, с поиском.

---

## Что за книга

**Название:** "Prometheus + Grafana + Loki: Production-мониторинг"

**Место в курсе:** Книга 12 из 14

**Целевая аудитория:**
- Прошёл K8s + Helm
- Деплоит сервисы, но не знает что с ними происходит
- Хочет настоящий production-мониторинг, а не `htop` по SSH

**Объём:** 160-190 страниц

**Стиль:**
- Простой язык
- Проблема-первой: начинаем с поломки, весь курс строим систему чтобы её найти
- ASCII-схемы для архитектуры стека
- Практика на K8s через Helm

---

## Главная идея, которую должна передать книга

Мониторинг — это не "добавить метрики". Это ответы на три вопроса:

```
1. Что происходит прямо сейчас?   → Prometheus + Grafana (метрики)
2. Почему это произошло?          → Loki (логи)
3. Кто должен об этом узнать?     → Alertmanager (алерты)
```

**Ключевая педагогическая идея — проблема-первой:**
Глава 0: намеренно ломаем сервис (memory leak, медленные запросы).
Далее весь курс — строим систему чтобы найти поломку.
Каждый новый инструмент добавляет видимость: "теперь мы видели бы проблему раньше".

Это не абстрактное изучение инструментов — это решение реальной задачи.

---

## Что читатель построит к концу книги

```
Kubernetes кластер
│
├── kube-prometheus-stack (Helm)
│   ├── Prometheus          ← собирает метрики
│   ├── Alertmanager        ← отправляет алерты в Telegram
│   └── Grafana             ← дашборды (доступ через Ingress)
│
├── Loki + Promtail (Helm)
│   ├── Loki                ← агрегирует логи
│   └── Promtail            ← собирает логи со всех Pod'ов
│
└── Grafana (единая точка)
    ├── Dashboard: K8s обзор
    ├── Dashboard: Python-приложение (RED метрики)
    └── Dashboard: Логи (через Loki datasource)
```

Push → деплой → автоматически появились метрики и логи.
Проблема в продакшне → алерт в Telegram за < 1 минуты.

---

## Структура книги

### Глава 0: Намеренно ломаем сервис — почему мониторинг нужен

**Цель:** читатель видит проблему которую не может найти без инструментов.

- Создать простое Python-приложение с намеренными проблемами:
  ```python
  # Проблема 1: memory leak
  data = []
  @app.get("/leak")
  def leak():
      data.extend([0] * 10000)  # растёт каждый запрос
      return {"size": len(data)}

  # Проблема 2: медленный endpoint
  @app.get("/slow")
  def slow():
      time.sleep(random.uniform(0.1, 5.0))
      return {"ok": True}

  # Проблема 3: периодические ошибки
  @app.get("/flaky")
  def flaky():
      if random.random() < 0.3:
          raise HTTPException(500, "Случайная ошибка")
      return {"ok": True}
  ```
- Задеплоить в K8s
- Запустить нагрузку: `kubectl run loadgen --image=busybox -- /bin/sh -c "while true; do wget -q -O- http://app-svc/leak; done"`
- Попытаться найти проблему без инструментов: только `kubectl logs`, `kubectl top pods`
- Показать что это неудобно и неэффективно
- Вывод: нужна система которая сама всё видит

> **Именно этот сломанный сервис мы будем мониторить весь курс.**
> Каждый новый инструмент — новый слой видимости в ту же проблему.

---

### Часть 1: Метрики (Главы 1–4)

#### Глава 1: Prometheus — как работает pull-модель

**Цель:** читатель понимает как Prometheus собирает метрики и почему pull, а не push.

- Что такое метрика: число + метки + время
  ```
  http_requests_total{method="GET", path="/api", status="200"} 1543 1712345678
  └── имя метрики    └── labels                                 └── значение └── timestamp
  ```
- Pull-модель vs Push-модель:
  ```
  Push (StatsD, InfluxDB):     Pull (Prometheus):
  Приложение → сервер          Prometheus → /metrics приложения
  Кто упал — неизвестно        Если /metrics не отвечает → точно знаем
  ```
- `/metrics` endpoint: что там должно быть
- Типы метрик:
  ```
  Counter   — только растёт (requests_total, errors_total)
  Gauge     — вверх/вниз (memory_bytes, active_connections)
  Histogram — распределение (request_duration_seconds)
  Summary   — квантили (request_duration_p99)
  ```
- Установка через Helm (kube-prometheus-stack):
  ```bash
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
  helm install monitoring prometheus-community/kube-prometheus-stack \
    -n monitoring --create-namespace
  ```
- `kubectl get pods -n monitoring` — что поднялось
- `kubectl port-forward svc/monitoring-prometheus 9090:9090 -n monitoring`
- Prometheus UI: Status → Targets (кто скрейпится)
- Первый запрос: `up` — все ли таргеты живы

#### Глава 2: Node Exporter — метрики сервера

**Цель:** читатель видит метрики K8s нод в Prometheus.

- Node Exporter автоматически поднят kube-prometheus-stack
- Что собирает: CPU, RAM, диск, сеть, файловые дескрипторы
- Полезные метрики в PromQL:
  ```
  # Загрузка CPU (все ядра)
  100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

  # Свободная RAM
  node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100

  # Использование диска
  (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100
  ```
- Кube State Metrics: метрики K8s объектов (deployment replicas, pod restarts)
  ```
  kube_deployment_status_replicas_available{deployment="myapp"}
  kube_pod_container_status_restarts_total
  ```
- `kubectl top nodes` vs Prometheus: разница в детализации и истории

#### Глава 3: PromQL — язык запросов

**Цель:** читатель пишет запросы и понимает что они возвращают.

- Типы данных PromQL:
  ```
  Instant vector  — значение в конкретный момент
  Range vector    — значения за период [5m], [1h]
  Scalar          — одно число
  ```
- Основные операции:
  ```
  # Фильтрация по labels
  http_requests_total{job="myapp", status="500"}

  # rate — скорость роста counter за период
  rate(http_requests_total[5m])

  # irate — мгновенная скорость (для спайков)
  irate(http_requests_total[5m])

  # sum — суммировать
  sum(rate(http_requests_total[5m]))

  # sum by — суммировать с группировкой
  sum by (status) (rate(http_requests_total[5m]))

  # avg, max, min
  avg(container_memory_usage_bytes{pod=~"myapp-.*"})
  ```
- Агрегационные операторы: `sum`, `avg`, `max`, `min`, `count`, `topk`, `bottomk`
- Арифметика:
  ```
  # Конвертировать байты в MB
  container_memory_usage_bytes / 1024 / 1024

  # Процент ошибок
  rate(http_requests_total{status=~"5.."}[5m]) /
  rate(http_requests_total[5m]) * 100
  ```
- Применить к сломанному сервису:
  ```
  # Найти memory leak
  container_memory_usage_bytes{pod=~"myapp-.*"}

  # Найти медленные запросы (p99 latency)
  histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

  # Найти ошибки
  rate(http_requests_total{status=~"5.."}[5m])
  ```

> **Связь с Главой 0:** применяем PromQL к сломанному сервису. Читатель видит: вот где memory leak, вот где медленные запросы. Мониторинг работает.

#### Глава 4: Инструментирование Python-приложения

**Цель:** читатель добавляет метрики в своё приложение.

- prometheus-client для Python:
  ```python
  from prometheus_client import Counter, Histogram, Gauge, start_http_server

  REQUESTS = Counter('http_requests_total', 'HTTP requests', ['method', 'path', 'status'])
  DURATION = Histogram('http_request_duration_seconds', 'Request duration', ['path'])
  ACTIVE   = Gauge('active_requests', 'Active requests')

  @app.middleware("http")
  async def metrics_middleware(request, call_next):
      ACTIVE.inc()
      start = time.time()
      response = await call_next(request)
      DURATION.labels(path=request.url.path).observe(time.time() - start)
      REQUESTS.labels(
          method=request.method,
          path=request.url.path,
          status=response.status_code
      ).inc()
      ACTIVE.dec()
      return response

  @app.get("/metrics")
  async def metrics():
      return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
  ```
- ServiceMonitor: как сказать Prometheus скрейпить твой сервис
  ```yaml
  apiVersion: monitoring.coreos.com/v1
  kind: ServiceMonitor
  metadata:
    name: myapp
  spec:
    selector:
      matchLabels:
        app: myapp
    endpoints:
    - port: http
      path: /metrics
  ```
- RED метрики (Rate, Errors, Duration) — стандарт для веб-сервисов:
  ```
  Rate:     rate(http_requests_total[5m])
  Errors:   rate(http_requests_total{status=~"5.."}[5m])
  Duration: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
  ```

---

### Часть 2: Визуализация и алерты (Главы 5–7)

#### Глава 5: Grafana — дашборды

**Цель:** читатель создаёт дашборды и понимает их структуру.

- Grafana уже установлена через kube-prometheus-stack
- Доступ: `kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring`
- Пароль: `kubectl get secret monitoring-grafana -n monitoring -o jsonpath='{.data.admin-password}' | base64 -d`
- Datasource: Prometheus уже подключён автоматически
- Готовые дашборды (импорт по ID):
  - **13770** — K8s All-in-one
  - **1860** — Node Exporter Full
  - **7249** — K8s Cluster
- Создать дашборд для Python-приложения:
  - Panel 1: RPS (requests per second)
  - Panel 2: Error rate (%)
  - Panel 3: P99 latency
  - Panel 4: Memory usage
  - Panel 5: Pod restarts
- Variables в дашборде: выбрать namespace, deployment
- Annotations: отмечать деплои на графике времени
- Dashboard as code: JSON export → git → повторное использование

#### Глава 6: Alertmanager — алерты в Telegram

**Цель:** читатель получает Telegram-уведомление когда что-то сломалось.

- Архитектура алертинга:
  ```
  Prometheus → PrometheusRule → Alertmanager → Telegram Bot
  (считает)     (условие)       (маршрутизация) (отправляет)
  ```
- Создать Telegram бота: @BotFather → `/newbot` → получить токен
- Найти chat_id: написать боту → `https://api.telegram.org/bot<TOKEN>/getUpdates`
- Настроить Alertmanager через Helm values:
  ```yaml
  alertmanager:
    config:
      receivers:
      - name: telegram
        telegram_configs:
        - bot_token: "YOUR_TOKEN"
          chat_id: YOUR_CHAT_ID
          message: |
            🔴 *{{ .CommonLabels.alertname }}*
            {{ range .Alerts }}
            • {{ .Annotations.description }}
            {{ end }}
      route:
        receiver: telegram
  ```
- PrometheusRule — правила алертов:
  ```yaml
  apiVersion: monitoring.coreos.com/v1
  kind: PrometheusRule
  metadata:
    name: myapp-alerts
  spec:
    groups:
    - name: myapp
      rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Высокий процент ошибок"
          description: "Error rate {{ $value | humanizePercentage }} > 10%"

      - alert: MemoryLeak
        expr: container_memory_usage_bytes{pod=~"myapp-.*"} > 500e6
        for: 5m
        annotations:
          description: "Memory usage {{ $value | humanize }}B — возможен memory leak"

      - alert: SlowRequests
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        annotations:
          description: "P99 latency {{ $value }}s > 2s"
      ```
- `kubectl get prometheusrule` — список правил
- Состояния алертов: inactive → pending → firing
- Проверка: запустить нагрузку на сломанный сервис → ждать алерт в Telegram

> **Демонстрация которую нельзя пропустить:**
> Запустить нагрузку на `/leak` endpoint. Ждать 5 минут. Получить алерт в Telegram.
> Читатель должен увидеть: вот как работает production-мониторинг.

#### Глава 7: Grafana Alerting — алерты прямо из дашборда

**Цель:** читатель умеет создавать алерты в Grafana UI (альтернатива PrometheusRule).

- Grafana Alerting vs Alertmanager: разные подходы
  ```
  PrometheusRule + Alertmanager:  Grafana Alerting:
  YAML в git (GitOps)             UI в браузере (проще начать)
  Мощнее для сложных условий      Проще для дашбордных алертов
  Production choice               Good for learning
  ```
- Создать alert rule в Grafana: Alert → New alert rule
- Contact point: Telegram (те же настройки)
- Notification policy: когда и кому отправлять
- Silences: заглушить алерты на время деплоя

---

### Часть 3: Логи (Главы 8–10)

#### Глава 8: Loki — агрегация логов

**Цель:** читатель понимает архитектуру Loki и зачем он нужен рядом с Prometheus.

- Метрики vs Логи:
  ```
  Метрики (Prometheus):    Логи (Loki):
  "error rate = 5%"        "ERROR: db connection failed at 15:32:01"
  что происходит           почему происходит
  числа и графики          текст и контекст
  ```
- Архитектура Loki:
  ```
  Pod'ы → Promtail → Loki → Grafana
  (приложения)  (агент)  (хранилище)  (UI)
  ```
- Установка через Helm:
  ```bash
  helm repo add grafana https://grafana.github.io/helm-charts
  helm install loki grafana/loki-stack \
    --set grafana.enabled=false \
    --set prometheus.enabled=false \
    -n monitoring
  ```
- Добавить Loki datasource в Grafana (URL: `http://loki:3100`)
- Loki похож на Prometheus но для логов — та же идея labels

#### Глава 9: Promtail — собираем логи Pod'ов

**Цель:** читатель автоматически собирает логи всех Pod'ов.

- Promtail = агент который:
  - Читает логи Pod'ов (`/var/log/pods/`)
  - Добавляет labels из K8s (namespace, pod, container)
  - Отправляет в Loki
- Автоматические labels из K8s:
  ```
  {namespace="prod", pod="myapp-xxx", container="app", node="node1"}
  ```
- Pipeline stages: трансформация лога перед отправкой
  ```yaml
  pipeline_stages:
  - regex:
      expression: '(?P<level>INFO|WARN|ERROR)'
  - labels:
      level:
  ```
- Проверка: `kubectl logs pod/promtail-xxx -n monitoring` — что собирается

#### Глава 10: LogQL — поиск по логам

**Цель:** читатель ищет ошибки по всем сервисам в одном месте.

- LogQL = язык запросов Loki (похож на PromQL)
- Log stream selector:
  ```
  {namespace="prod", pod=~"myapp-.*"}
  {container="app"} |= "ERROR"
  {namespace="prod"} |~ "exception|error|failed" | json
  ```
- Фильтрация:
  ```
  |=  содержит строку
  !=  не содержит
  |~  regexp
  !~  не regexp
  ```
- Парсинг JSON логов:
  ```
  {container="app"} | json | level="error"
  ```
- Log metrics — считать ошибки из логов:
  ```
  rate({container="app"} |= "ERROR" [5m])
  ```
- Explore в Grafana: поиск логов в реальном времени
- Корреляция: на графике Grafana увидел спайк ошибок → кликнул в то время → открылись логи из Loki

> **Связь с Главой 0:** теперь мы видим полную картину сломанного сервиса:
> - Prometheus показывает что memory растёт (метрика)
> - Loki показывает почему (логи с ошибками)
> - Alertmanager уже написал в Telegram

---

### Часть 4: K8s-нативный мониторинг (Глава 11)

#### Глава 11: kube-prometheus-stack — полный стек в одном Helm chart

**Цель:** читатель понимает что уже установлено и как это настраивать через values.

- Что входит в kube-prometheus-stack:
  ```
  kube-prometheus-stack
  ├── Prometheus Operator     ← управляет Prometheus через CRD
  ├── Prometheus              ← сбор метрик
  ├── Alertmanager            ← алерты
  ├── Grafana                 ← дашборды
  ├── Node Exporter           ← метрики нод
  ├── kube-state-metrics      ← метрики K8s объектов
  └── Готовые дашборды        ← K8s, nodes, workloads
  ```
- CRD (Custom Resource Definitions):
  - `ServiceMonitor` — что скрейпить
  - `PrometheusRule` — правила алертов
  - `PodMonitor` — скрейпить Pod напрямую
- Кастомизация через values:
  ```yaml
  # values-monitoring.yaml
  grafana:
    ingress:
      enabled: true
      hosts:
        - grafana.myapp.ru
    adminPassword: "changeme"
    persistence:
      enabled: true
      size: 5Gi

  prometheus:
    prometheusSpec:
      retention: 30d
      storageSpec:
        volumeClaimTemplate:
          spec:
            resources:
              requests:
                storage: 20Gi
  ```
- `helm upgrade monitoring prometheus-community/kube-prometheus-stack -f values-monitoring.yaml -n monitoring`
- Retention: сколько хранить метрики (default 10d, рекомендуется 30d)

---

### Мини-проекты

#### Мини-проект 1: Дашборд сервера
Настроить и задокументировать:
- Grafana дашборд с CPU, RAM, диском, сетью
- Для K8s: deployment replicas, pod restarts, namespace quotas
- Экспортировать JSON → сохранить в git

#### Мини-проект 2: Алерт на падение сервиса
1. Написать PrometheusRule: сервис недоступен больше 1 минуты
2. Настроить Alertmanager → Telegram
3. Остановить приложение: `kubectl scale deployment myapp --replicas=0`
4. Ждать алерт в Telegram (< 2 минут)
5. Поднять обратно → алерт resolved в Telegram

#### Мини-проект 3: Логи всех сервисов в Grafana
1. Установить Loki + Promtail
2. Подключить к Grafana
3. Создать дашборд: метрики + логи рядом
4. Найти ошибку через LogQL в сломанном сервисе (из Главы 0)

---

### Приложения

#### Приложение A: Шпаргалка PromQL

| Выражение | Назначение |
|-----------|-----------|
| `up` | Все таргеты живы |
| `rate(counter[5m])` | Скорость роста counter |
| `sum by (label)` | Суммировать с группировкой |
| `histogram_quantile(0.99, ...)` | P99 latency |
| `node_memory_MemAvailable_bytes` | Свободная память |
| `kube_pod_container_status_restarts_total` | Рестарты контейнеров |

#### Приложение B: Готовые конфиги
- PrometheusRule: базовые алерты (CPU, RAM, disk, error rate)
- Alertmanager config для Telegram
- ServiceMonitor для Python/FastAPI
- Grafana dashboard JSON: RED метрики
- values.yaml для kube-prometheus-stack

#### Приложение C: Диагностика
- Prometheus не скрейпит таргет → проверить ServiceMonitor labels совпадают с Service labels
- Алерт не приходит → `kubectl get alertmanagerconfig`, проверить chat_id
- Loki не получает логи → `kubectl logs promtail-xxx -n monitoring`
- Grafana пустой дашборд → проверить datasource, временной диапазон, namespace

---

## Принципы написания

### 1. Проблема-первой — всегда

Вся книга строится вокруг сломанного сервиса из Главы 0.
При введении каждого инструмента показывать:
- **До:** "мы бы не заметили проблему / заметили поздно"
- **После:** "теперь мы видим это за X минут"

### 2. Применяй к реальным данным немедленно

После каждой новой концепции — применить к данным сломанного сервиса:
- Написали PromQL → посмотри memory leak в Prometheus UI
- Создали дашборд → открой и найди медленный endpoint
- Настроил алерты → запусти нагрузку и жди Telegram

### 3. Корреляция метрик и логов

В главах про Loki всегда показывать связку:
```
Grafana: спайк ошибок в 15:32 (метрика)
    ↓ кликнул на временной отрезок
Loki: "ERROR: db connection pool exhausted" в 15:32 (лог)
```
Это и есть ценность единой платформы мониторинга.

### 4. Helm values — в git

Любая настройка через `--set` в примерах должна быть перефразирована:
"Для продакшна выноси это в `values.yaml` и коммить в git".

### 5. Никакой воды

- Без истории SoundCloud и создания Prometheus
- Без сравнения с Datadog, New Relic, Zabbix
- Без OpenTelemetry (упомянуть что существует)
- Без Thanos, Cortex (distributed Prometheus) — упомянуть

---

## Что НЕ надо делать

- ❌ Не объяснять мониторинг без контекста сломанного сервиса
- ❌ Не показывать PromQL без применения к реальным данным
- ❌ Не настраивать алерты без реальной проверки (запусти нагрузку, жди Telegram)
- ❌ Не оставлять Grafana без Ingress — доступ только через port-forward неудобен
- ❌ Не пропускать retention настройку — дефолтные 10 дней мало для продакшна

---

## Формат файлов

```
docs/books/
├── AGENT-INSTRUCTIONS-module-12.md          # Этот файл
└── monitoring-devops/                       # Книга 12 (создать)
    ├── book.md
    ├── chapter-00.md                        # Намеренно ломаем сервис
    ├── chapter-01.md                        # Prometheus: pull-модель
    ├── chapter-02.md                        # Node Exporter
    ├── chapter-03.md                        # PromQL
    ├── chapter-04.md                        # Инструментирование Python
    ├── chapter-05.md                        # Grafana дашборды
    ├── chapter-06.md                        # Alertmanager + Telegram
    ├── chapter-07.md                        # Grafana Alerting
    ├── chapter-08.md                        # Loki
    ├── chapter-09.md                        # Promtail
    ├── chapter-10.md                        # LogQL
    ├── chapter-11.md                        # kube-prometheus-stack
    ├── appendix-a.md
    ├── appendix-b.md
    └── appendix-c.md
```

---

## Связь с другими модулями

**Что нужно из Модуля 6 (Безопасность и мониторинг базово):**
- `htop`, `netdata` — базовый мониторинг одного сервера
- fail2ban алерты — первый опыт "система сообщает о проблеме"

**Что нужно из Модуля 11 (K8s + Helm):**
- Helm — устанавливаем весь стек через Helm
- Ingress — для доступа к Grafana
- Namespace — всё в namespace `monitoring`

**Что даёт Модулю 13 (GitLab + GitOps):**
- PrometheusRule в git → ArgoCD деплоит автоматически
- Метрики деплоев: `kube_deployment_status_replicas_available` — мониторинг CI/CD
- Grafana annotations: отмечать деплои на графиках

---

*Эта инструкция — для ИИ-агента, который будет писать двенадцатую книгу курса DevOps.*
*Контекст проекта: /home/adelfos/Documents/lessons/dev-ops/README.md*
*Предыдущая: AGENT-INSTRUCTIONS-module-11.md (K8s + Helm)*
*Следующая: AGENT-INSTRUCTIONS-module-13.md (GitLab CI + GitOps)*
