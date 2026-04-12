# Глава 3: Инструментирование Python

---

## 3.1 prometheus-client

```python
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Response

REQUESTS = Counter('http_requests_total', 'HTTP requests', ['method', 'path', 'status'])

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route("/")
def home():
    REQUESTS.labels(method="GET", path="/", status=200).inc()
    return "ok"
```

---

## 3.2 ServiceMonitor

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

Prometheus автоматически начнёт скрейпить /metrics.

---

## 3.3 RED метрики

```
Rate:     rate(http_requests_total[5m])
Errors:   rate(http_requests_total{status=~"5.."}[5m])
Duration: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

---

## 📋 Чеклист

- [ ] /metrics endpoint добавлен
- [ ] ServiceMonitor создан
- [ ] RED метрики видны в Prometheus

**Переходи к Главе 4 — Grafana.**
