# Глава 0: Ломаем сервис — зачем мониторинг

> **Цель:** создать сервис с проблемами и показать что без мониторинга мы слепы.

---

## 0.1 Сломанное приложение

```python
# app.py
import time, random
from flask import Flask, jsonify

data = []  # memory leak!
app = Flask(__name__)

@app.route("/")
def home():
    data.extend([0] * 10000)  # растёт
    return jsonify({"ok": True})

@app.route("/slow")
def slow():
    time.sleep(random.uniform(0.1, 5.0))
    return jsonify({"ok": True})

@app.route("/flaky")
def flaky():
    if random.random() < 0.3:
        return jsonify({"error": "fail"}), 500
    return jsonify({"ok": True})
```

Три проблемы: memory leak, медленные запросы, случайные ошибки.

---

## 0.2 Деплой и нагрузка

```bash
kubectl apply -f broken-app.yaml
kubectl run loadgen --image=busybox --restart=Never -- \
  sh -c "while true; do wget -q -O- http://broken-svc/; done"
```

---

## 0.3 Попытка найти проблему

```bash
kubectl logs broken-app-xxx     # тысячи строк
kubectl top pods                # только текущее состояние
kubectl describe pod            # нет истории
```

Без инструментов мы не видим:
- Растёт ли память?
- Какой % ошибок?
- Когда начались проблемы?

Наглядно: одиночные `kubectl`-команды дают только снимок «сейчас», а вопросы о тренде и истории остаются без ответа.

```mermaid
flowchart TD
    app["Сломанный сервис\n(leak + slow + 5xx)"]
    k1["kubectl logs\n(тысячи строк)"]
    k2["kubectl top\n(только сейчас)"]
    k3["kubectl describe\n(нет истории)"]
    q1["Растёт ли память?"]
    q2["Какой % ошибок?"]
    q3["Когда началось?"]

    app --> k1 --> q1
    app --> k2 --> q2
    app --> k3 --> q3

    q1 --> blind["Ответа нет —\nмы слепы"]
    q2 --> blind
    q3 --> blind

    style app fill:#6e2f1a,color:#fff
    style blind fill:#6e2f1a,color:#fff
    style q1 fill:#7d6608,color:#fff
    style q2 fill:#7d6608,color:#fff
    style q3 fill:#7d6608,color:#fff
```

**Вывод:** нужна система которая сама всё видит.

---

## 📋 Чеклист

- [ ] Сломанное приложение задеплоено
- [ ] Нагрузка запущена
- [ ] Я вижу что без мониторинга проблему не найти

**Переходи к Главе 1 — Prometheus.**
