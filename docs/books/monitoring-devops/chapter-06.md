# Глава 6: Loki — агрегация логов

---

## 6.1 Метрики vs Логи

```
Метрики: "error rate = 5%"     → что
Логи:    "ERROR: db failed"    → почему
```

---

## 6.2 Установка

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  --set grafana.enabled=false \
  --set prometheus.enabled=false \
  -n monitoring
```

---

## 6.3 Loki datasource в Grafana

Configuration → Data Sources → Add → Loki:
- URL: `http://loki:3100`

---

## 6.4 Explore в Grafana

Explore → выбери Loki → напиши:

```
{namespace="default", pod=~"myapp-.*"} |= "ERROR"
```

Покажет все ERROR логи из Pod'ов myapp.

---

## 📋 Чеклист

- [ ] Loki установлен
- [ ] Datasource добавлен в Grafana
- [ ] Могу искать логи через Explore

**Переходи к Главе 7 — LogQL.**
