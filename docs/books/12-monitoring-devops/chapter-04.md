# Глава 4: Grafana — дашборды

---

## 4.1 Готовые дашборды

В Grafana → Import:
- **13770** — K8s All-in-one
- **1860** — Node Exporter Full
- **7249** — K8s Cluster

Что показывает каждый:

| ID | Название | Что показывает |
|----|----------|----------------|
| 13770 | K8s All-in-one | CPU/RAM по Pod, сеть, PVC, overview кластера |
| 1860 | Node Exporter Full | CPU ноды, диск, сеть, load average |
| 7249 | K8s Cluster | Использование ресурсов по namespace |

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

Без переменной дашборд жёстко привязан к одному namespace. С переменной один и тот же дашборд можно использовать для `dev`, `staging`, `prod`.

---

## 📝 Упражнения

### Упражнение 4.1: Импорт дашборда
1. В Grafana открой `Dashboards -> Import`
2. Импортируй ID `13770`
3. Выбери Prometheus datasource
4. Найди Pod который потребляет больше всего CPU

### Упражнение 4.2: Свой RED дашборд
1. Создай 3 панели: `RPS`, `Error Rate`, `P99 Latency`
2. Добавь переменную `namespace`
3. Переключай namespace через dropdown
4. Убедись что данные обновляются в реальном времени

---

## 📋 Чеклист

- [ ] Готовый дашборд импортирован
- [ ] Свой дашборд с RED метриками создан
- [ ] Variables настроены

**Переходи к Главе 5 — Alertmanager.**
