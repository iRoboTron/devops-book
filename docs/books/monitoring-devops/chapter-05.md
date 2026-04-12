# Глава 5: Alertmanager — алерты в Telegram

---

## 5.1 Telegram бот

1. @BotFather → `/newbot` → получи токен
2. Напиши боту → найди chat_id

---

## 5.2 PrometheusRule

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
      annotations:
        description: "Error rate > 10%"
    - alert: MemoryLeak
      expr: container_memory_usage_bytes{pod=~"myapp-.*"} > 500e6
      for: 5m
      annotations:
        description: "Memory > 500MB"
```

---

## 5.3 Настройка Telegram в Alertmanager

Через Helm values:

```yaml
alertmanager:
  config:
    receivers:
    - name: telegram
      telegram_configs:
      - bot_token: "TOKEN"
        chat_id: CHAT_ID
    route:
      receiver: telegram
```

```bash
helm upgrade monitoring prometheus-community/kube-prometheus-stack -f values.yaml -n monitoring
```

---

## 5.4 Проверка

Запусти нагрузку на `/flaky` endpoint → жди алерт в Telegram.

---

## 📋 Чеклист

- [ ] Telegram бот создан
- [ ] PrometheusRule с алертами создан
- [ ] Alertmanager настроен на Telegram
- [ ] Алерт пришёл при нагрузке

**Переходи к Главе 6 — Loki.**
