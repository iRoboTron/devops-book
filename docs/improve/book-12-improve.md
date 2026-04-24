# Инструкция агенту: улучшение книги 12 «Prometheus + Grafana + Loki»

## Контекст

```
/home/adelfos/Documents/lessons/dev-ops/docs/books/12-monitoring-devops/
```

Книга: **544 строки** — критически короткая для темы такого масштаба. Среднее по главе: ~60 строк. Самая короткая книга курса 2.0. В главах **нет ни одного упражнения** и почти нет вывода команд.

**Главная проблема:** три из семи глав (Alertmanager, Loki, LogQL) показывают конфиг без пояснения как проверить что это работает.

---

## Что НЕ трогать

- Структуру глав
- Существующие конфиги и PromQL запросы
- Схему метрики vs логи (глава 6)

---

## Добавить упражнения во все главы

Ни в одной главе нет блока «📝 Упражнения». Добавить в каждую.

---

## Задачи по главам

---

### Глава 1 (`chapter-01.md`) — Prometheus установка

**Проблема:** После установки helm chart нет проверки — как убедиться что всё поднялось.

**Добавить** в раздел 1.3 проверку после установки:

```bash
kubectl get pods -n monitoring
```

```
NAME                                                  READY   STATUS
alertmanager-monitoring-kube-prometheus-alertmanager  2/2     Running
monitoring-grafana-xxx                                3/3     Running
monitoring-kube-prometheus-operator-xxx               1/1     Running
monitoring-kube-state-metrics-xxx                     1/1     Running
monitoring-prometheus-node-exporter-xxx               1/1     Running
prometheus-monitoring-kube-prometheus-prometheus       2/2     Running
```

Если Pod в состоянии `Pending` — скорее всего нет StorageClass для PVC Prometheus.

```bash
kubectl get pvc -n monitoring
# Если Pending:
kubectl describe pvc -n monitoring | grep -A5 Events
```

**Добавить** в раздел 1.3 port-forward для Prometheus UI:

```bash
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 -n monitoring &
```

Открыть `http://localhost:9090` → Status → Targets: все targets должны быть `UP`.

**Добавить** упражнения:

```
### Упражнение 1.1: Установка
1. helm install monitoring ... (из раздела 1.2)
2. kubectl get pods -n monitoring — все Running?
3. port-forward на 9090
4. Prometheus UI: Status → Targets — сколько targets UP?

### Упражнение 1.2: Первый запрос
1. В Prometheus UI → Graph
2. Введи: up
3. Что показывает? Сколько сервисов мониторится?
```

---

### Глава 2 (`chapter-02.md`) — PromQL

**Проблема:** Запросы показаны без ожидаемого результата — читатель не знает правильный ли у него вывод.

**Добавить** к каждому запросу пример результата:

После `rate(http_requests_total[5m])`:

```
http_requests_total{handler="/", method="GET", status="200"}  → 2.3 req/s
http_requests_total{handler="/health", method="GET", status="200"} → 0.5 req/s
```

После `sum by (status) (rate(http_requests_total[5m]))`:

```
{status="200"} → 2.8 req/s
{status="500"} → 0.05 req/s   ← 1.7% ошибок
```

**Добавить** раздел **2.3 «Три ключевых запроса для любого сервиса (RED метрики)»:**

```promql
# Rate — запросов в секунду
rate(http_requests_total[5m])

# Errors — доля ошибок
rate(http_requests_total{status=~"5.."}[5m])
  /
rate(http_requests_total[5m])
* 100

# Duration — P99 задержка
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket[5m])
)
```

RED = Rate + Errors + Duration. Если эти три запроса работают — базовый мониторинг готов.

**Добавить** упражнения:

```
### Упражнение 2.1: Базовые запросы
1. Открой Prometheus UI (port-forward 9090)
2. Введи: up — что видишь?
3. Введи: container_memory_usage_bytes — сколько Pod'ов?
4. Введи: rate(container_cpu_usage_seconds_total[5m]) — топ по CPU?

### Упражнение 2.2: RED метрики (если есть приложение)
1. Запусти нагрузку на своё приложение
2. Посмотри rate(http_requests_total[1m])
3. Создай ошибку (несуществующий endpoint) — видно в error rate?
```

---

### Глава 3 (`chapter-03.md`) — Инструментирование Python

**Проблема:** Код показан, но нет вывода `/metrics` endpoint — непонятно что должно отдаваться.

**Добавить** в раздел 3.1 реальный пример вывода `/metrics`:

```bash
curl http://localhost:8000/metrics
```

```
# HELP http_requests_total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/",status="200"} 42.0
http_requests_total{method="GET",path="/health",status="200"} 156.0

# HELP python_gc_objects_collected_total...
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 1234.0
```

Это то что Prometheus будет скрейпить каждые 15 секунд.

**Добавить** раздел **3.3 «Проверить что Prometheus нашёл сервис»:**

```bash
# В Prometheus UI: Status → Targets
# Найти target с label job="myapp"
# Status должен быть UP

# Или через PromQL:
up{job="myapp"}
# 1 = работает, 0 = недоступен
```

**Добавить** упражнения:

```
### Упражнение 3.1: Метрики в приложении
1. Добавь Counter для HTTP запросов в своё приложение
2. curl http://localhost:8000/metrics — видишь метрику?
3. Примени ServiceMonitor
4. Prometheus: Status → Targets — myapp появился?
5. PromQL: http_requests_total — данные есть?
```

