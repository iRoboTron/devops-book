# K8s Advanced + Helm

> Книга 11: Ingress, HPA, StatefulSet, NetworkPolicy, RBAC, Helm

---

## Оглавление

- [**Глава 0: Что строим**](chapter-00.md)
- [**Глава 1: Ingress**](chapter-01.md) — HTTPS по домену вместо NodePort
- [**Глава 2: HPA**](chapter-02.md) — автомасштабирование
- [**Глава 3: Resources**](chapter-03.md) — limits, requests, quotas
- [**Глава 4: StatefulSet**](chapter-04.md) — БД в K8s
- [**Глава 5: NetworkPolicy**](chapter-05.md) — фаервол для Pod'ов
- [**Глава 6: RBAC**](chapter-06.md) — права в кластере
- [**Глава 7: Helm зачем**](chapter-07.md) — почему 20 YAML это проблема
- [**Глава 8: Создаём Chart**](chapter-08.md) — шаблоны + values
- [**Глава 9: Helm практика**](chapter-09.md) — готовые charts, зависимости

---

## Главная идея

```
Модуль 10:              Модуль 11:
NodePort :30080    →    Ingress (HTTPS по домену)
1 реплика всегда   →    HPA (автомасштабирование)
20 yaml файлов     →    Helm chart (один пакет)
```

---

## Предварительные требования

- Пройден Модуль 10 (K8s основы)
- k3s установлен и работает
- Умение kubectl apply/get/describe

---

*K8s Advanced + Helm — Курс DevOps, Модуль 11*
