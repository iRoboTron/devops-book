# Глава 4: Grafana — дашборды

---

## 4.1 Готовые дашборды

В Grafana → Import:
- **13770** — K8s All-in-one
- **1860** — Node Exporter Full
- **7249** — K8s Cluster

---

## 4.2 Свой дашборд

Создай панели:
1. RPS — `sum(rate(http_requests_total[5m]))`
2. Error rate — `rate(http_requests_total{status=~"5.."}[5m])`
3. P99 latency — `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))`
4. Memory — `container_memory_usage_bytes{pod=~"myapp-.*"}`

---

## 4.3 Variables

Dashboard Settings → Variables → New:
- Name: `namespace`
- Type: Query
- Query: `label_values(up, namespace)`

Теперь можно выбирать namespace на дашборде.

---

## 📋 Чеклист

- [ ] Готовый дашборд импортирован
- [ ] Свой дашборд с RED метриками создан
- [ ] Variables настроены

**Переходи к Главе 5 — Alertmanager.**