---

### Глава 4 (`chapter-04.md`) — Grafana дашборды

**Проблема:** Dashboard IDs показаны без пояснения что на них видно. Переменные описаны но нет скриншота UI.

**Добавить** в раздел 4.1 что показывает каждый дашборд:

| ID | Название | Что показывает |
|----|----------|----------------|
| 13770 | K8s All-in-one | CPU/RAM по Pod'ам, сеть, PVC — overview кластера |
| 1860 | Node Exporter Full | Метрики ноды: CPU, дисковый I/O, сеть |
| 7249 | K8s Cluster | Использование ресурсов namespace |

**Добавить** в раздел 4.3 пример создания переменной с объяснением зачем:

Без переменной дашборд жёстко привязан к одному namespace. С переменной — выбираешь в dropdown какой namespace смотреть. Один дашборд для dev, staging, prod.

**Добавить** упражнения:

```
### Упражнение 4.1: Импорт дашборда
1. Grafana → Dashboards → Import → ID: 13770
2. Выбери Prometheus datasource
3. Что видишь? Какой Pod потребляет больше CPU?

### Упражнение 4.2: Свой RED дашборд
1. Создай 3 панели: RPS, Error Rate, P99 Latency
2. Добавь переменную namespace
3. Проверь что данные обновляются в реальном времени
```

---

### Глава 5 (`chapter-05.md`) — Alertmanager + Telegram

**Проблема:** Показан PrometheusRule, но конфиг Alertmanager для Telegram не показан полностью — "через Helm values" без реального values.yaml.

**Добавить** полный `alertmanager-values.yaml`:

```yaml
# alertmanager-values.yaml — используй при helm upgrade
alertmanager:
  config:
    global:
      resolve_timeout: 5m
    route:
      group_by: ['alertname']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'telegram'
    receivers:
    - name: 'telegram'
      telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: YOUR_CHAT_ID
        message: |
          {{ range .Alerts }}
          🚨 *{{ .Annotations.summary }}*
          {{ .Annotations.description }}
          {{ end }}
        parse_mode: 'Markdown'
```

Применить:
```bash
helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring -f alertmanager-values.yaml
```

**Добавить** раздел **5.4 «Как проверить что алерт работает»:**

Принудительно вызвать алерт без поломки приложения:

```bash
# Создать тестовый алерт через Alertmanager API
curl -X POST http://localhost:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "warning"},
    "annotations": {"summary": "Тестовый алерт", "description": "Проверка Telegram"}
  }]'
```

Или через PrometheusRule с условием которое всегда true:
```yaml
- alert: AlwaysTrue
  expr: vector(1) == 1
  annotations:
    summary: "Тест алерта"
    description: "Этот алерт всегда срабатывает — удали после проверки"
```

**Добавить** упражнения:

```
### Упражнение 5.1: Telegram бот
1. @BotFather создай бота, получи токен
2. Напиши боту сообщение, найди chat_id через API
3. Добавь конфиг в helm values, сделай upgrade
4. Отправь тестовый алерт — пришло в Telegram?

### Упражнение 5.2: Реальный алерт
1. Создай PrometheusRule HighMemory: > 100Mi на 1 минуту
2. Подожди — алерт пришёл?
3. Что видно в Alertmanager UI (port 9093)?
```

---

### Глава 6 (`chapter-06.md`) — Loki

**Проблема:** Установка показана, datasource в Grafana показан. Нет проверки что Loki реально собирает логи.

**Добавить** в раздел 6.3 проверку:

```bash
kubectl get pods -n monitoring | grep loki
# loki-0  Running — сам Loki
# loki-promtail-xxx Running — агент который собирает логи
```

Promtail (или Alloy) собирает логи со всех Pod'ов и отправляет в Loki.

Проверить что Promtail видит Pod'ы:

```bash
kubectl logs -l app.kubernetes.io/name=promtail -n monitoring | tail -20
```

**Добавить** упражнения:

```
### Упражнение 6.1: Первые логи
1. Grafana → Explore → выбери Loki datasource
2. Введи: {namespace="default"}
3. Видишь логи своих Pod'ов?
4. Добавь фильтр: {namespace="default"} |= "ERROR"
```

---

### Глава 7 (`chapter-07.md`) — LogQL

**Глава краткая но структурированная.** Добавить только упражнения:

```
### Упражнение 7.1: LogQL запросы
1. {namespace="monitoring"} — сколько логов в monitoring?
2. {namespace="default"} |= "error" — есть ошибки?
3. {container="app"} | json | level="error" — JSON парсинг (если логи в JSON)

### Упражнение 7.2: Корреляция метрик и логов
1. В Grafana найди спайк ошибок на RED дашборде
2. Кликни на точку времени → "View logs"
3. Что было причиной ошибки по логам?
```

---

## Общий объём

Цель: 1200–1400 строк (сейчас 544). Удвоение объёма за счёт реальных выводов и упражнений.

## Приоритет

1. Глава 5 (Alertmanager) — добавить полный values.yaml с Telegram и способ тестирования
2. Глава 1 (Prometheus) — проверка после установки, `up` query
3. Глава 2 (PromQL) — добавить ожидаемые результаты и RED метрики
4. Упражнения во все главы — книга единственная без них

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-12-improve.md`*
