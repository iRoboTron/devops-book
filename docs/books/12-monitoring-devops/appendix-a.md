# Мониторинг — Приложения

---

## A: PromQL шпаргалка

| Выражение | Назначение |
|-----------|-----------|
| `up` | Все таргеты живы |
| `rate(counter[5m])` | Скорость counter |
| `sum by (label) (rate(...))` | Сумма с группировкой |
| `histogram_quantile(0.99, rate(...))` | P99 latency |
| `container_memory_usage_bytes` | Память контейнера |
| `node_memory_MemAvailable_bytes` | Свободная RAM |
| `kube_pod_container_status_restarts_total` | Рестарты |

## B: Готовые конфиги

### PrometheusRule — алерты
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: myapp
spec:
  groups:
  - name: myapp
    rules:
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.1
      for: 2m
    - alert: HighLatency
      expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 2
      for: 5m
    - alert: PodCrashLooping
      expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
      for: 5m
```

### Alertmanager Telegram
```yaml
alertmanager:
  config:
    global:
      resolve_timeout: 5m
    route:
      receiver: telegram
      group_by: ['alertname']
    receivers:
    - name: telegram
      telegram_configs:
      - bot_token: "TOKEN"
        chat_id: CHAT_ID
```

## C: Диагностика

| Проблема | Причина | Решение |
|----------|---------|---------|
| Prometheus не скрейпит | ServiceMonitor labels ≠ Service | Проверь labels |
| Алерт не приходит | Неправильный chat_id | Проверь в Telegram |
| Loki не получает логи | Promtail не запущен | `kubectl logs promtail-xxx` |
| Grafana пустой дашборд | Неверный datasource | Проверь URL Prometheus |
