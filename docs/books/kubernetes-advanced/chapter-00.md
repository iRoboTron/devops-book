# Глава 0: Что будем строить

> **Цель:** увидеть финальную архитекцию и понять путь.

---

## 0.1 От NodePort к продакшну

```
Модуль 10 (было):          Модуль 11 (станет):
NodePort :30080        →    Ingress: myapp.ru (HTTPS)
1 реплика                →    HPA: 2-10 реплик
Deployment для БД        →    StatefulSet + PVC
Все Pod'ы видят всех     →    NetworkPolicy: изоляция
20 YAML файлов           →    Helm chart
```

---

## 0.2 Финальная архитектура

```
Интернет
    │ HTTPS (myapp.ru)
    ▼
[ Ingress Controller ]
    │ routing
    ├──→ [ Service: myapp ]
    │        └──→ [ Deployment: myapp (2-5 реплик, HPA) ]
    │
    └──→ [ Service: api ]
             └──→ [ Deployment: api ]

[ StatefulSet: postgres ]
    └──→ [ PVC: pgdata-0 ]

[ NetworkPolicy: только api → postgres ]

Всё через Helm:
helm install myapp ./charts/myapp -f values.prod.yaml
```

---

## 0.3 План

| Глава | Что изучишь |
|-------|------------|
| 1 | Ingress — HTTPS по домену |
| 2 | HPA — автомасштабирование |
| 3 | Resources — limits и requests |
| 4 | StatefulSet — БД в K8s |
| 5 | NetworkPolicy — фаервол Pod'ов |
| 6 | RBAC — права в кластере |
| 7 | Helm зачем — проблема 20 YAML |
| 8 | Создаём Chart — шаблоны |
| 9 | Helm практика — готовые charts |

---

## 📋 Чеклист

- [ ] Я вижу финальную архитектуру
- [ ] Я понимаю что каждая глава решает конкретную проблему

**Переходи к Главе 1 — Ingress.**
