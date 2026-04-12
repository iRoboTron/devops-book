# Глава 1: Prometheus — сбор метрик

---

## 1.1 Pull-модель

```
Prometheus → /metrics приложения
    ↓
Собирает метрики каждые 15 секунд
```

Если /metrics не отвечает — Prometheus знает что сервис упал.

---

## 1.2 Установка

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace
```

В одном Helm chart:
- Prometheus (сбор метрик)
- Grafana (дашборды)
- Alertmanager (алерты)
- Node Exporter (метрики нод)
- kube-state-metrics (метрики K8s)

---

## 1.3 Доступ

```bash
# Prometheus
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 -n monitoring

# Grafana
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring
# пароль: admin
kubectl get secret monitoring-grafana -n monitoring -o jsonpath='{.data.admin-password}' | base64 -d
```

---

## 1.4 Первый запрос

Открой Prometheus UI (localhost:9090):

```
up
```

Покажет все таргеты. Все должны быть `1` (живы).

---

## 📋 Чеклист

- [ ] kube-prometheus-stack установлен
- [ ] Prometheus UI доступен
- [ ] Grafana доступна
- [ ] Запрос `up` показывает все таргеты живыми

**Переходи к Главе 2 — PromQL.**
