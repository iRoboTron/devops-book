# Глава 2: PromQL

---

## 2.1 Основы

```
# Скорость роста counter
rate(http_requests_total[5m])

# Сумма по статусам
sum by (status) (rate(http_requests_total[5m]))

# Среднее памяти
avg(container_memory_usage_bytes)

# Процент ошибок
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100
```

---

## 2.2 Применить к сломанному сервису

```
# Memory leak
container_memory_usage_bytes{pod=~"broken-.*"}

# Ошибки
rate(http_requests_total{status="500"}[5m])

# P99 latency (если есть histogram)
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

---

## 📋 Чеклист

- [ ] Могу написать rate(), sum by(), avg()
- [ ] Вижу memory leak в Prometheus
- [ ] Вижу процент ошибок

**Переходи к Главе 3 — Инструментирование.**
